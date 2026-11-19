# One image with both halves, for hosts that run a single container (such as Render).
# Next.js serves the pages on $PORT and forwards /api to FastAPI, which listens only inside the container.

FROM node:24-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# The browser calls /api on the same site; the rewrite in next.config.ts forwards it to FastAPI.
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_OUTPUT=standalone \
    NEXT_PUBLIC_API_BASE_URL=/api
RUN npm run build

FROM python:3.12-slim-bookworm AS backend
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app

FROM python:3.12-slim-bookworm
# Node is only needed to run the built Next.js server, so take the binary rather than a full install.
COPY --from=node:24-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=backend /app/backend /app/backend
COPY --from=frontend /app/frontend/.next/standalone /app/frontend
COPY --from=frontend /app/frontend/.next/static /app/frontend/.next/static
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Sessions and the retrieval index live under /data: mount a persistent disk there.
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    APP_ENV=production \
    SESSION_STORE_PATH=/data/sessions \
    CHROMA_PERSIST_DIR=/data/index \
    PORT=10000
EXPOSE 10000
CMD ["/app/start.sh"]
