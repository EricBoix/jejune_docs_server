# Stage 1 - clone doc repos
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyyaml

ARG INCLUDE_PDFS=false
ENV INCLUDE_PDFS=${INCLUDE_PDFS}

COPY build_docs.py /build_docs.py

# Private repositories: jejune_cli passes the credentials as the BuildKit secret
# git_credentials (git-credential-store lines, one per private repository);
# public only: nothing is mounted.
# The secret is read-only and git-credential-store rewrites its file: hence the
# copy, removed within the same RUN so that it never reaches an image layer.
RUN --mount=type=secret,id=git_credentials \
    --mount=type=secret,id=catalog \
    set -ex \
    && (cp /run/secrets/git_credentials /tmp/git_credentials || touch /tmp/git_credentials) \
    && GIT_CREDENTIALS_FILE=/tmp/git_credentials python3 /build_docs.py \
    && rm -f /tmp/git_credentials

# Stage 2 - runtime
FROM python:3.12-slim

ARG INCLUDE_PDFS=false
ENV INCLUDE_PDFS=${INCLUDE_PDFS} \
    DEV_MODE=false \
    DEV_DOCS_MOUNT=/docs-mount

RUN pip install --no-cache-dir fastapi uvicorn[standard] pyyaml

COPY --from=builder /docs /docs
COPY --from=builder /catalog.yaml /catalog.yaml
COPY app /app

EXPOSE 8765
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
