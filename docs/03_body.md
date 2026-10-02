# Guide 03: The body on a Linode

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)  --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This guide adds the **body**: a Linode in Seattle behind a Cloud Firewall, running the agent and Valkey with Docker Compose. With it come the **reflexes**, the Valkey container next to the agent.

## Overview

So far the agent runs in your terminal and stops when your laptop sleeps. In this guide it moves to a Linode, a virtual machine in Akamai Cloud, with a public address your teammates and the judges can open in a browser.

Four pieces make that work. A Cloud Firewall lets in SSH and the agent's port and drops everything else. cloud-init, a standard first-boot tool that reads instructions from the Linode's Metadata service, installs Docker. Your code and `.env` travel over SSH, because user data is readable from inside the Linode and is no place for secrets. Docker Compose builds the agent and starts it next to Valkey.

`scripts/deploy_linode.sh`, which runs the same commands, took 3 minutes 9 seconds from start to a working `/health` on 2026-10-02.

## Learning objectives

By the end of this guide you will be able to:

- Create a Cloud Firewall that admits only the ports you name
- Create a Linode that configures itself on first boot with cloud-init
- Add the Linode to the database's allow list
- Copy code and secrets over SSH, and start containers with Docker Compose
- Check the agent through `/health`, `POST /chat`, and its web page
- Explain why secrets go over SSH and never into user data

## Prerequisites

- [Guide 01](01_knowledge.md) and [guide 02](02_memory.md) done. On the 30-minute path without a database, skip step 5.
- An SSH key at `~/.ssh/id_ed25519.pub` (see the [pre-work](00_prework.md), step 6)
- About 20 minutes

Commands in this guide use two shell variables: your laptop's public address and your database's id. Set them first, in the terminal you will use. On the 30-minute path, `DB_ID` comes back empty, which is fine.

```bash
MY_IP=$(curl -s https://api.ipify.org)
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
echo $MY_IP $DB_ID
```

## Step 1: Create the Cloud Firewall

A Cloud Firewall filters traffic before it reaches the Linode. This one drops all inbound traffic except TCP port 22 for SSH and port 8000 for the agent. Outbound traffic is allowed, so the agent can reach the model, the bucket, and the database.

```bash
linode-cli firewalls create \
  --label hackmidwest-fw \
  --rules.inbound_policy DROP \
  --rules.outbound_policy ACCEPT \
  --rules.inbound '[{"label": "ssh-and-agent", "action": "ACCEPT", "protocol": "TCP", "ports": "22,8000", "addresses": {"ipv4": ["0.0.0.0/0"], "ipv6": ["::/0"]}}]' \
  --format id,label,status
```

`--rules.inbound_policy DROP` is the default for anything no rule matches. The one rule accepts ports 22 and 8000 from any address; `0.0.0.0/0` and `::/0` mean every IPv4 and IPv6 address.

```
┌───────────┬────────────────┬─────────┐
│ id        │ label          │ status  │
├───────────┼────────────────┼─────────┤
│ 187247005 │ hackmidwest-fw │ enabled │
└───────────┴────────────────┴─────────┘
```

In Cloud Manager, open **Firewalls**: `hackmidwest-fw` is listed with one inbound rule. Step 3 needs its id; look it up by label:

```bash
FW_ID=$(linode-cli firewalls list --label hackmidwest-fw --text --no-headers --format id)
```

## Step 2: Read the cloud-init file

A new Linode can read user data from the Akamai Metadata service on its first boot, and cloud-init acts on it. Here is the whole file:

```bash
cat deploy/cloud-init.yaml
```

```yaml
#cloud-config
# Runs once, on the Linode's first boot: installs Docker and makes the folder the agent runs from.
# No secrets in here. Anyone on the Linode can read user data, so .env is copied over SSH instead.
package_update: true
packages:
  - docker.io
  - docker-compose-v2
ssh_pwauth: false
runcmd:
  - systemctl enable --now docker
  - mkdir -p /opt/hackmidwest
```

It installs Docker and the Compose plugin from Ubuntu's packages, turns off password logins over SSH, and creates `/opt/hackmidwest`, where your code goes.

## Step 3: Create the Linode

