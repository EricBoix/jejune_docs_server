# jejune\_docs\_server

## Introduction

UI components in the jejune ecosystem need runtime HTTP access to `jj_doc_*` content:
markdown files, PDFs, and sentence chunks extracted from source documents. That content
lives in git repositories with no built-in HTTP interface.

`jejune_docs_server` bridges the gap: at image build time it clones the repositories
listed in a catalog, bakes their content into the image, and serves everything — plus
catalog search — over HTTP using FastAPI. The interactive Swagger UI is included for
exploration and debugging.

## Catalogs

A catalog is a YAML file with a `documents` list, each entry containing at minimum
`name` and `url` fields. It is injected at build time as a Docker secret and is never
baked into a repository layer.

The builder is responsible for providing the catalog via the `CATALOG_FILE` environment
variable. The build fails immediately if `CATALOG_FILE` is not set.

## Use cases

### Docker only (no jejune\_cli)

Set `CATALOG_FILE` to point to your catalog and run:

```sh
CATALOG_FILE=/path/to/catalog.yaml docker compose build
```

Catalog validation is your responsibility before building.

### With jejune\_cli

Use `jejune_cli` to validate the deployment catalog before building:

```sh
jejune catalog check-deployment /path/to/jj_deployments/deploy_<name>
```

Then build with:

```sh
CATALOG_FILE=/path/to/jj_deployments/deploy_<name>/catalog.yaml docker compose build
```

## Prerequisites

- Docker with Compose v2 (`docker compose`)
- A GitHub personal-access token written to `~/.github_token` (needed only for private
  repositories; omit or leave empty for fully public catalogs — the build will only fail
  at clone time if a token is actually required)

## Build

```sh
CATALOG_FILE=/path/to/catalog.yaml docker compose build
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

The service is then reachable at <http://localhost:8765>.

## Swagger UI

Interactive API documentation is available at:

```text
http://localhost:8765/swagger
```

All endpoints, query parameters, and response schemas are listed and executable there.

## API endpoints

| Method | Path                              | Description                                                           |
|--------|-----------------------------------|-----------------------------------------------------------------------|
| `GET`  | `/catalog`                        | List all catalog entries with metadata                                |
| `GET`  | `/catalog/search?q=<term>`        | Case-insensitive substring search across catalog fields               |
| `GET`  | `/docs/{name}/markdown`           | Raw markdown content of the document                                  |
| `GET`  | `/docs/{name}/turtle`             | RDF/Turtle knowledge graph (requires `turtle_file` in `doc.yaml`)     |
| `GET`  | `/docs/{name}/pdf`                | PDF file (requires `INCLUDE_PDFS=true` or `DEV_MODE=true`)            |
| `GET`  | `/docs/{name}/chapters`           | Ordered list of chapters                                              |
| `GET`  | `/docs/{name}/sentences`          | All sentences; filter with `?chapter=`, `?paragraph=`, `?sentence=`  |
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
