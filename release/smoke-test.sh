#!/bin/sh
# Start-up smoke test of an `api` image (ADR 0021).
#
#     release/smoke-test.sh <api image>
#
# `api` refuses to start on a database that is not at the code's migration
# head (ADR 0020), so the test does what an Operator does: it starts the
# PostGIS image of deploy/compose.yaml, runs `tart migrate` from the image in
# a one-shot container, starts `api`, and expects it to serve /api/config. (Not
# /api/health: without a `worker`, its heartbeat check fails it, as it should.) `api`
# also refuses to start without a valid Instance configuration and environment,
# so it gets the tests' fictional configuration directory and a complete one.
# DB_PLATFORM runs the database under another platform (the PostGIS image is
# published for linux/amd64 only, so the arm64 test emulates it).
set -eu

image=$1
compose_file=$(dirname "$0")/../deploy/compose.yaml
db_image=$(sed -n 's|^ *image: \(postgis/postgis:.*\)$|\1|p' "$compose_file")
name=tart-smoke-$$
url=postgresql+asyncpg://postgres:smoke@$name-db:5432/postgres
config=$(cd "$(dirname "$0")/../backend/tests/fixtures/config/valid" && pwd)

cleanup() {
	docker rm --force "$name-db" "$name-api" >/dev/null 2>&1 || true
	docker network rm "$name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$name" >/dev/null
docker run --detach --name "$name-db" --network "$name" ${DB_PLATFORM:+--platform "$DB_PLATFORM"} \
	--env POSTGRES_PASSWORD=smoke "$db_image" >/dev/null

# The image's init phase listens on a Unix socket only, so the first TCP
# connection that succeeds reaches the final server.
tries=0
until docker exec "$name-db" pg_isready --quiet --host 127.0.0.1 --username postgres; do
	tries=$((tries + 1))
	if [ "$tries" -ge 150 ]; then
		echo "smoke test: the database did not start" >&2
		exit 1
	fi
	sleep 2
done

docker run --rm --network "$name" --env DATABASE_URL="$url" "$image" tart migrate
docker run --detach --name "$name-api" --network "$name" --env DATABASE_URL="$url" \
	--volume "$config:/config:ro" --env PUBLIC_BASE_URL=https://smoke.example.org \
	--env SESSION_KEY=smoke-test-session-key-0123456789abcdef --env SMTP_HOST=smtp.example.org \
	--env SMTP_FROM=archive@smoke.example.org \
	--publish 127.0.0.1::8000 "$image" >/dev/null
port=$(docker port "$name-api" 8000/tcp | head -n 1 | sed 's/.*://')

tries=0
until curl --silent --fail --max-time 2 --output /dev/null "http://127.0.0.1:$port/api/config"; do
	tries=$((tries + 1))
	if [ "$tries" -ge 30 ] || [ "$(docker inspect --format '{{.State.Running}}' "$name-api")" != true ]; then
		echo "smoke test: /api/config did not answer" >&2
		docker logs "$name-api" >&2
		exit 1
	fi
	sleep 1
done
echo "smoke test: api started and served /api/config"
