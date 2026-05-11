# Helm Deployment Track

This chart is a production-shaped starting point for Kubernetes environments.
The current primary server runbook remains `README_ubuntu.md`; use this chart
only after the company platform team confirms Kubernetes is the target.

The chart intentionally does not create secrets. Provide an existing secret via
`existingSecret.name` with the required keys for PostgreSQL, Neo4j, Qdrant,
model gateway, and trusted proxy values.

Validate locally when Helm is available:

```bash
helm lint ops/helm/rune-agent
helm template rune-agent ops/helm/rune-agent \
  --set image.repository=registry.example.com/rune-agent \
  --set image.tag=0.1.0 \
  --set existingSecret.name=rune-agent-secrets
```

Current repo tests validate the chart structure, required templates, and that
the chart does not hardcode secret values. They do not replace `helm lint` in
the target deployment environment.

Platform decisions still required before production rollout:

- ingress and trusted proxy header policy
- secret manager integration and secret key names
- PostgreSQL, Neo4j, Qdrant, and artifact-store endpoints
- scheduler ownership for single-worker, PostgreSQL-lease, or CronJob mode
- backup, restore, and retention jobs
- resource requests and load-test evidence

Charts must not bake in secrets, internal endpoint credentials, or MCP tool
names. Source integration remains configured through source skills and
company-local runtime configuration.
