# Helm Deployment Track

Helm packaging is intentionally deferred until the company deployment target is
known.

Current Ubuntu deployment guidance is maintained in:

- `README_ubuntu.md`
- `docs/runbooks/BACKUP_RESTORE.md`
- `ops/rehearsal/check_production_readiness.py`

Before adding charts here, confirm the production platform choices:

- ingress and trusted proxy header policy
- secret manager integration
- PostgreSQL, Neo4j, Qdrant, and artifact-store endpoints
- scheduler ownership for single-worker versus multi-worker deployment
- backup, restore, and retention jobs
- resource requests and load-test evidence

Charts must not bake in secrets, internal endpoint credentials, or MCP tool
names. Source integration remains configured through source skills and
company-local runtime configuration.
