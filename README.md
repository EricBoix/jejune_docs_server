# jejune\_docs\_server<!-- omit in toc -->

## Table of content<!-- omit in toc -->

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Build](#build)
- [Run](#run)
- [Swagger UI](#swagger-ui)
- [API endpoints](#api-endpoints)
- [Health check](#health-check)
- [Development mode](#development-mode)

## Introduction

UI components in the jejune ecosystem need runtime HTTP access to `jejune_doc_*` documents content: markdown files, PDFs, and sentence chunks extracted from source documents. That content
lives in git repositories with no built-in HTTP interface.

`jejune_docs_server` bridges the gap: at image build time it clones the repositories
listed in a catalog, bakes their content into the image, and serves everything — plus
catalog search — over HTTP using FastAPI. The interactive Swagger UI is included for
exploration and debugging.

## Prerequisites

- Docker with Compose v2 (`docker compose`)
- A (jejune) catalog file
- Associated git access tokens (only for a catalog accessing private jejune_doc_* repositories)

### Catalog

A catalog is a YAML file with a list of (jejune) `documents`, each entry containing at minimum `name` and `url` fields (refer to [https://github.com/EricBoix/jejune_cli/jejune_cli/schema/doc.yaml] for a simplified schema). The catalog content is injected at container build time.

The component builder is responsible for providing the catalog (which is mandatory for building) via the `CATALOG_FILE` environment variable.

#### Defaulting the catalog with jejune\_cli

If you wish to test the component and have no documents catalog at hand generate one with `jejune_cli` with

```bash
jejune catalog sample    # Creates catalog.yaml
```

Then use `jejune_cli` to validate that catalog before building:

```sh
jejune catalog test catalog.yaml
```

### Git token

GH_TOKEN_FILE=~/.github_token

## Build

Before building assert the catalog is valid (easier with `jejune_cli` but this is another use case).

Set `CATALOG_FILE` to point to your catalog and run:

```sh
CATALOG_FILE=`pwd`/catalog.yaml docker compose build
```

To use a specific token file:

```sh
GH_TOKEN_FILE=~/.github_token CATALOG_FILE=/path/to/catalog.yaml docker compose build
```

To include PDF files in the image (excluded by default to keep the image small):

```sh
CATALOG_FILE=... INCLUDE_PDFS=true docker compose build
```

## Run

```sh
docker compose up
```

The service is then reachable at <http://localhost:8765>, where a catalog summary landing page
lists every document and the file types available for it.



## Swagger UI

Interactive API documentation is available at:

```text
http://localhost:8765/swagger
```

All endpoints, query parameters, and response schemas are listed and executable there.

## API endpoints

| Method | Path                              | Description                                                           |
|--------|-----------------------------------|-----------------------------------------------------------------------|
| `GET`  | `/`                               | Catalog summary landing page (HTML)                                   |
| `GET`  | `/catalog`                        | List all catalog entries with metadata                                |
| `GET`  | `/catalog/search?q=<term>`        | Case-insensitive substring search across catalog fields               |
| `GET`  | `/docs/{name}/markdown`           | Raw markdown content of the document                                  |
| `GET`  | `/docs/{name}/turtle`             | RDF/Turtle knowledge graph (requires `turtle_file` in `doc.yaml`)     |
| `GET`  | `/docs/{name}/pdf`                | PDF file (requires `INCLUDE_PDFS=true` or `DEV_MODE=true`)            |
| `GET`  | `/docs/{name}/chapters`           | Ordered list of chapters                                              |
| `GET`  | `/docs/{name}/sentences`          | All sentences; filter with `?chapter=`, `?paragraph=`, `?sentence=`   |
| `GET`  | `/docs/{name}/sentences/{index}`  | Single sentence by 0-based array index                                |

## Health check

Install the check package once (requires `jejune_cli` to be installed):

```sh
pip install -e check/
```

Then probe a running container:

```sh
python -m jejune_docs_server_check status
```

The default port is `8765`. Override with `DOCS_SERVER_PORT`:

```sh
DOCS_SERVER_PORT=9000 python -m jejune_docs_server_check status
```

## Development mode

To iterate without rebuilding the image, mount a local docs tree and enable dev mode
by uncommenting the relevant block in `docker-compose.yml`:

```yaml
environment:
  DEV_MODE: "true"
  DEV_DOCS_MOUNT: /docs-mount
volumes:
  - ${JEJUNE_ROOT_DIR}:/docs-mount:ro
```

In dev mode the service reads documents from `/docs-mount` instead of the baked-in
`/docs` layer, and PDF access is unrestricted regardless of `INCLUDE_PDFS`.