```bash
linode-cli linodes create \
  --label hackmidwest-agent \
  --region us-sea \
  --type g6-standard-1 \
  --image linode/ubuntu24.04 \
  --root_pass "$(openssl rand -base64 32)" \
  --authorized_keys "$(cat ~/.ssh/id_ed25519.pub)" \
  --firewall_id $FW_ID \
  --metadata.user_data "$(base64 < deploy/cloud-init.yaml | tr -d '\n')" \
  --format id,label,status,ipv4
```

The fields that matter: `g6-standard-1` has 1 CPU and 2 GB of memory for $0.018 an hour, enough to build and run the containers. `--root_pass` gets a random password you never use, because you log in with the key from `--authorized_keys`. `--firewall_id` puts the Linode behind the firewall from step 1 from its first second. `--metadata.user_data` must be base64; the `tr` removes line breaks so the command works the same on macOS and Linux.

```
┌───────────┬───────────────────┬──────────────┬──────────────┐
│ id        │ label             │ status       │ ipv4         │
├───────────┼───────────────────┼──────────────┼──────────────┤
│ 107237550 │ hackmidwest-agent │ provisioning │ 198.51.100.7 │
└───────────┴───────────────────┴──────────────┴──────────────┘
```

Keep the address in a variable. This looks it up by label, so it also works in a new terminal:

```bash
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
echo $LINODE_IP
```

In Cloud Manager, open **Linodes**: `hackmidwest-agent` goes from Provisioning to Running in about a minute and a half. Its **Network** tab shows `hackmidwest-fw`.

## Step 4: Wait for cloud-init

Log in and wait for cloud-init to finish. The first time you connect, SSH asks whether to trust the Linode's host key; type `yes`.

```bash
ssh root@$LINODE_IP cloud-init status --wait
```

```
.................................................status: done
```

If SSH says "Connection refused", the Linode is still booting. Try again in 20 seconds. On 2026-10-02, SSH answered 1 minute 39 seconds after the create command and cloud-init finished about 40 seconds later.

## Step 5: Let the Linode into the database

The database still accepts only your laptop. The update below replaces the whole allow list, so it names both addresses.

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$LINODE_IP/32"
linode-cli databases postgresql-view $DB_ID --format allow_list
```

```
┌──────────────────────────────────┐
│ allow_list                       │
├──────────────────────────────────┤
│ 198.51.100.7/32 203.0.113.25/32  │
└──────────────────────────────────┘
```

Skip this step if you have no database.

## Step 6: Copy the code and start the containers

Copy the agent, the sample documents, the container files, and `.env`. The keys travel over SSH, encrypted, and never pass through user data:

```bash
scp -r agent docs Dockerfile compose.yaml .dockerignore .env root@$LINODE_IP:/opt/hackmidwest/
```

Then build the agent's image and start both containers:

```bash
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose up -d --build"
```

```
 agent  Built
 Network hackmidwest_default  Created
 Container hackmidwest-valkey-1  Created
 Container hackmidwest-agent-1  Created
 Container hackmidwest-valkey-1  Started
 Container hackmidwest-agent-1  Started
```

`compose.yaml` describes the two containers:

```yaml
services:
  agent:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      VALKEY_URL: redis://valkey:6379/0  # the valkey service below; this wins over .env
    depends_on:
      - valkey
    restart: unless-stopped

  valkey:
    image: valkey/valkey:8  # no ports line, so only the agent can reach it
    restart: unless-stopped
```

The agent gets its settings from `.env` plus one more, `VALKEY_URL`, which points at the `valkey` container by name. Valkey publishes no port, so the internet cannot reach it, and the firewall would drop it anyway. `restart: unless-stopped` brings both back after a reboot.

## Step 7: Check that it works

`/health` lists every role and where it is connected:

```bash
curl http://$LINODE_IP:8000/health
```

```json
{"status":"ok","brain":{"state":"live","detail":"hackathon-chat at https://ws.akamai-workshops.com/v1"},"knowledge":{"state":"live","detail":"bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com"},"memory":{"state":"live","detail":"PostgreSQL 17.11 at a123456-akamai-prod-1234567-default.g2a.akamaidb.net:15268, pgvector 0.8.6"},"reflexes":{"state":"live","detail":"Valkey 8.1.10 at valkey:6379: embedding cache, 20 messages a minute per session"}}
```

Every role says `live`. If `memory` says `error`, the allow list change from step 5 has not reached the database yet; wait a minute and run `ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose restart agent"`. If `/health` does not answer at all, read the agent's log:

