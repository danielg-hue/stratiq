#!/usr/bin/env bash
# Run on a disposable database after applying the migrations.
set -euo pipefail
container="${1:?disposable Postgres container name required}"
qa_dir="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
psql_qa() { docker exec -i "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U postgres; }

if [[ "$(echo "select count(*) from stratiq_private.company where id = '00000000-0000-0000-0000-000000000001';" | psql_qa)" = 0 ]]; then
    sed -n '/^insert into stratiq_private.company/,/^set local role/{ /^set local role/d; p; }' "$qa_dir/submission.sql" | psql_qa
fi
cat > "$scratch/submit.sql" <<'SQL'
set local role stratiq_assessor;
select stratiq_private.submit_assessment(
    '00000000-0000-0000-0000-000000000020', '00000000-0000-0000-0000-000000000001',
    'qa-1', '2020-02-01', 'qa', jsonb_build_object('sources', jsonb_build_array(
        jsonb_build_object('source_id','00000000-0000-0000-0000-000000000001','sha256',repeat('a',64)))),
    jsonb_agg(jsonb_build_object('element',element,'score',1,'status','assessed','rationale','test') order by element),
    jsonb_agg(jsonb_build_object('element',element,'source_id','00000000-0000-0000-0000-000000000001','locator','test') order by element)
) from stratiq_private.element_registry;
SQL

{ echo 'begin;'; cat "$scratch/submit.sql"; echo 'select pg_sleep(2); commit;'; } | psql_qa > "$scratch/first" &
first=$!
# Wait until the first worker has inserted its snapshot and holds the transaction open.
for attempt in {1..40}; do
    if [[ "$(echo "select count(*) from pg_stat_activity where query like 'select pg_sleep(2)%' and pid <> pg_backend_pid() and state='active';" | psql_qa)" = 1 ]]; then
        break
    fi
    sleep 0.05
done
[[ "$attempt" -lt 40 ]]
{ echo 'begin;'; cat "$scratch/submit.sql"; echo 'commit;'; } | psql_qa > "$scratch/second"
wait "$first"
expected=00000000-0000-0000-0000-000000000020
[[ "$(head -n1 "$scratch/first")" = "$expected" && "$(cat "$scratch/second")" = "$expected" ]]
[[ "$(echo "select count(*) from stratiq_private.assessment where snapshot_id = '$expected';" | psql_qa)" = 50 ]]
[[ "$(echo "select count(*) from stratiq_private.snapshot_seal where snapshot_id = '$expected';" | psql_qa)" = 1 ]]
echo 'Concurrent identical requests produced one sealed snapshot with 50 assessments.'
