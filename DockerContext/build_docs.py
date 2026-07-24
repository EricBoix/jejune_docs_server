#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

import yaml

_FULL_CATALOG = '/full-catalog.yaml'
_SECRET_CATALOG = '/run/secrets/catalog'
_EFFECTIVE_CATALOG = '/catalog.yaml'


def _load_yaml(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f).get('documents', [])


def _validate_subset(deployment: list[dict], reference: list[dict]) -> None:
    ref_index = {doc['name']: doc['url'].rstrip('/') for doc in reference}
    errors = []
    for doc in deployment:
        name = doc['name']
        url = doc['url'].rstrip('/')
        if name not in ref_index:
            errors.append(f"  {name}: not in full-catalog.yaml")
        elif url != ref_index[name]:
            errors.append(f"  {name}: URL mismatch (catalog={url!r}, reference={ref_index[name]!r})")
    if errors:
        print("Catalog subset validation failed:", flush=True)
        for e in errors:
            print(e, flush=True)
        sys.exit(1)


def _resolve_catalog() -> list[dict]:
    full = _load_yaml(_FULL_CATALOG)

    if os.path.exists(_SECRET_CATALOG):
        print("Using deployment catalog from secret.", flush=True)
        deployment = _load_yaml(_SECRET_CATALOG)
        _validate_subset(deployment, full)
        return deployment

    print("No deployment catalog provided — using full-catalog.yaml.", flush=True)
    return full


def main() -> None:
    token = os.environ.get('GH_TOKEN', '').strip()
    include_pdfs = os.environ.get('INCLUDE_PDFS', 'false').lower() == 'true'

    catalog = _resolve_catalog()

    with open(_EFFECTIVE_CATALOG, 'w') as f:
        yaml.dump({'documents': catalog}, f, default_flow_style=False, allow_unicode=True)

    os.makedirs('/docs', exist_ok=True)

    for doc in catalog:
        name = doc['name']
        url = doc['url'].rstrip('/')
        dest = f'/docs/{name}'

        clone_url = url
        if token:
            clone_url = url.replace('https://', f'https://x-access-token:{token}@')

        print(f'Cloning {name} ...', flush=True)
        subprocess.run(
            ['git', 'clone', '--depth=1', clone_url, dest],
            check=True,
        )

        # Strip .git — not needed at runtime, saves space
        shutil.rmtree(os.path.join(dest, '.git'), ignore_errors=True)

        if not include_pdfs:
            removed = 0
            for root, _dirs, files in os.walk(dest):
                for fname in files:
                    if fname.lower().endswith('.pdf'):
                        os.remove(os.path.join(root, fname))
                        removed += 1
            if removed:
                print(f'  Removed {removed} PDF file(s)', flush=True)

    print('All docs cloned.', flush=True)


if __name__ == '__main__':
    main()
