import os
from pathlib import Path

import yaml

CATALOG_PATH = Path('/catalog.yaml')

_CATALOG: list[dict] | None = None


def _docs_base() -> Path:
    if os.environ.get('DEV_MODE', 'false').lower() == 'true':
        return Path(os.environ.get('DEV_DOCS_MOUNT', '/docs-mount'))
    return Path('/docs')


def _load_catalog() -> list[dict]:
    raw = yaml.safe_load(CATALOG_PATH.read_text()).get('documents', [])
    result = []
    for doc in raw:
        name = doc['name']
        doc_dir = _docs_base() / name
        meta_path = doc_dir / 'catalog.yaml'

        entry: dict = {'name': name, 'url': doc.get('url', '')}

        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text()) or {}
            entry.update(meta)
            for field in ('markdown_file', 'pdf_file', 'sentences_file', 'turtle_file'):
                rel = meta.get(field)
                entry[f'has_{field[:-5]}'] = bool(rel and (doc_dir / rel).exists())

        result.append(entry)
    return result


def get_catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = _load_catalog()
    return _CATALOG


def find_doc(name: str) -> dict | None:
    return next((d for d in get_catalog() if d['name'] == name), None)


def search_catalog(q: str) -> list[dict]:
    q_lower = q.lower()
    matches = []
    for doc in get_catalog():
        text = ' '.join(
            (str(v) if not isinstance(v, list) else ' '.join(str(i) for i in v))
            for v in doc.values()
        )
        if q_lower in text.lower():
            matches.append(doc)
    return matches
