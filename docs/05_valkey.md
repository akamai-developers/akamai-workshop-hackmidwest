# Guide 05 (optional): Reflexes with Valkey

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)   --tools-->  Object Storage bucket (knowledge)
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
- Read the `Valkey` class in `agent/cache.py` and change the limit
- Run Valkey on your laptop for local development
- Decide when a managed Valkey is worth $59 a month

## Prerequisites

- [Guide 03](03_body.md) done
- About 15 minutes

Set your Linode's address in a variable first. The lookup works in any terminal:

```bash
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
echo $LINODE_IP
```

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

Send one message, then list Valkey's keys from the Linode right away. Run both lines together: the counter for the message expires after 60 seconds.

```bash
curl -s -o /dev/null -X POST http://$LINODE_IP:8000/chat -H "Content-Type: application/json" -d '{"session_id": "valkey-demo", "message": "Where can I park?"}'
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose exec -T valkey valkey-cli --scan"
```

```
rate:valkey-demo:29848454
vector:hackathon-embedding:<64 hexadecimal characters>
```

That is part of the list from a test run on 2026-10-02, with the long hash replaced. Earlier chats add more keys. `rate:valkey-demo:29848454` counts the messages of the `valkey-demo` conversation in one minute; the number at the end is that minute, counted since 1970. `vector:hackathon-embedding:...` holds the vector for the text "Where can I park?", named by the SHA-256 hash of that text, and expires after a day. Ask the same question again within a day and the agent skips the embedding request.

## Step 3: Trip the rate limit

Send 21 messages from one conversation at the same moment. The `&` starts each request in the background, so all 21 land within the same minute, and `sort | uniq -c` counts the answers by status code:

```bash
for i in $(seq 1 21); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://$LINODE_IP:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": "rate-demo", "message": "Reply with the single word OK."}' &
done | sort | uniq -c
```

```
     20 200
      1 429
```

Twenty messages got an answer and one got HTTP 429 Too Many Requests without reaching the model. Its body says why:

```json
{"detail":"This conversation sent 20 messages in the last minute. Wait a moment and try again."}
```

Other conversations are not affected. The 20 answered messages each cost one model request, a third of your team's 60 a minute, so run this once.

## Step 4: Read the code you just used

Open `agent/cache.py`:

```python
class Valkey:
    state = "live"

    def __init__(self, url: str):
        self.db = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        server = self.db.info("server")
        version = server.get("valkey_version") or server.get("redis_version")
        self.detail = f"Valkey {version} at {host_of(url)}: embedding cache, {RATE_LIMIT} messages a minute per session"

    # If Valkey stops answering, each method below acts like Off: a cache miss, and every message allowed.
    def get_vector(self, model: str, text: str) -> list[float] | None:
        try:
            cached = self.db.get(_vector_key(model, text))
        except redis.RedisError:
            return None
        return json.loads(cached) if cached else None

    def set_vector(self, model: str, text: str, vector: list[float]) -> None:
        try:
            self.db.set(_vector_key(model, text), json.dumps(vector), ex=VECTOR_TTL)
        except redis.RedisError:
            pass

    def allow(self, session_id: str) -> bool:
        """Count this session's messages in the current minute. True while the count is within the limit."""
        key = f"rate:{session_id}:{int(time.time() // 60)}"
        try:
            count = self.db.incr(key)
            if count == 1:
                self.db.expire(key, 60)
        except redis.RedisError:
            return True
        return count <= RATE_LIMIT
```

`allow()` is a fixed-window counter: `INCR` adds one and returns the new count in a single step, so two requests at the same moment cannot both read 19. The first message of each minute sets the key to expire after 60 seconds, so old counters clean themselves up. `get_vector()` and `set_vector()` store each vector as JSON, keyed by model and text, with `ex=VECTOR_TTL` so cached vectors expire after a day.

`redis` is the Python package for Redis. Valkey speaks the same protocol, so the package works unchanged. The three methods after `__init__()` catch `redis.RedisError`, so if the Valkey container stops while the agent runs, the agent keeps answering without a cache or a rate limit.

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
- Step 2 lists a `vector:` key for the question you sent. `rate:` keys show only within a minute of a message.
- The 21-message loop counts 20 answers with `200` and one `429`.

**Show the judges:** the `reflexes live` line on the chat page and at `/health`, and the 429 from step 3. Valkey runs on the Linode, so the Linode in Cloud Manager, **Linodes**, is the Akamai service behind it.

## Clean up

Nothing extra to delete. Valkey runs inside the Linode from guide 03 and goes away with it. If you started Valkey on your laptop in step 5, run `docker rm -f valkey`.

## Next steps

Change the limit, cache something else you compute often, or store your own data in Valkey with the same `redis` client. For a second way to run the body, try [guide 04 on LKE](04_lke.md).
