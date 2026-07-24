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

`DockerContext/full-catalog.yaml` is the canonical reference of all known
`jj_doc_*` repositories. It is the default catalog used when no deployment-specific
one is provided.

A deployment-specific catalog is a subset of `full-catalog.yaml`. It lives outside this
repository (typically in `jj_deployments/deploy_<name>/catalog.yaml`) and is injected
at build time as a Docker secret — it is never baked into a repository layer.

Use `jejune_cli` to validate a deployment catalog before building:

```sh
jejune catalog check-deployment /path/to/jj_deployments/deploy_<name>
```

## Prerequisites

- Docker with Compose v2 (`docker compose`)
- A GitHub personal-access token written to `~/.github_token` (needed only for private
  repositories; the file may be empty for fully public catalogs)

## Build

Default build (full catalog):

```sh
docker compose build
```

Deployment-specific build (subset catalog from outside the repo):

```sh
CATALOG_FILE=/path/to/jj_deployments/deploy_<name>/catalog.yaml docker compose build
```

`build_docs.py` validates that the provided catalog is a subset of `full-catalog.yaml`
(names and URLs must match) before cloning anything. The build fails if validation does
not pass.

To include PDF files in the image (excluded by default to keep the image small):

```sh
INCLUDE_PDFS=true docker compose build
# or with a deployment catalog:
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
| `GET`  | `/docs/{name}/pdf`                | PDF file (requires `INCLUDE_PDFS=true` or `DEV_MODE=true`)             |
| `GET`  | `/docs/{name}/chapters`           | Ordered list of chapters                                              |
| `GET`  | `/docs/{name}/sentences`          | All sentences; filter with `?chapter=`, `?paragraph=`, `?sentence=`  |
| `GET`  | `/docs/{name}/sentences/{index}`  | Single sentence by 0-based array index                                |

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
