# Guide 05 (optional): Reflexes with Valkey

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)  --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This module looks at the **reflexes**: Valkey, the in-memory store running next to the agent on your Linode since guide 03.

## Overview

Some things should happen fast and without thinking. Valkey, the open source in-memory key-value store that forked from Redis, handles two of them for the agent:

- **An embedding cache.** Every question becomes a vector before the search. The vector for the same text is always the same, so the agent keeps it in Valkey for a day and skips the embedding request when the question repeats.
- **A rate limit.** Your team shares 60 requests a minute on the inference endpoint. One browser tab sending messages in a loop could spend all of it. Valkey counts each conversation's messages per minute and the agent refuses the 21st.

Valkey already runs in Docker Compose on your Linode, so there is nothing to create. You will look inside it, trip the rate limit, and read the code.

Akamai also offers Valkey as a Managed Database. It is in limited availability, runs on dedicated plans only, and the smallest plan costs $59 a month (checked 2026-10-02 with the public API). A container costs nothing extra, which is why the kit uses one.

## Learning objectives

By the end of this module you will be able to:

- Find Valkey in the agent's status and look at its keys
- Show the rate limit refusing a conversation with HTTP 429
- Read the 40 lines of `agent/cache.py` and change the limit
- Run Valkey on your laptop for local development
- Decide when a managed Valkey is worth $59 a month

## Prerequisites

- [Guide 03](03_body.md) done, with `LINODE_IP` set to your Linode's address
- About 15 minutes

## Step 1: Find the reflexes in the status

```bash
curl -s http://$LINODE_IP:8000/health
```

The last role in the reply is Valkey:

```json
"reflexes":{"state":"live","detail":"Valkey 8.1.10 at valkey:6379: embedding cache, 20 messages a minute per session"}
```

`valkey:6379` is the container's name on the Compose network. Only the agent can reach it.

## Step 2: Look inside Valkey

Ask the agent a question or two in the chat page, then list Valkey's keys from the Linode:

```bash
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose exec -T valkey valkey-cli --scan"
```

```
rate:judge-demo:29848408
rate:web-before-restart:29848409
vector:hackathon-embedding:<64 hexadecimal characters>
vector:hackathon-embedding:<64 hexadecimal characters>
```

That is part of the list from the test run on 2026-10-02, with the long hashes replaced. Your session names and hashes differ. A `rate:` key counts one conversation's messages in one minute; the number at the end is that minute, counted since 1970. Each counter expires 60 seconds after its first message. A `vector:` key holds the vector of one question text, named by the SHA-256 hash of the text, and expires after a day.

## Step 3: Trip the rate limit

Send 21 messages from one conversation as fast as you can. Each of the first 20 costs one model request, so keep the message short:

```bash
for i in $(seq 1 21); do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://$LINODE_IP:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": "rate-demo", "message": "Reply with the single word OK."}'
done; echo
```

```
200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 429
```

The 21st message got HTTP 429 Too Many Requests, and the model never saw it. The body explains:

```json
{"detail":"This conversation sent 20 messages in the last minute. Wait a moment and try again."}
```

Other conversations are not affected. If the loop crosses into a new minute, the count starts over and all 21 succeed; run it again.

## Step 4: Read the code you just used

Open `agent/cache.py`:

```python
class Valkey:
    state = "live"

    def __init__(self, url: str):
        import redis  # Valkey speaks the Redis protocol, so the redis package works unchanged

        self.db = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        server = self.db.info("server")
        version = server.get("valkey_version") or server.get("redis_version")
        self.detail = f"Valkey {version} at {host_of(url)}: embedding cache, {RATE_LIMIT} messages a minute per session"

    def get_vector(self, model: str, text: str) -> list[float] | None:
        cached = self.db.get(_vector_key(model, text))
        return json.loads(cached) if cached else None

    def set_vector(self, model: str, text: str, vector: list[float]) -> None:
        self.db.set(_vector_key(model, text), json.dumps(vector), ex=VECTOR_TTL)

    def allow(self, session_id: str) -> bool:
        """Count this session's messages in the current minute. True while the count is within the limit."""
        key = f"rate:{session_id}:{int(time.time() // 60)}"
        count = self.db.incr(key)
        if count == 1:
            self.db.expire(key, 60)
        return count <= RATE_LIMIT
```

`allow()` is a fixed-window counter: `INCR` adds one and returns the new count in a single step, so two requests at the same moment cannot both read 19. The first message of each minute sets the key to expire after 60 seconds, so old counters clean themselves up. `get_vector()` and `set_vector()` store each vector as JSON, keyed by model and text, with `ex=VECTOR_TTL` so cached vectors expire after a day.

The brain calls `allow()` before anything else in `Brain.chat()`, and `Embedder.one()` in `knowledge.py` checks the cache before it calls the embedding model. Change `RATE_LIMIT` at the top of `cache.py` to change the limit, then redeploy with the `scp` and `docker compose up -d --build` commands from guide 03.

## Step 5 (optional): Valkey on your laptop

With Docker Desktop installed, start Valkey and point the agent at it:

```bash
docker run -d --name valkey -p 127.0.0.1:6379:6379 valkey/valkey:8
```

Set `VALKEY_URL=redis://localhost:6379/0` in `.env`, then:

```bash
python -m agent --once "Say hello"
```

```
reflexes   live      Valkey 8.1.10 at localhost:6379: embedding cache, 20 messages a minute per session
```

Your version number may be newer. The `-p 127.0.0.1:6379:6379` part publishes Valkey on your laptop only, not on the venue network. Stop it with `docker rm -f valkey` and empty `VALKEY_URL` again.

## When to switch to managed Valkey

Keep the container while the cache and the counters are the only things in Valkey. Losing them on a restart costs a few embedding requests and resets the counters. Move to a Managed Database for Valkey when you store data you cannot lose, such as user sessions, a job queue, or a leaderboard, or when two Linodes need to share it. Managed Valkey is in limited availability, and the docs say CLI support is not available yet, so you create it in Cloud Manager.

## Validation

- `/health` shows `reflexes` as `live`.
- `valkey-cli --scan` on the Linode lists `rate:` and `vector:` keys.
- The 21-message loop ends with `429`.

**Show the judges:** the `reflexes live` line on the chat page and at `/health`, and the 429 from step 3. Valkey runs on the Linode, so the Linode in Cloud Manager, **Linodes**, is the Akamai service behind it.

## Clean up

Nothing extra to delete. Valkey runs inside the Linode from guide 03 and goes away with it. If you started Valkey on your laptop in step 5, run `docker rm -f valkey`.

## Next steps

Change the limit, cache something else you compute often, or store your own data in Valkey with the same `redis` client. For a second way to run the body, try guide 04 on LKE (coming next).
