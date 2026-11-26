\set ON_ERROR_STOP on
set session authorization stratiq_assessment_worker;
do $$
begin
    if has_schema_privilege(current_user, 'stratiq_private', 'USAGE') then
        raise exception 'worker inherited private schema access';
    end if;
end;
$$;
begin;
set local role stratiq_assessor;
do $$
begin
    if not has_function_privilege(current_user,
        'stratiq_private.submit_assessment(uuid,uuid,text,timestamptz,text,jsonb,jsonb,jsonb)', 'EXECUTE') then
        raise exception 'worker cannot submit after role assumption';
    end if;
    if has_table_privilege(current_user, 'stratiq_private.outcome', 'SELECT')
        or has_table_privilege(current_user, 'stratiq_private.source', 'SELECT') then
        raise exception 'worker can read outcomes or source registry';
    end if;
end;
$$;
rollback;
reset session authorization;
