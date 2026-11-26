\set ON_ERROR_STOP on
insert into stratiq_private.source (id,url,content_sha256,available_at,retrieved_at,license_status)
select (entry->>'source_id')::uuid, 'Synthetic filing', entry->>'sha256',
       '2023-01-01','2023-01-02','research_only'
from jsonb_array_elements(:'payload'::jsonb->'manifest'->'sources') as entry;

begin;
set local role stratiq_assessor;
select stratiq_private.submit_assessment(
    request_id, company_id, methodology_version, cutoff, model_version, manifest, assessments, citations
) from jsonb_to_record(:'payload'::jsonb) as p(
    request_id uuid, company_id uuid, methodology_version text, cutoff timestamptz,
    model_version text, manifest jsonb, assessments jsonb, citations jsonb
);
commit;

set role stratiq_evaluator;
do $$
begin
    if (select count(*) from stratiq_private.assessment
        where snapshot_id = '00000000-0000-0000-0000-000000000030') <> 50 then
        raise exception 'adapter request did not produce a visible sealed snapshot';
    end if;
end;
$$;
reset role;
