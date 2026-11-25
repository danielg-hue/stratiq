create function stratiq_private.submit_assessment(
    request_id uuid, company_id uuid, methodology_version text,
    cutoff timestamptz, model_version text, manifest jsonb,
    assessments jsonb, citations jsonb
) returns uuid
language plpgsql
security definer
set search_path = pg_catalog
set timezone = 'UTC'
as $$
declare
    payload jsonb;
    inserted_id uuid;
begin
    if request_id is null or company_id is null or methodology_version is null
        or cutoff is null or not isfinite(cutoff) or cutoff > statement_timestamp()
        or nullif(btrim(model_version), '') is null
        or jsonb_typeof(manifest) is distinct from 'object'
        or jsonb_typeof(assessments) is distinct from 'array'
        or jsonb_typeof(citations) is distinct from 'array' then
        raise exception 'invalid assessment submission' using errcode = '22023';
    end if;
    if jsonb_array_length(assessments) <> 50
        or jsonb_array_length(citations) > 500
        or pg_column_size(manifest) + pg_column_size(assessments) + pg_column_size(citations) > 1048576 then
        raise exception 'invalid assessment submission size' using errcode = '22023';
    end if;
    if current_setting('transaction_isolation') <> 'read committed' then
        raise exception 'read committed required';
    end if;

    payload := jsonb_build_object(
        'manifest', manifest,
        'submission_sha256', encode(sha256(convert_to(jsonb_build_array(
            company_id, methodology_version, cutoff, model_version, manifest, assessments, citations
        )::text, 'UTF8')), 'hex')
    );

    insert into stratiq_private.snapshot as s (id, company_id, version, as_of, model_version, input_manifest)
    values (request_id, company_id, methodology_version, cutoff, model_version, payload)
    on conflict (id) do nothing
    returning s.id into inserted_id;

    if inserted_id is null then
        if exists (
            select 1 from stratiq_private.snapshot s
            join stratiq_private.snapshot_seal seal on seal.snapshot_id = s.id
            where s.id = request_id and s.input_manifest = payload
        ) then
            return request_id;
        end if;
        raise exception 'assessment request identifier already in use' using errcode = '23505';
    end if;

    insert into stratiq_private.assessment (snapshot_id, element, status, score, rationale)
    select request_id, a.element, a.status, a.score, a.rationale
    from jsonb_to_recordset(assessments) as a(element text, status text, score numeric, rationale text);

    insert into stratiq_private.evidence (snapshot_id, element, source_id, locator)
    select request_id, e.element, e.source_id, e.locator
    from jsonb_to_recordset(citations) as e(element text, source_id uuid, locator text);

    insert into stratiq_private.snapshot_seal (snapshot_id) values (request_id);
    return request_id;
end;
$$;
revoke all on function stratiq_private.submit_assessment(uuid, uuid, text, timestamptz, text, jsonb, jsonb, jsonb)
    from public, anon, authenticated, service_role;
grant execute on function stratiq_private.submit_assessment(uuid, uuid, text, timestamptz, text, jsonb, jsonb, jsonb)
    to stratiq_assessor;

-- Deferred checks run at commit under the calling worker's effective role.
-- This trigger needs read access to the private evidence table at that point.
create or replace function stratiq_private.require_evidence()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog
as $$
begin
    if new.status = 'assessed' and not exists (
        select 1 from stratiq_private.evidence
        where snapshot_id = new.snapshot_id and element = new.element
    ) then
        raise exception 'scored element requires evidence';
    end if;
    return null;
end;
$$;
revoke all on function stratiq_private.require_evidence()
    from public, anon, authenticated, service_role, stratiq_assessor, stratiq_evaluator, stratiq_outcome_ingest;
