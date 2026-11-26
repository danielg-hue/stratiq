\set ON_ERROR_STOP on
do $$
begin
    if session_user <> 'stratiq_assessment_worker' or current_user <> session_user then
        raise exception 'expected an independently authenticated worker session';
    end if;
    if has_schema_privilege(current_user, 'stratiq_private', 'USAGE') then
        raise exception 'worker has private schema access before role assumption';
    end if;
    begin
        set role stratiq_evaluator;
        raise exception 'worker can assume evaluator role';
    exception when insufficient_privilege then null;
    end;
end;
$$;
begin;
set local role stratiq_assessor;
do $$
begin
    if current_user <> 'stratiq_assessor' then
        raise exception 'assessor role was not assumed';
    end if;
    if has_table_privilege(current_user, 'stratiq_private.outcome', 'SELECT')
        or has_table_privilege(current_user, 'stratiq_private.source', 'SELECT')
        or has_table_privilege(current_user, 'stratiq_private.snapshot', 'INSERT') then
        raise exception 'assessor has unwanted direct table access';
    end if;
end;
$$;
select stratiq_private.submit_assessment(
    '00000000-0000-0000-0000-000000000040', '00000000-0000-0000-0000-000000000001',
    'qa-1', '2020-02-01', 'qa-worker-login',
    jsonb_build_object('sources', jsonb_build_array(
        jsonb_build_object('source_id', '00000000-0000-0000-0000-000000000001', 'sha256', repeat('a', 64)))),
    jsonb_agg(jsonb_build_object('element', element, 'score', 1, 'status', 'assessed', 'rationale', 'test') order by element),
    jsonb_agg(jsonb_build_object('element', element, 'source_id', '00000000-0000-0000-0000-000000000001',
                                'locator', 'test') order by element)
) from stratiq_private.element_registry;
commit;
do $$
begin
    if current_user <> session_user or has_schema_privilege(current_user, 'stratiq_private', 'USAGE') then
        raise exception 'assessor rights remained after commit';
    end if;
end;
$$;
