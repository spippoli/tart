# One image for `api` and `worker` (ADR 0004).
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

# go-pmtiles, for `tart tiles update` (Discovery spec, Basemap tiles): BSD-3-Clause, a
# separate program under ADR 0011's tiers. Pinned, and checked against the
# release archives' SHA-256.
FROM python:3.14.8-slim-trixie AS pmtiles
ARG TARGETARCH
ARG PMTILES_VERSION=1.31.2
ARG PMTILES_SHA256_AMD64=3ed7dbf4ec2e6dfe5e25b6f70d1ffc932729f93c86db353bf514dd71010a312f
ARG PMTILES_SHA256_ARM64=f8bd47e7ea866863489cad588fbaf2f31f42e5821f7a03f009b3769f05801cb1
RUN python - <<'EOF'
import hashlib, io, os, tarfile, urllib.request
arch, digest = {
    "amd64": ("x86_64", os.environ["PMTILES_SHA256_AMD64"]),
    "arm64": ("arm64", os.environ["PMTILES_SHA256_ARM64"]),
}[os.environ.get("TARGETARCH") or "amd64"]
version = os.environ["PMTILES_VERSION"]
url = (
    f"https://github.com/protomaps/go-pmtiles/releases/download/v{version}/"
    f"go-pmtiles_{version}_Linux_{arch}.tar.gz"
)
archive = urllib.request.urlopen(url, timeout=120).read()
if hashlib.sha256(archive).hexdigest() != digest:
    raise SystemExit(f"{url}: unexpected SHA-256")
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall("/opt/pmtiles", members=[tar.getmember("pmtiles"), tar.getmember("LICENSE")])
EOF

FROM python:3.14.8-slim-trixie
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=pmtiles /opt/pmtiles/pmtiles /usr/local/bin/pmtiles
COPY --from=pmtiles /opt/pmtiles/LICENSE /usr/local/share/licenses/go-pmtiles/LICENSE
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev
RUN useradd --system --uid 10001 tart \
    && mkdir -p /data/tiles && chown tart /data/tiles
USER tart
EXPOSE 8000
CMD ["uvicorn", "tart.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
