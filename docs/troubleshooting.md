# Troubleshooting

[Workshop home](../README.md) · [Setup](00_prework.md) · [API reference](inference.md)

Start with the smallest failing operation. Check the request or application log before creating another resource. When asking for help, include the command, error, time, and request ID if provided. Remove credentials and connection strings.

## Inference

| Symptom | Check | Next action |
|---|---|---|
| Missing environment variable | `.env` exists in the workshop directory | Copy `.env.example` only if needed, fill in the key, and rerun setup |
| `401` | Correct workshop key and base URL | Replace the placeholder; rerun the notebook setup cell without printing the key |
| `404` | Request path and model alias | Use one of the three operations in [the reference](inference.md) |
| `422` | Request fields | Check embedding batch size, supported image size, count, and response format |
| `429` | Shared team usage and retry headers | Wait, then retry with backoff; stop unnecessary parallel requests |
| Timeout or `5xx` | Service availability and request size | Retry a small chat request; contact the organizers if it persists |
| Empty or truncated answer | `finish_reason`, output budget, optional thinking | Reduce input or increase output allowance within the service limit |
| Notebook package import fails | Selected kernel and installation output | Select the workshop environment and rerun the install cell |

A `brain: live` status means the starter has configured its inference client. It does not make a live model call. Use `python -m agent --once "Say hello"` to verify inference.

## Object Storage

| Symptom | Check | Next action |
|---|---|---|
| Access denied | Bucket, endpoint, and key permissions | Use a key scoped to the correct bucket and operation |
| App uses local files | All four required `OBJ_*` connection values | Fill them in, then restart or redeploy |
| File exists but cannot be searched | File extension, text extraction, application log | Use `.md` or `.txt`, or implement the [PDF reader](../agent/README.md#read-other-file-types) |
| Answer does not use the document | Tool log, source text, search description | Check that `search_docs` ran; update the prompt and description for your data |

## PostgreSQL

| Symptom | Check | Next action |
|---|---|---|
| Host does not resolve | Provisioning state and DNS | Wait for the endpoint; rerun `scripts/status.sh` |
| Connection timeout | Current source IP and database allow list | Add the required address while retaining other authorized entries |
| Authentication failure | Host, port, user, encoded password | Refresh connection settings with `scripts/status.sh` |
| Missing `vector` type or table | Schema initialization | Run `python scripts/db_init.py` |
| Application uses process memory | Component status and startup error | Correct the connection and restart; fallback data is not migrated automatically |
| Vector dimension error | Model and database column dimensions | Use the configured model or migrate the schema and re-embed the corpus |

## Deployment

For a Linode:

```bash
ssh root@<linode-ip> "cloud-init status"
ssh root@<linode-ip> "cd /opt/hackmidwest && docker compose ps"
ssh root@<linode-ip> "cd /opt/hackmidwest && docker compose logs --tail=50 agent"
```

For LKE, from the workshop directory:

```bash
export KUBECONFIG="$PWD/hackmidwest-kubeconfig.yaml"
kubectl get nodes
kubectl -n hackmidwest get pods,services
kubectl -n hackmidwest logs deployment/agent --tail=50
kubectl -n hackmidwest get events --sort-by=.metadata.creationTimestamp
```

| Symptom | Likely area to inspect |
|---|---|
| SSH fails | VM boot status, SSH key or agent, firewall rule, intended account |
| `/health` unreachable | Container or pod startup, firewall, Service address, load balancer readiness |
| `/health` returns 200 but chat fails | Inference request, quota, application log, source data |
| LKE pod has invalid credentials | Quotes or inline comments in `.env`; `kubectl --from-env-file` preserves them |
| Works locally but not after deployment | Copied environment, network allow list, dependencies, redeployment |
| Account activation or resource limit error | Cloud Manager account status; organizer or provider support |

After fixing a database connection that failed at startup, restart the application. The starter may already be using its in-process fallback.

If a cloud service is unavailable during the workshop, use the local samples and continue with the notebooks. Return to your chosen component lab when access is restored.
