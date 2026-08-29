-- Select AI setup for HealthInsight MVP.
--
-- Auth path: OCI Resource Principal (no API key credential needed). The
-- healthinsightdb ADB's dynamic group (healthinsightdb-dynamic-group) is
-- granted `use generative-ai-family` in the tenancy via IAM policy
-- healthinsightdb-genai-policy. This lets the database call OCI
-- Generative AI as itself.
--
-- Verified empirically against the live healthinsightdb ADB
-- (Oracle Database 19c Autonomous, sa-saopaulo-1). The brief's original
-- sketch (DBMS_CLOUD.CREATE_CREDENTIAL with a `comp_ocid` param) does NOT
-- work on this DB version -- that params overload only accepts
-- {aws_role_arn, gcp_oauth2, oauth2, secret_id, auth_method}, and
-- auth_method does not accept 'resource_principal' as a value either
-- (ORA-20041 both times). The correct mechanism is
-- DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL, which creates the reserved
-- OCI$RESOURCE_PRINCIPAL credential automatically.

-- Step 1: enable resource principal auth. This creates a credential named
-- OCI$RESOURCE_PRINCIPAL owned by the current user (ADMIN). Verified
-- idempotent -- re-running this after the credential already exists
-- succeeds silently (no error).
BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL();
END;
/

-- Step 2: create the Select AI profile scoped to the 3 project tables.
--
-- IMPORTANT: "region" must be set explicitly to the ADB's OWN home region
-- (sa-saopaulo-1), not left to default (which resolves to us-chicago-1)
-- and not set to any other explicit region (eu-frankfurt-1 was also
-- tried). Any region other than the ADB's own home region hits a
-- reproducible product bug where DBMS_CLOUD_AI cannot resolve the
-- Generative AI inference hostname and fails with:
--   ORA-20404: Object not found -
--   https://inference.generativeai.<region>.oci.my$cloud_domain/20231130/actions/chat
-- (the "my$cloud_domain" segment is a literal, unsubstituted template
-- placeholder -- this matches other reports of the same exact string on
-- Oracle's own community forum, so it looks like a genuine platform bug
-- tied to resource-principal auth rather than anything wrong with this
-- profile's attributes). Neither adding "oci_compartment_id" nor
-- changing "model" changed this behavior -- only region=sa-saopaulo-1
-- (the ADB's own region, from v$pdbs.cloud_identity) made GENERATE work.
-- No explicit "model" attribute is needed; the OCI provider default
-- model works.
BEGIN
  DBMS_CLOUD_AI.DROP_PROFILE(profile_name => 'HEALTHINSIGHT_PROFILE', force => true);
EXCEPTION
  WHEN OTHERS THEN NULL; -- profile may not exist yet
END;
/

BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'HEALTHINSIGHT_PROFILE',
    attributes   => '{
      "provider": "oci",
      "credential_name": "OCI$RESOURCE_PRINCIPAL",
      "object_list": [
        {"owner": "ADMIN", "name": "ESTABELECIMENTOS"},
        {"owner": "ADMIN", "name": "PROCEDIMENTOS"},
        {"owner": "ADMIN", "name": "INTERNACOES"}
      ],
      "region": "sa-saopaulo-1"
    }'
  );
END;
/

-- Step 3: verification -- ask a real natural-language question against
-- the live data. Expected: a JSON result with the actual row count from
-- internacoes (135507 rows as of the initial ETL load).
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt       => 'Quantas internacoes existem no total?',
  profile_name => 'HEALTHINSIGHT_PROFILE',
  action       => 'runsql'
) FROM dual;
