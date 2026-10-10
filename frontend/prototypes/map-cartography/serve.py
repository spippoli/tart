#!/usr/bin/env python3
"""PROTOTYPE (issue #36), throwaway. Serves the map cartography prototype.

Run:  python3 frontend/prototypes/map-cartography/serve.py
Open: http://localhost:8036/?variant=A

PMTiles needs HTTP Range requests, which `python -m http.server` does not
support, so this adds them. On first run it downloads the Rome extract
(about 47 MB) with the go-pmtiles CLI if `rome.pmtiles` is missing.
"""
import http.server
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8036"))
PMTILES = os.path.join(HERE, "rome.pmtiles")
BUILD = "https://build.protomaps.com/20261009.pmtiles"
BBOX = "12.23,41.65,12.86,42.08"


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else size - int(m.group(2))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        outputfile.write(source.read(remaining))
        self._remaining = None


def ensure_tiles():
    if os.path.exists(PMTILES):
        return
    cli = shutil.which("pmtiles")
    if not cli:
        sys.exit(
            "rome.pmtiles is missing. Install go-pmtiles "
            "(https://github.com/protomaps/go-pmtiles/releases) and re-run, or run:\n"
            f"  pmtiles extract {BUILD} {PMTILES} --bbox={BBOX}"
        )
    subprocess.run([cli, "extract", BUILD, PMTILES, f"--bbox={BBOX}"], check=True)


if __name__ == "__main__":
    ensure_tiles()
    print(f"Map cartography prototype: http://localhost:{PORT}/?variant=A")
    http.server.ThreadingHTTPServer(("", PORT), RangeHandler).serve_forever()
