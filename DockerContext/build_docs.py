#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

import yaml

_SECRET_CATALOG = '/run/secrets/catalog'
_EFFECTIVE_CATALOG = '/catalog.yaml'


def main() -> None:
    if not os.path.exists(_SECRET_CATALOG):
        print("Error: no catalog provided. Set CATALOG_FILE before building.", flush=True)
        sys.exit(1)

    with open(_SECRET_CATALOG) as f:
        catalog = yaml.safe_load(f).get('documents', [])

    token = os.environ.get('GH_TOKEN', '').strip()
    include_pdfs = os.environ.get('INCLUDE_PDFS', 'false').lower() == 'true'

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
