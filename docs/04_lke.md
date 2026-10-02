# Guide 04 (optional): The body on Kubernetes with LKE

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)   --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This module swaps the **body**: instead of one Linode running Docker Compose, the agent and Valkey run on a Linode Kubernetes Engine (LKE) cluster behind a NodeBalancer. The brain, knowledge, and memory stay the same.

## Overview

Kubernetes runs containers for you on a group of machines, restarts them when they fail, and puts a stable address in front of them. LKE is Akamai's managed Kubernetes: Akamai runs the control plane for free on the standard tier, and you pay for the worker nodes, which are ordinary Linodes.

Kubernetes normally pulls your code as a container image from a registry. This module skips the registry so it fits in 15 minutes: the pod starts from the public `python:3.12-slim` image, unpacks your code from a ConfigMap, and installs the agent's packages on start. Your `.env` becomes a Secret. A NodeBalancer, Akamai's load balancer, gives the agent a public address. The cluster creates it for you when you ask for a Service of type LoadBalancer. For the production pattern, with an image in a registry and two replicas, see module 8 of the [solution architect agent workshop](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent/tree/main/workshop/08_deploy_to_lke).

In this module the body looks like this:

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  kubectl / linode-cli ---creates-->  LKE cluster "hackmidwest-lke" (body)
                                        NodeBalancer "hackmidwest-nb", port 80
                                          node: a Linode that the cluster manages
                                            pod agent (port 8000)      --tools-->  Object Storage bucket (knowledge)
                                            pod valkey (reflexes)      --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

Tested on 2026-10-02: the cluster had a Ready node 2 and a half minutes after the create command, and the agent answered through its NodeBalancer 45 seconds after `kubectl apply`.

## Learning objectives

By the end of this module you will be able to:

- Create an LKE cluster and connect `kubectl` to it
- Turn `.env` into a Secret and your code into a ConfigMap
- Deploy the agent and Valkey with `kubectl apply`
- Explain how a Service of type LoadBalancer becomes a NodeBalancer, and give it a name you can find
- Check the agent through the NodeBalancer
- Tear the cluster down so it stops billing

## Prerequisites

