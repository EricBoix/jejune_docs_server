import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .catalog import find_doc, get_catalog, search_catalog
from .sentences import find_by_position, get_chapters, load_sentences

app = FastAPI(
    title="jejune_docs_server",
    description=(
        "HTTP service for jejune_doc repositories. "
        "Provides catalog search and per-document access to markdown, PDF, and sentences."
    ),
    version="0.1.0",
    docs_url="/swagger",
)

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