```bash
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose logs agent"
```

Now ask the deployed agent the question you saved from your laptop in guide 02:

```bash
curl -X POST http://$LINODE_IP:8000/chat -H "Content-Type: application/json" \
  -d '{"session_id": "judge-demo", "message": "When is our demo slot?"}'
```

```json
{"reply":"Your demo slot is at 2:15 PM.","tools_used":["recall"]}
```

Your laptop saved that fact and the Linode recalled it, because both talk to the same database. Open `http://<your Linode address>:8000` in a browser for the chat page. It shows the same four roles at the top.

> NOTE: The agent has no login. Anyone who finds this address can chat with it, spend your team's quota, and read the facts it saved. That is fine for a demo; see "What this kit is not" in the [README](../README.md#what-this-kit-is-not).

## Step 8: Read the code you just used

Open `agent/server.py`. The web front is three routes around the same brain the terminal uses:

```python
@app.post("/chat")
def chat(body: ChatRequest, request: Request) -> ChatReply:
    try:
        reply = request.app.state.brain.chat(body.session_id, body.message)
    except RateLimited as error:
        raise HTTPException(status_code=429, detail=str(error))
    except openai.APIError as error:
        raise HTTPException(status_code=502, detail=f"The brain did not answer: {error}")
    return ChatReply(reply=reply.text, tools_used=reply.tools_used)


@app.get("/health")
def health(request: Request) -> dict:
    """Which Akamai services this agent is using right now. Open it in front of the judges."""
    roles = request.app.state.brain.roles()
    return {"status": "ok", **{role: {"state": state, "detail": detail} for role, state, detail in roles}}
```

`POST /chat` takes a session id and a message and returns the reply and the tools the agent used. The page in `agent/static/index.html` keeps one session id per browser in local storage. For your project, add routes here, or call `/chat` from your own frontend. To ship a code change, repeat the `scp` and `docker compose up -d --build` commands from step 6.

## Validation

- `curl http://$LINODE_IP:8000/health` shows four roles, all `live` (or `memory` as `fallback` on the 30-minute path).
- The chat page at `http://<your Linode address>:8000` answers "Where can I park?" from `parking.md`.
- `ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose ps"` shows `agent` and `valkey` up.
- Optional: restart both containers with `ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose restart"`, wait ten seconds, and ask "When is our demo slot?" again. The answer still comes back, from PostgreSQL.

**Show the judges:** open `http://<your Linode address>:8000/health` in front of them. It names the bucket, the database, and Valkey the agent is using. In Cloud Manager, **Linodes** shows `hackmidwest-agent` in Seattle, and **Firewalls** shows `hackmidwest-fw` attached to it.

## Clean up

Look up the ids by label, then delete the Linode first and the firewall second:

```bash
LINODE_ID=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format id)
FW_ID=$(linode-cli firewalls list --label hackmidwest-fw --text --no-headers --format id)
linode-cli linodes delete $LINODE_ID
linode-cli firewalls delete $FW_ID
```

If you keep the database, take the Linode's address off its allow list. Akamai gives freed addresses to other customers. This leaves only your laptop:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32"
```

Cloud Manager's **Linodes** and **Firewalls** pages should no longer list them. Left running, the Linode costs $0.018 an hour, up to $12 a month, even when it is powered off. The firewall is free.

To delete everything from guides 01 to 03 at once, run `bash scripts/down.sh`.

## Next steps

`scripts/deploy_linode.sh` runs steps 1 to 7 for you when you rebuild: it creates or reuses the firewall and the Linode, waits for cloud-init, updates the allow list, copies the code, and waits for `/health`. These are the same commands you just typed, in one file.

Then try an optional module:

- [Guide 04: Kubernetes with LKE](04_lke.md): the same agent on a cluster behind a NodeBalancer
- [Guide 05: Valkey reflexes](05_valkey.md): see the cache and the rate limit at work
