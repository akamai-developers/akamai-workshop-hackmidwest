# Lab: Run the application on a Linode

[Workshop home](../README.md) · [Runtime comparison](cloud.md#choose-a-runtime) · [Project paths](build.md)

**Result:** the starter runs on an Akamai Cloud virtual machine and answers a request from another computer.

**Prerequisites:** [setup](00_prework.md), activated account, CLI permissions, working inference key, and an SSH key. Object Storage and PostgreSQL are optional. Allow about 15–20 minutes plus provisioning delays. This lab creates or reuses a VM and Cloud Firewall.

A Linode is a Linux virtual machine. This deployment uses cloud-init to install Docker, copies your code and `.env` over SSH, then starts the API and a Valkey container with Docker Compose. The models remain on the shared inference service.

## 1. Check the local app and deployment settings

```bash
python -m agent --once "Where can I park?"
```

Inspect [scripts/lib.sh](../scripts/lib.sh), [deploy/cloud-init.yaml](../deploy/cloud-init.yaml), and [compose.yaml](../compose.yaml). Defaults include Seattle, an Ubuntu image, and the `g6-standard-1` plan. The script uses the fixed labels `hackmidwest-agent` and `hackmidwest-fw`; verify that existing resources with these names belong to this workshop before reusing them.

The demo firewall opens SSH on port 22 and the unauthenticated app on port 8000 to the internet. The app uses HTTP. Use fictional documents and facts. Restrict network access or add authentication and HTTPS before using private data or sharing the application more broadly.

## 2. Deploy

```bash
bash scripts/deploy_linode.sh
```

For a different SSH key:

```bash
SSH_KEY=~/.ssh/your_key bash scripts/deploy_linode.sh
```

The script:

1. Creates or reuses the firewall and Linode.
2. Waits for SSH and cloud-init.
3. Adds the VM address to the workshop database allow list if `DATABASE_URL` is configured.
4. Copies the starter and `.env` over SSH, then builds and starts the containers.
5. Waits for `/health` and prints the application address.

In Cloud Manager, inspect **Linodes** and **Firewalls**. A running VM means the machine has booted; the application still needs to build and start.

## 3. Verify the application

Copy the printed IPv4 address:

```bash
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
LINODE_IP=${LINODE_IP%% *}
curl -fsS "http://$LINODE_IP:8000/health"
curl -fsS "http://$LINODE_IP:8000/chat" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"linode-demo","message":"Where can I park?"}'
```

Open `http://<your-linode-ipv4-address>:8000` in a browser. The answer should refer to the fictional parking document. Check the returned `tools_used` list and the document content.

`/health` shows the configured inference client, document source, data store, and cache. Without a bucket or database, the respective components use local fallbacks. A `200` from `/health` does not prove that every backend is reachable; a successful `/chat` request verifies the model path.

## 4. Inspect or update the runtime

```bash
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose ps"
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose logs --tail=50 agent"
```

The API listens on container port 8000, mapped to VM port 8000. Valkey is reachable on the Compose network and has no published host port. `restart: unless-stopped` restarts the containers after a VM reboot unless you stopped them deliberately.

To redeploy code or settings, edit them locally and run `bash scripts/deploy_linode.sh` again. It copies the files and rebuilds the container. Keep credentials out of cloud-init user data and source control.

If a database allow-list update finished after application startup, restart the app and inspect its status:

```bash
ssh root@$LINODE_IP "cd /opt/hackmidwest && docker compose restart agent"
curl -fsS "http://$LINODE_IP:8000/health"
```

## Verify and clean up

Show the VM in Cloud Manager and a working request to its application address. If PostgreSQL is configured, confirm a saved fact survives an application restart.

Use [cleanup](costs.md) to remove the workshop resources when finished. A powered-off VM can still accrue charges. If you retain the database after deleting the VM, remove the VM's old address from its allow list.

Next: [adapt the starter](../agent/README.md#make-it-yours), [inspect Valkey](05_valkey.md), or deploy the same app on [LKE](04_lke.md).