- [Guide 01](01_knowledge.md) and [guide 02](02_memory.md) done, so `.env` has your bucket and database. The Linode from [guide 03](03_body.md) can stay or go.
- `kubectl` installed: see [Install the Kubernetes tools](https://kubernetes.io/docs/tasks/tools/). Check with `kubectl version --client`. Use a version within one minor version of the cluster's.
- About 15 minutes

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

```
┌──────┐
│ id   │
├──────┤
│ 1.36 │
├──────┤
│ 1.35 │
└──────┘
```

That was the list on 2026-10-02. Create a cluster with one worker node on the newest version:

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

```
Using default values: {}; use the --no-defaults flag to disable defaults
┌────────┬─────────────────┬────────┬─────────────┐
│ id     │ label           │ region │ k8s_version │
├────────┼─────────────────┼────────┼─────────────┤
│ 662761 │ hackmidwest-lke │ us-sea │ 1.36        │
└────────┴─────────────────┴────────┴─────────────┘
```

In Cloud Manager, open **Kubernetes**: `hackmidwest-lke` is listed in Seattle. Keep the id in a variable:

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

Right after you create the cluster, this fails:

```
Request failed: 503
	Cluster kubeconfig is not yet available. Please try again later.
```

`kubectl` then prints several lines about `localhost:8080`, because the file it reads is empty. Wait a minute and run the four lines again. On 2026-10-02 the kubeconfig was ready 2 minutes 17 seconds after the create command, and the node was already `Ready`:

```
NAME                     STATUS   ROLES    AGE   VERSION
lke662761-981465-w54sh   Ready    <none>   12s   v1.36.3
```

The node is a Linode that the cluster made and manages. It shows in Cloud Manager under **Linodes** with a name that starts with `lke` and your cluster's id.

## Step 3: Load your settings and code into the cluster

Everything goes in a namespace, `hackmidwest`, so `kubectl get` shows only this module's objects. Your `.env` becomes a Secret, and a tarball of your code becomes a ConfigMap:

```bash
kubectl create namespace hackmidwest --save-config
kubectl -n hackmidwest create secret generic agent-env --from-env-file=.env --save-config
COPYFILE_DISABLE=1 tar --no-xattrs -czf agent.tgz --exclude=__pycache__ agent docs/sample
kubectl -n hackmidwest create configmap agent-code --from-file=agent.tgz --save-config
rm agent.tgz
```

```
namespace/hackmidwest created
secret/agent-env created
configmap/agent-code created
```

`--from-env-file` reads `.env` line by line and skips the comment lines. Unlike the agent on your laptop, it keeps quotes and end-of-line comments as part of a value: `OPENAI_API_KEY="hk_..."` would reach the pod with its quotes, and the brain would refuse the key. Remove any quotes around values in `.env` before this step. `--save-config` records what you created, so the `kubectl apply` commands in step 8 and in `scripts/deploy_lke.sh` can change these objects later without a warning. `COPYFILE_DISABLE=1` stops macOS from adding hidden `._` files to the tarball. `--no-xattrs` leaves out file attributes, such as the quarantine flag macOS puts on downloaded files; the tar in the pod would print a warning for each one at the top of the agent's log. On Linux, both change nothing. The tarball of `agent/` and `docs/sample/` was 19 KB on 2026-10-02; a ConfigMap holds up to 1 MiB.

## Step 4: Let the node into the database

The agent's pod reaches the database from the worker node's public address. Read it from Kubernetes; `grep -v ':'` drops the node's IPv6 address:

```bash
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' | tr ' ' '\n' | grep -v ':' | head -n 1)
echo $NODE_IP
```

`kubectl get nodes -o wide` shows the same address in its EXTERNAL-IP column. Then add it to the allow list. The update replaces the whole list, so name every address that should keep access. If you kept the Linode from guide 03:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$LINODE_IP/32" --allow_list "$NODE_IP/32" --format id,label,status
```

If you deleted it:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$NODE_IP/32" --format id,label,status
```

```
┌────────┬────────────────┬──────────┐
│ id     │ label          │ status   │
├────────┼────────────────┼──────────┤
│ 533120 │ hackmidwest-db │ updating │
└────────┴────────────────┴──────────┘
```

The database says `updating` while the change rolls out. The agent connects to it once, when it starts, so wait until this says `active` before step 5. On 2026-10-02 that took under a minute:

```bash
linode-cli databases postgresql-view $DB_ID --format status
```

## Step 5: Deploy

Read the three manifests in `k8s/` first: `valkey.yaml` runs Valkey with an in-cluster Service, `agent.yaml` runs the agent, and `service.yaml` is the public front door. Then apply them:

```bash
kubectl apply -f k8s/valkey.yaml -f k8s/agent.yaml -f k8s/service.yaml
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s
kubectl -n hackmidwest get pods,services
```

```
deployment.apps/valkey created
service/valkey created
deployment.apps/agent created
service/agent created
Waiting for deployment "agent" rollout to finish: 0 of 1 updated replicas are available...
deployment "agent" successfully rolled out
NAME                         READY   STATUS    RESTARTS   AGE
pod/agent-5679f46fdc-vtqpq   1/1     Running   0          27s
pod/valkey-979dbf59c-ppgkr   1/1     Running   0          28s

NAME             TYPE           CLUSTER-IP       EXTERNAL-IP       PORT(S)        AGE
service/agent    LoadBalancer   10.128.117.69    198.51.100.20     80:32455/TCP   27s
service/valkey   ClusterIP      10.128.180.124   <none>            6379/TCP       28s
```

`rollout status` waits until the agent pod passes its readiness check, which took about 30 seconds on 2026-10-02 while the pod installed its packages. It gives up after 10 minutes. If it does, read the agent's log:

```bash
kubectl -n hackmidwest logs deployment/agent
```

The `agent` Service has type LoadBalancer. On LKE, that makes the cluster create a NodeBalancer and point it at your node. Its public address is the EXTERNAL-IP, which appeared 7 seconds after the Service on 2026-10-02. If it says `<pending>`, wait a few seconds and run `kubectl -n hackmidwest get services` again.

## Step 6: Name the NodeBalancer

The cluster names its NodeBalancer after itself, such as `lke662761-97045693dd69`. Give it the kit's name, so you can tell it apart in Cloud Manager and `scripts/down.sh` can find it. Look it up by its address, then rename it:

```bash
NB_IP=$(kubectl -n hackmidwest get service agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
NB_ID=$(linode-cli nodebalancers list --ipv4 $NB_IP --text --no-headers --format id)
linode-cli nodebalancers update $NB_ID --label hackmidwest-nb --format id,label,ipv4
```

```
┌─────────┬────────────────┬───────────────┐
│ id      │ label          │ ipv4          │
├─────────┼────────────────┼───────────────┤
│ 2504574 │ hackmidwest-nb │ 198.51.100.20 │
└─────────┴────────────────┴───────────────┘
```

The cluster keeps managing the NodeBalancer under its new name: it finds it by its address, not its name. In Cloud Manager, open **NodeBalancers**: `hackmidwest-nb` is there, with the tag `kubernetes`. A NodeBalancer costs $0.015 an hour.

## Step 7: Check it

```bash
curl http://$NB_IP/health
curl -X POST http://$NB_IP/chat -H "Content-Type: application/json" \
  -d '{"session_id": "lke-demo", "message": "When is our demo slot?"}'
```

```json
{"status":"ok","brain":{"state":"live","detail":"hackathon-chat at https://ws.akamai-workshops.com/v1"},"knowledge":{"state":"live","detail":"bucket hackmidwest-e02dabda at us-sea-1.linodeobjects.com"},"memory":{"state":"live","detail":"PostgreSQL 17.11 at a123456-akamai-prod-1234567-default.g2a.akamaidb.net:15268, pgvector 0.8.6"},"reflexes":{"state":"live","detail":"Valkey 8.1.10 at valkey:6379: embedding cache, 20 messages a minute per session"}}
{"reply":"Your demo slot is at 2:15 PM.","tools_used":["recall"]}
```

If `curl` says it could not connect, the NodeBalancer is still applying its settings. On 2026-10-02 it answered 45 seconds after the Service appeared; 35 seconds was too soon. Wait and run it again.

If `memory` says `error`, the agent started before the allow list change from step 4 reached the database. Restart the agent so it connects again, then run the checks again:

```bash
kubectl -n hackmidwest rollout restart deployment/agent
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s
```

All four roles are live, with `reflexes` at the Valkey Service, `valkey:6379`. The chat answer comes from the same database as before, so the demo slot you saved in guide 02 is still there. Open `http://<NB_IP>` in a browser for the chat page; the NodeBalancer listens on port 80.

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
COPYFILE_DISABLE=1 tar --no-xattrs -czf agent.tgz --exclude=__pycache__ agent docs/sample
kubectl -n hackmidwest create configmap agent-code --from-file=agent.tgz --dry-run=client -o yaml | kubectl apply -f -
rm agent.tgz
kubectl -n hackmidwest rollout restart deployment/agent
```

To change a setting, edit `.env`, then replace the Secret and restart the agent:

```bash
kubectl -n hackmidwest create secret generic agent-env --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
kubectl -n hackmidwest rollout restart deployment/agent
```

Installing packages on every start costs half a minute and needs PyPI to be up. That is fine for a hackathon and wrong for production, where you build an image once and push it to a registry, as module 8 of the solution architect agent workshop does.

## Validation

- `kubectl get nodes` shows one `Ready` node.
- `kubectl -n hackmidwest get pods` shows `agent` and `valkey` running.
- `curl http://$NB_IP/health` shows four roles, all `live`.
- `linode-cli nodebalancers list --label hackmidwest-nb --format id,label,ipv4` shows the NodeBalancer with the same address as the Service's EXTERNAL-IP.

**Show the judges:** Cloud Manager, **Kubernetes**, then `hackmidwest-lke` and its node pool, and **NodeBalancers**, then `hackmidwest-nb`. From the terminal, `kubectl -n hackmidwest get pods,services` shows the agent behind the NodeBalancer's address, and `http://<NB_IP>/health` shows what it is connected to.

## Clean up

The cluster's node and the NodeBalancer bill by the hour until you delete them. Delete the Service first: the cluster then deletes the NodeBalancer it made, which took a second on 2026-10-02. Then delete the cluster and the kubeconfig. The last line checks that no NodeBalancer named `hackmidwest-nb` is left:

```bash
export KUBECONFIG=$PWD/hackmidwest-kubeconfig.yaml
kubectl -n hackmidwest delete service agent
CLUSTER_ID=$(linode-cli lke clusters-list --label hackmidwest-lke --text --no-headers --format id)
linode-cli lke cluster-delete $CLUSTER_ID
rm hackmidwest-kubeconfig.yaml
linode-cli nodebalancers list --label hackmidwest-nb --format id,label
```

```
service "agent" deleted from hackmidwest namespace
┌────┬───────┐
│ id │ label │
├────┼───────┤
└────┴───────┘
```

Deleting the cluster deletes its node Linode; on 2026-10-02 it was gone 30 seconds later. If the last table lists `hackmidwest-nb`, the Service was not deleted first, and the NodeBalancer keeps billing. Delete it by name:

```bash
NB_ID=$(linode-cli nodebalancers list --label hackmidwest-nb --text --no-headers --format id)
linode-cli nodebalancers delete $NB_ID
```

Then take the node's address off the database's allow list. Akamai gives freed addresses to other customers. Set the three variables again, as in the prerequisites:

```bash
MY_IP=$(curl -s https://api.ipify.org)
DB_ID=$(linode-cli databases postgresql-list --label hackmidwest-db --text --no-headers --format id)
LINODE_IP=$(linode-cli linodes list --label hackmidwest-agent --text --no-headers --format ipv4)
```

If you kept the Linode from guide 03:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --allow_list "$LINODE_IP/32" --format id,label,status
```

If you deleted it:

```bash
linode-cli databases postgresql-update $DB_ID --allow_list "$MY_IP/32" --format id,label,status
```

Left running, this module costs $0.033 an hour: $0.018 for the node and $0.015 for the NodeBalancer. Cloud Manager's **Kubernetes** and **NodeBalancers** pages should no longer list them.

`scripts/down.sh` also finds `hackmidwest-lke` and `hackmidwest-nb` and deletes them, and while the cluster runs it finds the NodeBalancer even when you skipped step 6. It deletes everything else the kit made as well, including the database and the bucket, so run it only when you are done with the whole kit.

## Next steps

`scripts/deploy_lke.sh` runs steps 1 to 7 for you when you rebuild, and on a second run it ships your latest code. These are the same commands you just typed, in one file.

For a production setup, work through module 8 of the [solution architect agent workshop](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent/tree/main/workshop/08_deploy_to_lke): an image in GitHub's container registry, two replicas, and sessions kept in Object Storage so any pod can answer any conversation.
