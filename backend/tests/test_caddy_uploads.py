"""Foundations spec, 3. Upload path: Caddy's side of criteria 22 and 51.

The deploy/Caddyfile served by the Caddy image of deploy/compose.yaml, in front of a
stand-in `api` that reads whatever body it gets and answers with its length.
"""

import http.client
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import wait_for_http
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

DEPLOY = Path(__file__).parents[2] / "deploy"
# The images of deploy/compose.yaml (Caddy) and of backend/Dockerfile (the stand-in).
CADDY_IMAGE = "caddy:2.11.7-alpine"
STAND_IN_IMAGE = "python:3.14.8-slim-trixie"
MIB = 1024 * 1024

STAND_IN = """
import http.server

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        remaining, read = int(self.headers.get("Content-Length") or 0), 0
        while remaining:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            read += len(chunk)
        body = str(read).encode()
        self.send_response(202)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

http.server.ThreadingHTTPServer(("", 8000), Handler).serve_forever()
"""


def test_compose_runs_the_caddy_image_these_tests_use() -> None:
    compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")

    assert f"image: {CADDY_IMAGE}\n" in compose
    assert "TART_UPLOAD_BODY_LIMIT: ${TART_UPLOAD_BODY_LIMIT:-26MiB}" in compose


@pytest.fixture(scope="module")
def caddy() -> Iterator[tuple[str, int]]:
    """Caddy on plain HTTP with a 2 MiB upload limit (`max_upload_mb = 1`), as host and port."""
    with Network() as network:
        api = (
            DockerContainer(STAND_IN_IMAGE)
            .with_network(network)
            .with_network_aliases("api")
            .with_command(["python", "-c", STAND_IN])
        )
        proxy = (
            DockerContainer(CADDY_IMAGE)
            .with_network(network)
            .with_env("TART_SITE_ADDRESS", ":80")
            .with_env("TART_UPLOAD_BODY_LIMIT", "2MiB")
            .with_volume_mapping(str(DEPLOY / "Caddyfile"), "/etc/caddy/Caddyfile", "ro")
            .with_exposed_ports(80)
        )
        with api, proxy:
            host, port = proxy.get_container_host_ip(), int(proxy.get_exposed_port(80))
            wait_for_http(f"http://{host}:{port}/api/health")
            yield host, port


def _post(caddy: tuple[str, int], path: str, size: int) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection(*caddy, timeout=30)
    try:
        connection.request("POST", path, body=bytes(size), headers={"X-TART-Request": "1"})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_criterion_51_caddy_lets_through_the_limit_plus_its_margin(caddy) -> None:
    assert _post(caddy, "/api/media", 2 * MIB) == (202, str(2 * MIB).encode())


def test_criterion_22_caddy_refuses_a_larger_upload_with_the_error_code(caddy) -> None:
    assert _post(caddy, "/api/media", 2 * MIB + 1) == (413, b'{"code":"file_too_large"}')


def test_the_upload_limit_applies_to_uploads_only(caddy) -> None:
    assert _post(caddy, "/api/auth/code", 2 * MIB + 1)[0] == 202
