import os
import urllib.request
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .catalog import find_doc, get_catalog, search_catalog
from .sentences import find_by_position, get_chapters, load_sentences

app = FastAPI(
    title="jejune_docs_server",
    description=(
        "HTTP service for jejune_doc repositories. "
        "Provides catalog search and per-document access to markdown, PDF, and sentences.\n\n"
        "Internal endpoints (`/config`, `/project-link`) serve the landing page only "
        "and are excluded from this schema."
    ),
    version="0.1.0",
    docs_url="/swagger",
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

_PROJECT_LINK_YAML = (
    "https://raw.githubusercontent.com/EricBoix/jejune_project/main/GitHostingSite.yaml"
)
_project_link: str | None = None


def _fetch_project_link() -> str:
    try:
        with urllib.request.urlopen(_PROJECT_LINK_YAML, timeout=5) as resp:
            data = yaml.safe_load(resp.read().decode())
        site = data.get("git_hosting_site") or ""
        repo = data.get("project_repository_name") or ""
        return site + repo
    except Exception:
        return ""


@app.get("/project-link", include_in_schema=False)
def get_project_link():
    global _project_link
    if _project_link is None:
        _project_link = _fetch_project_link()
    return {"link": _project_link}


_DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() == 'true'
_INCLUDE_PDFS = os.environ.get('INCLUDE_PDFS', 'false').lower() == 'true'
_DOCS_BASE = Path(os.environ.get('DEV_DOCS_MOUNT', '/docs-mount') if _DEV_MODE else '/docs')


def _doc_path(doc: dict, field: str) -> Path | None:
    rel = doc.get(field)
    if not rel:
        return None
    p = _DOCS_BASE / doc['name'] / rel
    return p if p.exists() else None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@app.get('/catalog', summary='List all catalog entries with metadata')
def list_catalog():
    return get_catalog()


@app.get('/catalog/search', summary='Search catalog by query string (case-insensitive substring)')
def search(q: str):
    return search_catalog(q)


# ---------------------------------------------------------------------------
# Document content
# ---------------------------------------------------------------------------

@app.get('/docs/{name}/markdown', summary='Raw markdown content')
def get_markdown(name: str):
    doc = _require_doc(name)
    path = _doc_path(doc, 'markdown_file')
    if not path:
        raise HTTPException(404, 'No markdown file available for this document')
    return FileResponse(path, media_type='text/markdown; charset=utf-8')


@app.get('/docs/{name}/markdown-url', summary='Canonical public URL for the raw markdown')
def get_markdown_url(name: str, request: Request):
    _require_doc(name)
    base = str(request.base_url).rstrip('/')
    return {"markdown_url": f"{base}/docs/{name}/markdown"}


@app.get('/docs/{name}/turtle', summary='RDF/Turtle knowledge graph')
def get_turtle(name: str):
    doc = _require_doc(name)
    path = _doc_path(doc, 'turtle_file')
    if not path:
        raise HTTPException(404, 'No turtle file available for this document')
    return FileResponse(path, media_type='text/turtle; charset=utf-8')


@app.get('/docs/{name}/pdf', summary='PDF file (requires INCLUDE_PDFS=true or DEV_MODE=true)')
def get_pdf(name: str):
    doc = _require_doc(name)
    if not (_DEV_MODE or _INCLUDE_PDFS):
        raise HTTPException(403, 'PDF access disabled; set INCLUDE_PDFS=true or DEV_MODE=true')
    path = _doc_path(doc, 'pdf_file')
    if not path:
        raise HTTPException(404, 'No PDF available for this document')
    return FileResponse(path, media_type='application/pdf')


# ---------------------------------------------------------------------------
# Sentences
# ---------------------------------------------------------------------------

@app.get('/docs/{name}/chapters', summary='Chapter list in order of first appearance')
def list_chapters(name: str):
    return get_chapters(_load_sentences(name))


@app.get(
    '/docs/{name}/sentences',
    summary='All sentences, optionally filtered by chapter / paragraph / sentence number',
)
def get_sentences(
    name: str,
    chapter: Optional[str] = None,
    paragraph: Optional[int] = None,
    sentence: Optional[int] = None,
):
    sentences = _load_sentences(name)
    if chapter is not None and paragraph is not None and sentence is not None:
        result = find_by_position(sentences, chapter, paragraph, sentence)
        if result is None:
            raise HTTPException(404, 'Sentence not found')
        return result
    if chapter is not None:
        ch_lower = chapter.lower()
        sentences = [s for s in sentences if (s.get('chapter') or '').lower() == ch_lower]
    return sentences


@app.get('/docs/{name}/sentences/{index}', summary='Sentence by 0-based array index')
def get_sentence_by_index(name: str, index: int):
    sentences = _load_sentences(name)
    if index < 0 or index >= len(sentences):
        raise HTTPException(404, f'Index {index} out of range (0–{len(sentences) - 1})')
    return sentences[index]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_doc(name: str) -> dict:
    doc = find_doc(name)
    if not doc:
        raise HTTPException(404, f"Document '{name}' not found in catalog")
    return doc


def _load_sentences(name: str) -> list[dict]:
    doc = _require_doc(name)
    path = _doc_path(doc, 'sentences_file')
    if not path:
        raise HTTPException(404, 'No sentences file available for this document')
    return load_sentences(path)
