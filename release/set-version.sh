#!/bin/sh
# Writes a release version into both project files (and the backend's lock
# file, which records it), in the release job's workspace only: the release
# never commits it, and the repository stays at 0.0.0 (ADR 0021).
#
#     release/set-version.sh <version> [<repository root>]
set -eu

version=$1
root=${2:-$(dirname "$0")/..}

uv version "$version" --no-sync --directory "$root/backend"
cd "$root/frontend"
npm pkg set "version=$version"
