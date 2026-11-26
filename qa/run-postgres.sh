#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
container="stratiq-regression-$$"
trap 'docker stop "$container" >/dev/null 2>&1 || true' EXIT
export POSTGRES_PASSWORD
POSTGRES_PASSWORD="$(openssl rand -hex 24)"
docker run --rm -d --name "$container" -e POSTGRES_PASSWORD     -e 'POSTGRES_INITDB_ARGS=--auth-local=trust --auth-host=scram-sha-256'     postgres:17 -c listen_addresses=localhost >/dev/null
unset POSTGRES_PASSWORD
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
psql_qa < "$repo/qa/assessment-worker.sql"

worker_password="$(openssl rand -hex 24)"
printf '%s\n%s\n' "$worker_password" "$worker_password" |     docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -c '\password stratiq_assessment_worker'
if denied="$(PGPASSWORD=incorrect docker exec -e PGPASSWORD "$container"     psql -h 127.0.0.1 -XAt -U stratiq_assessment_worker -d postgres -c 'select 1' 2>&1)"; then
    echo 'Worker accepted an incorrect password.' >&2
    exit 1
fi
[[ "$denied" == *'password authentication failed'* ]]
PGPASSWORD="$worker_password" docker exec -i -e PGPASSWORD "$container"     psql -h 127.0.0.1 -X -q -v ON_ERROR_STOP=1 -U stratiq_assessment_worker -d postgres     < "$repo/qa/second-user.sql"
unset worker_password
sealed_count="$(docker exec "$container" psql -XAt -U postgres -c "select count(*) from stratiq_private.snapshot_seal where snapshot_id='00000000-0000-0000-0000-000000000040'")"
[[ "$sealed_count" = 1 ]]
echo 'Second-user SCRAM login and sealed submission passed.'
