create role stratiq_assessment_worker login noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls connection limit 2 password null;
grant stratiq_assessor to stratiq_assessment_worker with inherit false, set true, admin false;
