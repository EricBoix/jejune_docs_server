# Stage 1 — clone doc repos
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyyaml

ARG INCLUDE_PDFS=false
ENV INCLUDE_PDFS=${INCLUDE_PDFS}

COPY --from=catalog_ref full-catalog.yaml /full-catalog.yaml
COPY build_docs.py /build_docs.py

RUN --mount=type=secret,id=gh_token \
    --mount=type=secret,id=catalog \
    GH_TOKEN=$(cat /run/secrets/gh_token 2>/dev/null || true) \
    python3 /build_docs.py

# Stage 2 — runtime
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
