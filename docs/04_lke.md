# Guide 04 (optional): The body on Kubernetes with LKE

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)  --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This module swaps the **body**: instead of one Linode running Docker Compose, the agent and Valkey run on a Linode Kubernetes Engine (LKE) cluster behind a NodeBalancer. The brain, knowledge, and memory stay the same.

> [!WARNING]
> Steps marked `[Unverified: not yet run on a live LKE cluster]` have not been tested end to end yet. The manifests pass Kubernetes schema validation, and the pod's startup command was tested in Docker on 2026-10-02. If a step fails, tell the organizers what you saw.

## Overview

Kubernetes runs containers for you on a group of machines, restarts them when they fail, and puts a stable address in front of them. LKE is Akamai's managed Kubernetes: Akamai runs the control plane for free on the standard tier, and you pay for the worker nodes, which are ordinary Linodes.

Kubernetes normally pulls your code as a container image from a registry. This module skips the registry so it fits in 15 minutes: the pod starts from the public `python:3.12-slim` image, unpacks your code from a ConfigMap, and installs the agent's packages on start. Your `.env` becomes a Secret. A NodeBalancer, Akamai's load balancer, gives the agent a public address. For the production pattern, with an image in a registry and two replicas, see module 8 of the [solution architect agent workshop](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent/tree/main/workshop/08_deploy_to_lke).

## Learning objectives

By the end of this module you will be able to:

- Create an LKE cluster and connect `kubectl` to it
- Create a NodeBalancer and hand it to a Kubernetes Service
- Turn `.env` into a Secret and your code into a ConfigMap
- Deploy the agent and Valkey with `kubectl apply`
- Check the agent through the NodeBalancer
- Tear the cluster down so it stops billing

## Prerequisites

