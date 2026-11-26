#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
container="stratiq-regression-$$"
trap 'docker stop "$container" >/dev/null 2>&1 || true' EXIT
docker run --rm -d --name "$container" -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17 -c listen_addresses='' >/dev/null
for attempt in {1..60}; do
    if docker exec "$container" pg_isready -h /var/run/postgresql -q &&
        docker exec "$container" sh -c 'test "$(cat /proc/1/comm)" = postgres'; then
        break
    fi
    sleep 0.2
done
[[ "$attempt" -lt 60 ]]
psql_qa() { docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres; }
echo 'create role anon; create role authenticated; create role service_role bypassrls;' | psql_qa
for migration in "$repo"/supabase/migrations/*.sql; do
    { echo 'begin;'; cat "$migration"; echo 'commit;'; } | psql_qa
done
psql_qa < "$repo/qa/submission.sql"
bash "$repo/qa/concurrent-submission.sh" "$container"
payload="$(cd "$repo" && PYTHONDONTWRITEBYTECODE=1 python -c '
import json
from assessment_submission import prepare_submission
from test_assessment_submission import request_for
from test_strategic_report import bundle
data = bundle()
print(json.dumps(prepare_submission(data, request_for(data)), default=str, allow_nan=False))
')"
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -v "payload=$payload" -U postgres < "$repo/qa/adapter-submission.sql"
