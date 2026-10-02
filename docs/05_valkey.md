# Lab: Inspect the Valkey cache and rate limit

[Workshop home](../README.md) · [Cloud essentials](cloud.md)

**Result:** identify cached embeddings and observe the application's session counter.

**Prerequisites:** the [Linode lab](03_body.md) or [LKE lab](04_lke.md). Allow about 10–15 minutes. Valkey already runs beside the application, so this lab creates no additional cloud resource.

The starter uses a Valkey container for two tasks: cache an embedding for repeated text and count requests within a session. This is self-hosted Valkey on your compute, separate from Akamai's Managed Valkey offering.

## 1. Check the service

For the Linode deployment, set the address printed by the deployment script:

```bash
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
LINODE_IP=${LINODE_IP%% *}
curl -fsS "http://$LINODE_IP:8000/health"
```

The existing `reflexes` status field describes Valkey, the embedding cache, and the limit of 20 messages per minute per session. In this codebase, that field is a compatibility label for the cache and counters.

## 2. Inspect keys after a request

```bash
curl -fsS "http://$LINODE_IP:8000/chat" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"valkey-demo","message":"Where can I park?"}'
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose exec -T valkey valkey-cli --scan"
```

For LKE, make the chat request to the NodeBalancer address and list keys with:

```bash
kubectl -n hackmidwest exec deployment/valkey -- valkey-cli --scan
```

Look for `rate:valkey-demo:<minute>` and `vector:hackathon-embedding:<hash>`. The rate counter expires after 60 seconds; cached embeddings expire after a day. Repeated text can reuse a cached vector while the model configuration remains the same. Changing the backing embedding model requires invalidating old vectors and cache entries.

## 3. Inspect the counter without sending model requests

The following runs the application's limiter directly on the Linode. It uses a fresh session and does not call inference:

```bash
ssh root@$LINODE_IP 'cd /opt/hackmidwest && docker compose exec -T agent python -' <<'PYCODE'
import time
from uuid import uuid4
from agent.cache import Valkey

cache = Valkey("redis://valkey:6379/0")
session = "limit-check-" + uuid4().hex
minute = int(time.time() // 60)
allowed = [cache.allow(session) for _ in range(21)]
if int(time.time() // 60) != minute:
    print("The minute changed during the check. Run it again.")
else:
    print("Allowed:", sum(allowed), "Refused:", len(allowed) - sum(allowed))
PYCODE
```

Within one minute window, expect `Allowed: 20 Refused: 1`. [agent/server.py](../agent/server.py) maps a refused chat request to HTTP 429. This exercise avoids spending the team's inference quota on a burst of chat requests.

For LKE, use `kubectl -n hackmidwest exec -i deployment/agent -- python -` with the same Python body.

## 4. Understand the limits

[agent/cache.py](../agent/cache.py) defines `RATE_LIMIT`, `VECTOR_TTL`, and the fixed-minute counter. A client can choose a different session ID, so this is not an account-level abuse control. The application permits requests if Valkey fails, and its cache misses then fall back to fresh embedding calls.

The container has no persistent volume. Losing cached values is acceptable here because they can be recomputed. Keep durable records in PostgreSQL or another persistent store.

## Clean up

Counter and cache keys expire automatically. The Valkey container is removed with the deployment during [cleanup](costs.md). Its CPU and memory use are part of the VM or worker-node capacity.
