import os
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .catalog import CatalogService
from .chunks import find_chunk_by_position, get_chapters, load_chunks


class ServerSettings:
    def __init__(self) -> None:
        self.dev_mode: bool = os.environ.get('DEV_MODE', 'false').lower() == 'true'
        self.include_pdfs: bool = os.environ.get('INCLUDE_PDFS', 'false').lower() == 'true'
        self.docs_base: Path = Path(
            os.environ.get('DEV_DOCS_MOUNT', '/docs-mount') if self.dev_mode else '/docs'
        )


_PROJECT_LINK_YAML = (
    "https://raw.githubusercontent.com/EricBoix/jejune_project/main/GitHostingSite.yaml"
)


class ProjectLinkCache:
    def __init__(self) -> None:
        self._link: str | None = None

    def get(self) -> str:
        if self._link is None:
            self._link = self._fetch()
        return self._link

    def _fetch(self) -> str:
        try:
            with urllib.request.urlopen(_PROJECT_LINK_YAML, timeout=5) as resp:
                data = yaml.safe_load(resp.read().decode())
            site = data.get("git_hosting_site") or ""
            repo = data.get("project_repository_name") or ""
            return site + repo
        except Exception:
            return ""


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.settings = ServerSettings()
    application.state.catalog_service = CatalogService()
    application.state.project_link_cache = ProjectLinkCache()
    yield


