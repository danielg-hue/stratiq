set local lock_timeout = '2s';
create index assessment_element_idx on stratiq_private.assessment (element);
create index evidence_source_id_idx on stratiq_private.evidence (source_id);
create index experiment_version_idx on stratiq_private.experiment (version);
create index snapshot_company_id_idx on stratiq_private.snapshot (company_id);
create index snapshot_version_idx on stratiq_private.snapshot (version);
create index source_supersedes_idx on stratiq_private.source (supersedes);