- [Guide 01](01_knowledge.md) and [guide 02](02_memory.md) done, so `.env` has your bucket and database. The Linode from [guide 03](03_body.md) can stay or go.
- `kubectl` installed: see [Install the Kubernetes tools](https://kubernetes.io/docs/tasks/tools/). Check with `kubectl version --client`. Use a version within one minor version of the cluster's.
- About 15 minutes, plus 5 to 10 minutes for the cluster to start

Set three shell variables first, in the terminal you will use: your laptop's address, your database's id, and the address of the Linode from guide 03. `LINODE_IP` comes back empty if you deleted that Linode.

```bash
MY_IP=$(curl -s https://api.ipify.org)
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
echo $MY_IP $DB_ID $LINODE_IP
```

## Step 1: Create the cluster

See which Kubernetes versions LKE offers. The newest is first:

```bash
linode-cli lke versions-list
```

On 2026-10-02 the list was 1.36 and 1.35. Create a cluster with one worker node:

```bash
linode-cli lke cluster-create \
  --label hackmidwest-lke \
  --region us-sea \
  --k8s_version 1.36 \
  --node_pools.type g6-standard-1 \
  --node_pools.count 1 \
  --format id,label,region,k8s_version
```

`--node_pools.type` is the plan of each worker node, the same `g6-standard-1` as the Linode in guide 03. `--node_pools.count 1` keeps the cost to one node, $0.018 an hour. The control plane on the standard tier is free.

`[Unverified: not yet run on a live LKE cluster]` The output is a table with the cluster's id, label, region, and version. In Cloud Manager, open **Kubernetes**: `hackmidwest-lke` is listed in Seattle. Keep the id in a variable:

```bash
CLUSTER_ID=$(linode-cli lke clusters-list --label hackmidwest-lke --text --no-headers --format id)
```

## Step 2: Connect kubectl

`kubectl` needs a kubeconfig file: the cluster's address and a credential. LKE hands it out base64-encoded. Decode it into a file, and keep that file out of git; `.gitignore` already lists `hackmidwest-kubeconfig.yaml`.

```bash
linode-cli lke kubeconfig-view $CLUSTER_ID --text --no-headers | base64 --decode > hackmidwest-kubeconfig.yaml
chmod 600 hackmidwest-kubeconfig.yaml
export KUBECONFIG=$PWD/hackmidwest-kubeconfig.yaml
kubectl get nodes
```

`[Unverified: not yet run on a live LKE cluster]` If `kubeconfig-view` returns an error, the cluster is still starting; wait a minute and try again. `kubectl get nodes` lists one node, and its STATUS turns `Ready` after a few minutes. On older macOS, use `base64 -D` instead of `base64 --decode`.

## Step 3: Create the NodeBalancer

A Kubernetes Service of type LoadBalancer gets its public address from a NodeBalancer. If you let the cluster create one, it gets a generated name. Create it yourself instead, so it carries your `hackmidwest-` label and `scripts/down.sh` can find it:

```bash
linode-cli nodebalancers create --label hackmidwest-nb --region us-sea --format id,label,ipv4
```

`[Unverified: not yet run on a live LKE cluster]` The output shows the NodeBalancer's id and its public IPv4 address. Keep both in variables:

```bash
NB_ID=$(linode-cli nodebalancers list --label hackmidwest-nb --text --no-headers --format id)
NB_IP=$(linode-cli nodebalancers list --label hackmidwest-nb --text --no-headers --format ipv4)
echo $NB_ID $NB_IP
```

A NodeBalancer costs $0.015 an hour. In Cloud Manager it appears under **NodeBalancers**.

## Step 4: Load your settings and code into the cluster

Everything goes in a namespace, `hackmidwest`, so `kubectl get` shows only this module's objects. Your `.env` becomes a Secret, and a tarball of your code becomes a ConfigMap:

```bash
kubectl create namespace hackmidwest
kubectl -n hackmidwest create secret generic agent-env --from-env-file=.env
COPYFILE_DISABLE=1 tar -czf agent.tgz --exclude=__pycache__ agent docs/sample
kubectl -n hackmidwest create configmap agent-code --from-file=agent.tgz
rm agent.tgz
```

`--from-env-file` reads `.env` line by line and skips the comments. `COPYFILE_DISABLE=1` stops macOS from adding hidden `._` files to the tarball; on Linux it does nothing. The tarball of `agent/` and `docs/sample/` was 18.5 KB on 2026-10-02; a ConfigMap holds up to 1 MiB.

## Step 5: Let the node into the database

The agent's pod reaches the database from the worker node's public address. Read it from Kubernetes; `grep -v ':'` drops an IPv6 address if the node has one:

```bash
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' | tr ' ' '\n' | grep -v ':' | head -n 1)
echo $NODE_IP
```

`kubectl get nodes -o wide` shows the same address in its EXTERNAL-IP column. Then add it to the allow list. The update replaces the whole list, so name every address that should keep access. If you kept the Linode from guide 03:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$LINODE_IP/32" --allow_list "$NODE_IP/32"
```

If you deleted it:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$NODE_IP/32"
```

## Step 6: Deploy

Read the three manifests in `k8s/` first: `valkey.yaml` runs Valkey with an in-cluster Service, `agent.yaml` runs the agent, and `service.yaml` is the public front door. Then apply them. `sed` puts your NodeBalancer's id into the Service:

```bash
kubectl apply -f k8s/valkey.yaml -f k8s/agent.yaml
sed "s/NODEBALANCER_ID/$NB_ID/" k8s/service.yaml | kubectl apply -f -
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s
kubectl -n hackmidwest get pods,services
```

`[Unverified: not yet run on a live LKE cluster]` `rollout status` waits until the agent pod passes its readiness check, which takes about a minute while it installs packages, and gives up after 10 minutes. `get services` shows the `agent` Service with your NodeBalancer's address under EXTERNAL-IP. If the rollout gives up, read the agent's log:

```bash
kubectl -n hackmidwest logs deployment/agent
```

## Step 7: Check it

```bash
curl http://$NB_IP/health
curl -X POST http://$NB_IP/chat -H "Content-Type: application/json" \
  -d '{"session_id": "lke-demo", "message": "When is our demo slot?"}'
```

`[Unverified: not yet run on a live LKE cluster]` `/health` lists the four roles, with `reflexes` at `valkey:6379`. The chat answer comes from the same database as before, so the demo slot you saved in guide 02 is still there. Open `http://<NB_IP>` in a browser for the chat page; the NodeBalancer listens on port 80.

## Step 8: Read the manifest you just used

The interesting part of `k8s/agent.yaml` is how the pod starts:

```yaml
        - name: agent
          image: python:3.12-slim
          command: ["sh", "-c"]
          args:
            - mkdir -p /app && tar -xzf /code/agent.tgz -C /app && cd /app &&
              pip install --no-cache-dir --quiet --root-user-action=ignore -r agent/requirements.txt &&
              exec uvicorn agent.server:app --host 0.0.0.0 --port 8000
          envFrom:
            - secretRef:
                name: agent-env
          env:
            - name: VALKEY_URL  # the valkey Service in valkey.yaml; this wins over the Secret
              value: redis://valkey:6379/0
```

The ConfigMap is mounted at `/code`. The pod unpacks your code, installs its packages, and runs the same `uvicorn` command as the Dockerfile. `envFrom` turns every key in the Secret into an environment variable, and `env` adds `VALKEY_URL`, pointing at the Valkey Service by name.

To ship a code change, rebuild the ConfigMap and restart the agent:

```bash
COPYFILE_DISABLE=1 tar -czf agent.tgz --exclude=__pycache__ agent docs/sample
kubectl -n hackmidwest create configmap agent-code --from-file=agent.tgz --dry-run=client -o yaml | kubectl apply -f -
rm agent.tgz
kubectl -n hackmidwest rollout restart deployment/agent
```

Installing packages on every start costs a minute and needs PyPI to be up. That is fine for a hackathon and wrong for production, where you build an image once and push it to a registry, as module 8 of the solution architect agent workshop does.

## Validation

- `kubectl get nodes` shows one `Ready` node.
- `kubectl -n hackmidwest get pods` shows `agent` and `valkey` running.
- `curl http://$NB_IP/health` shows four roles.

**Show the judges:** Cloud Manager, **Kubernetes**, then `hackmidwest-lke` and its node pool, and **NodeBalancers**, then `hackmidwest-nb`. From the terminal, `kubectl -n hackmidwest get pods,services` shows the agent behind the NodeBalancer's address, and `http://<NB_IP>/health` shows what it is connected to.

## Clean up

The cluster's node and the NodeBalancer bill by the hour until you delete them. Look up the ids, then delete the cluster first, so nothing recreates the NodeBalancer, then the NodeBalancer, then the kubeconfig:

```bash
CLUSTER_ID=$(linode-cli lke clusters-list --label hackmidwest-lke --text --no-headers --format id)
NB_ID=$(linode-cli nodebalancers list --label hackmidwest-nb --text --no-headers --format id)
linode-cli lke cluster-delete $CLUSTER_ID
linode-cli nodebalancers delete $NB_ID
rm hackmidwest-kubeconfig.yaml
```

Deleting the cluster deletes its node Linode. Then take the node's address off the database's allow list by setting the list again without it, as in step 5. Akamai gives freed addresses to other customers. Left running, this module costs $0.033 an hour: $0.018 for the node and $0.015 for the NodeBalancer. Cloud Manager's **Kubernetes** and **NodeBalancers** pages should no longer list them.

`scripts/down.sh` also finds `hackmidwest-lke` and `hackmidwest-nb` and deletes them.

## Next steps

`scripts/deploy_lke.sh` runs steps 1 to 7 for you when you rebuild, and on a second run it ships your latest code. These are the same commands you just typed, in one file.

For a production setup, work through module 8 of the [solution architect agent workshop](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent/tree/main/workshop/08_deploy_to_lke): an image in GitHub's container registry, two replicas, and sessions kept in Object Storage so any pod can answer any conversation.
