\set ON_ERROR_STOP on
begin;
insert into stratiq_private.company (id, legal_name) values ('00000000-0000-0000-0000-000000000001','Synthetic');
insert into stratiq_private.methodology values ('qa-1','{}','2020-01-01');
insert into stratiq_private.source (id,url,content_sha256,available_at,retrieved_at,license_status)
values
('00000000-0000-0000-0000-000000000001','https://example.invalid/1',repeat('a',64),'2020-01-01','2020-01-01','research_only'),
('00000000-0000-0000-0000-000000000002','https://example.invalid/2',repeat('b',64),'2021-01-01','2021-01-01','research_only'),
('00000000-0000-0000-0000-000000000003','https://example.invalid/3',repeat('c',64),'2020-01-01','2020-01-01','restricted');
set local role stratiq_assessor;
do $$
declare
    request_id constant uuid := '00000000-0000-0000-0000-000000000010';
    company_id constant uuid := '00000000-0000-0000-0000-000000000001';
    scores jsonb;
    citations jsonb;
    variant jsonb;
    manifest jsonb;
    bad_manifest jsonb;
    expected text;
begin
    begin
        perform 1 from stratiq_private.outcome;
        raise exception 'assessor read outcomes';
    exception when insufficient_privilege then null;
    end;
    begin
        insert into stratiq_private.snapshot (id) values (request_id);
        raise exception 'assessor can write directly';
    exception when insufficient_privilege then null;
    end;
    select jsonb_agg(jsonb_build_object('element',element,'score',1,'status','assessed','rationale','test') order by element),
        jsonb_agg(jsonb_build_object('element',element,'source_id',company_id,'locator','test') order by element)
    into scores,citations from stratiq_private.element_registry;
    manifest := jsonb_build_object('sources', jsonb_build_array(jsonb_build_object('source_id', company_id, 'sha256', repeat('a',64))));
    for variant, expected in
        select * from (values
            ('[]'::jsonb, 'missing evidence'),
            (jsonb_set(citations,'{0,source_id}','"00000000-0000-0000-0000-000000000002"'), 'future evidence'),
            (jsonb_set(citations,'{0,source_id}','"00000000-0000-0000-0000-000000000003"'), 'source license not cleared')
        ) as cases(variant, expected)
    loop
        begin
            perform stratiq_private.submit_assessment(request_id,company_id,'qa-1','2020-02-01','qa',case when variant = '[]'::jsonb then '{"sources":[]}'::jsonb else manifest end,scores,variant);
            raise exception 'incorrectly accepted invalid submission';
        exception when raise_exception then
            if sqlerrm <> expected then raise; end if;
        end;
    end loop;
    for bad_manifest in
        select value from jsonb_array_elements(jsonb_build_array(
            '{}'::jsonb, '{"sources":[]}'::jsonb,
            jsonb_set(manifest, '{sources,0,sha256}', to_jsonb(repeat('f',64))),
            jsonb_set(manifest, '{sources}', (manifest->'sources') || (manifest->'sources')),
            jsonb_set(manifest, '{sources}', (manifest->'sources') || jsonb_build_array(
                jsonb_build_object('source_id','00000000-0000-0000-0000-000000000002','sha256',repeat('b',64))))
        ))
    loop
        begin
            perform stratiq_private.submit_assessment(request_id,company_id,'qa-1','2020-02-01','qa',bad_manifest,scores,citations);
            raise exception 'invalid source manifest accepted';
        exception when invalid_parameter_value then null;
        end;
    end loop;
    perform stratiq_private.submit_assessment(request_id,company_id,'qa-1','2020-02-01','qa',manifest,scores,citations);
    perform stratiq_private.submit_assessment(request_id,company_id,'qa-1','2020-02-01','qa',manifest,scores,citations);
    begin
        perform stratiq_private.submit_assessment(request_id,company_id,'qa-1','2020-02-01','qa','{"changed":true}',scores,citations);
        raise exception 'changed request accepted';
    exception when unique_violation then null;
    end;
end;
$$;
reset role;
set constraints all immediate;
set local role stratiq_evaluator;
do $$
begin
    if (select count(*) from stratiq_private.assessment where snapshot_id = '00000000-0000-0000-0000-000000000010') <> 50 then
        raise exception 'sealed snapshot not visible to evaluator';
    end if;
    begin
        delete from stratiq_private.assessment;
        raise exception 'evaluator can delete scores';
    exception when insufficient_privilege then null;
    end;
end;
$$;
reset role;
set local role stratiq_outcome_ingest;
insert into stratiq_private.outcome values ('00000000-0000-0000-0000-000000000001','2020-02-01','2021-02-01','2021-02-02','qa',1);
do $$
begin
    begin
        perform 1 from stratiq_private.outcome;
        raise exception 'ingestion role can read outcomes';
    exception when insufficient_privilege then null;
    end;
end;
$$;
reset role;
rollback;

begin isolation level repeatable read;
set local role stratiq_assessor;
do $$
begin
    begin
        perform stratiq_private.submit_assessment(
            '00000000-0000-0000-0000-000000000010','00000000-0000-0000-0000-000000000001',
            'qa-1','2020-02-01','qa','{}',
            (select jsonb_agg('{}'::jsonb) from generate_series(1,50)), '[]');
        raise exception 'repeatable read submission accepted';
    exception when raise_exception then
        if sqlerrm <> 'read committed required' then raise; end if;
    end;
end;
$$;
rollback;