app = FastAPI(
    title="jejune_docs_server",
    description=(
        "HTTP service for jejune_doc repositories. "
        "Provides catalog search and per-document access to markdown, PDF, and graph extractions.\n\n"
        "Internal endpoints (`/config`, `/project-link`) serve the landing page only "
        "and are excluded from this schema."
    ),
    version="0.1.0",
    docs_url="/swagger",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

app.mount("/static", StaticFiles(directory="/app/static"), name="static")


@app.get("/", include_in_schema=False)
async def landing():
    return FileResponse("/app/static/index.html")


@app.get("/config", include_in_schema=False)
def get_config():
    return {
        "kg_graph_viewer_url": os.environ.get("KG_GRAPH_VIEWER_URL", ""),
        "markdown_browser_url": os.environ.get("MARKDOWN_BROWSER_URL", ""),
        "markdown_browser_trigger_url": os.environ.get("MARKDOWN_BROWSER_TRIGGER_URL", ""),
    }


@app.get("/project-link", include_in_schema=False)
def get_project_link(request: Request):
    return {"link": request.app.state.project_link_cache.get()}


def _doc_path(doc: dict, field: str, settings: ServerSettings) -> Path | None:
    rel = doc.get(field)
    if not rel:
        return None
    path = settings.docs_base / doc['name'] / rel
    return path if path.exists() else None


def _find_graph_extraction(doc: dict, model_name: str, chunk_short_name: str) -> dict | None:
    for entry in (doc.get('graph_extractions') or []):
        if entry.get('model_name') == model_name and entry.get('chunk_short_name') == chunk_short_name:
            return entry
    return None


def _require_graph_extraction(doc: dict, model_name: str, chunk_short_name: str) -> dict:
    entry = _find_graph_extraction(doc, model_name, chunk_short_name)
    if entry is None:
        raise HTTPException(
            404, f"No graph extraction found for model='{model_name}' chunk='{chunk_short_name}'"
        )
    return entry


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@app.get('/catalog', summary='List all catalog entries with metadata')
def list_catalog(request: Request):
    return request.app.state.catalog_service.get_catalog()


@app.get('/catalog/search', summary='Search catalog by query string (case-insensitive substring)')
def search(q: str, request: Request):
    return request.app.state.catalog_service.search_catalog(q)


# ---------------------------------------------------------------------------
# Document content
# ---------------------------------------------------------------------------

@app.get('/docs/{name}/markdown', summary='Raw markdown content')
def get_markdown(name: str, request: Request):
    doc = _require_doc(name, request)
    path = _doc_path(doc, 'markdown_file', request.app.state.settings)
    if not path:
        raise HTTPException(404, 'No markdown file available for this document')
    return FileResponse(path, media_type='text/markdown; charset=utf-8')


@app.get('/docs/{name}/markdown-url', summary='Canonical public URL for the raw markdown')
def get_markdown_url(name: str, request: Request):
    _require_doc(name, request)
    base = str(request.base_url).rstrip('/')
    return {"markdown_url": f"{base}/docs/{name}/markdown"}


@app.get('/docs/{name}/pdf', summary='PDF file (requires INCLUDE_PDFS=true or DEV_MODE=true)')
def get_pdf(name: str, request: Request):
    doc = _require_doc(name, request)
    settings = request.app.state.settings
    if not (settings.dev_mode or settings.include_pdfs):
        raise HTTPException(403, 'PDF access disabled; set INCLUDE_PDFS=true or DEV_MODE=true')
    path = _doc_path(doc, 'pdf_file', settings)
    if not path:
        raise HTTPException(404, 'No PDF available for this document')
    return FileResponse(path, media_type='application/pdf')


# ---------------------------------------------------------------------------
# Graph extractions
# ---------------------------------------------------------------------------

@app.get('/docs/{name}/graphs', summary='List all graph extraction entries')
def list_graphs(name: str, request: Request):
    doc = _require_doc(name, request)
    return doc.get('graph_extractions') or []


@app.get(
    '/docs/{name}/graphs/{model_name}/{chunk_short_name}/turtle',
    summary='RDF/Turtle knowledge graph for a given model and chunk type',
)
def get_graph_turtle(name: str, model_name: str, chunk_short_name: str, request: Request):
    doc = _require_doc(name, request)
    entry = _require_graph_extraction(doc, model_name, chunk_short_name)
    turtle_file = entry.get('turtle_file')
    if not turtle_file:
        raise HTTPException(404, 'This extraction entry has no turtle_file')
    path = request.app.state.settings.docs_base / doc['name'] / turtle_file
    if not path.exists():
        raise HTTPException(404, 'Turtle file not found on disk')
    return FileResponse(path, media_type='text/turtle; charset=utf-8')


@app.get(
    '/docs/{name}/graphs/{model_name}/{chunk_short_name}/chunks',
    summary='Source chunk JSON file for a given model and chunk type',
)
def get_graph_chunk_file(name: str, model_name: str, chunk_short_name: str, request: Request):
    doc = _require_doc(name, request)
    entry = _require_graph_extraction(doc, model_name, chunk_short_name)
    chunk_file = entry.get('chunk_file')
    if not chunk_file:
        raise HTTPException(404, 'This extraction entry has no chunk_file')
    path = request.app.state.settings.docs_base / doc['name'] / chunk_file
    if not path.exists():
        raise HTTPException(404, 'Chunk file not found on disk')
    return FileResponse(path, media_type='application/json; charset=utf-8')


@app.get(
    '/docs/{name}/graphs/{model_name}/{chunk_short_name}/chapters',
    summary='Chapter list derived from chunk metadata, in order of first appearance',
)
def list_chunk_chapters(name: str, model_name: str, chunk_short_name: str, request: Request):
    return get_chapters(_load_chunk_entries(name, model_name, chunk_short_name, request))


@app.get(
    '/docs/{name}/graphs/{model_name}/{chunk_short_name}/entries',
    summary='Parsed chunk entries, optionally filtered by chapter / paragraph / sentence',
)
def get_chunk_entries(
    name: str,
    model_name: str,
    chunk_short_name: str,
    request: Request,
    chapter: Optional[str] = None,
    paragraph: Optional[int] = None,
    sentence: Optional[int] = None,
):
    chunks = _load_chunk_entries(name, model_name, chunk_short_name, request)
    if chapter is not None and paragraph is not None and sentence is not None:
        result = find_chunk_by_position(chunks, chapter, paragraph, sentence)
        if result is None:
            raise HTTPException(404, 'Chunk not found at the given position')
        return result
    if chapter is not None:
        chapter_lower = chapter.lower()
        chunks = [chunk for chunk in chunks if (chunk.get('chapter') or '').lower() == chapter_lower]
    return chunks


@app.get(
    '/docs/{name}/graphs/{model_name}/{chunk_short_name}/entries/{index}',
    summary='Single chunk entry by 0-based array index',
)
def get_chunk_entry_by_index(name: str, model_name: str, chunk_short_name: str, index: int, request: Request):
    chunks = _load_chunk_entries(name, model_name, chunk_short_name, request)
    if index < 0 or index >= len(chunks):
        raise HTTPException(404, f'Index {index} out of range (0–{len(chunks) - 1})')
    return chunks[index]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_doc(name: str, request: Request) -> dict:
    doc = request.app.state.catalog_service.find_doc(name)
    if not doc:
        raise HTTPException(404, f"Document '{name}' not found in catalog")
    return doc


def _load_chunk_entries(name: str, model_name: str, chunk_short_name: str, request: Request) -> list[dict]:
    doc = _require_doc(name, request)
    entry = _require_graph_extraction(doc, model_name, chunk_short_name)
    chunk_file = entry.get('chunk_file')
    if not chunk_file:
        raise HTTPException(404, 'This extraction entry has no chunk_file')
    path = request.app.state.settings.docs_base / doc['name'] / chunk_file
    if not path.exists():
        raise HTTPException(404, 'Chunk file not found on disk')
    return load_chunks(path)
