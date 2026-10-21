import os
from pathlib import Path
from typing import ClassVar

import yaml


class CatalogService:
    CATALOG_PATH: ClassVar[Path] = Path('/catalog.yaml')

    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path if catalog_path is not None else CatalogService.CATALOG_PATH
        self._catalog: list[dict] | None = None

    def _docs_base(self) -> Path:
        if os.environ.get('DEV_MODE', 'false').lower() == 'true':
            return Path(os.environ.get('DEV_DOCS_MOUNT', '/docs-mount'))
        return Path('/docs')

    def _load_catalog(self) -> list[dict]:
        raw = yaml.safe_load(self.catalog_path.read_text()).get('documents', [])
        result = []
        for doc in raw:
            name = doc['name']
            doc_dir = self._docs_base() / name
            meta_path = doc_dir / 'manifest.yaml'

            entry: dict = {'name': name, 'url': doc.get('url', '')}

            if meta_path.exists():
                meta = yaml.safe_load(meta_path.read_text()) or {}
                entry.update(meta)
                for field in ('markdown_file', 'pdf_file'):
                    rel = meta.get(field)
                    entry[f'has_{field[:-5]}'] = bool(rel and (doc_dir / rel).exists())
                extractions = meta.get('graph_extractions') or []
                entry['has_graph_extractions'] = bool(extractions) and any(
                    (doc_dir / ex['turtle_file']).exists()
                    for ex in extractions
                    if ex.get('turtle_file')
                )

            result.append(entry)
        return result

    def get_catalog(self) -> list[dict]:
        if self._catalog is None:
            self._catalog = self._load_catalog()
        return self._catalog

    def find_doc(self, name: str) -> dict | None:
        return next(
            (d for d in self.get_catalog()
             if d.get('name') == name
             or d.get('doc_name') == name
             or f"jejune_doc_{d.get('slug', '')}" == name),
            None,
        )

    def search_catalog(self, query: str) -> list[dict]:
        query_lower = query.lower()
        matches = []
        for doc in self.get_catalog():
            text = ' '.join(
                (str(value) if not isinstance(value, list) else ' '.join(str(item) for item in value))
                for value in doc.values()
            )
            if query_lower in text.lower():
                matches.append(doc)
        return matches
