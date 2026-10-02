# Lab: Run the application on LKE

[Workshop home](../README.md) · [Runtime comparison](cloud.md#choose-a-runtime) · [Project paths](build.md)

**Result:** the starter runs as a Kubernetes Deployment and answers through a NodeBalancer.

**Prerequisites:** [setup](00_prework.md), activated account, CLI permissions for LKE, Linodes, NodeBalancers, and database checks; `kubectl`; and a working inference key. A previous Linode deployment is not required. Allow about 20–30 minutes plus provisioning delays. Worker nodes and the NodeBalancer are billable.

LKE manages the Kubernetes control plane. You define workloads and choose worker-node capacity. This lab uses one node and one replica for demonstration, so a node failure interrupts the app.

## 1. Read the deployment files

| File | Purpose |
|---|---|
| [k8s/agent.yaml](../k8s/agent.yaml) | Application Deployment, configuration, and health probes |
| [k8s/valkey.yaml](../k8s/valkey.yaml) | Valkey Deployment and internal Service |
| [k8s/service.yaml](../k8s/service.yaml) | Public LoadBalancer Service |
| [scripts/deploy_lke.sh](../scripts/deploy_lke.sh) | Cluster creation, configuration, rollout, and validation |

For this exercise, the pod unpacks a code archive from a ConfigMap and installs dependencies at startup. This avoids a container-registry setup step but depends on package downloads whenever the pod starts. For a maintained application, build the supplied Dockerfile into an image, push it to a registry, and update the Deployment to use that image.

The public Service uses HTTP and the starter has no authentication. Use fictional data. Kubernetes Secrets hold the environment settings; they still require appropriate cluster access controls.

## 2. Deploy

Use unquoted `KEY=value` lines without inline comments in `.env`. `kubectl --from-env-file` preserves quotes as part of a value, unlike python-dotenv.

```bash
linode-cli lke versions-list
bash scripts/deploy_lke.sh
```

The script creates or reuses `hackmidwest-lke`, selects a version from the CLI response when creating it, and uses the compute plan in `scripts/lib.sh`. Check the selected version and plan in its output. Do not assume a hard-coded Kubernetes version will remain available.

It downloads a kubeconfig, creates the `hackmidwest` namespace, copies settings into `agent-env`, and loads the source archive into `agent-code`. If configured, it adds the worker address to the database allow list. It then deploys the workloads and waits for the Service address.

The `LoadBalancer` Service causes LKE to provision a NodeBalancer. The script labels it `hackmidwest-nb` and prints its address. Do not run this script concurrently against the same account from multiple laptops.

## 3. Inspect the objects

From the workshop directory:

```bash
export KUBECONFIG="$PWD/hackmidwest-kubeconfig.yaml"
kubectl get nodes
kubectl -n hackmidwest get deployments,pods,services
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s
```

Expect a Ready node, running application and Valkey pods, and an external address on the `agent` Service. An external address of `<pending>` means the load balancer is still being provisioned.

The kubeconfig is a credential. Keep it out of source control and shared logs.

## 4. Verify a request

```bash
NB_IP=$(kubectl -n hackmidwest get service agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -fsS "http://$NB_IP/health"
curl -fsS "http://$NB_IP/chat" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"lke-demo","message":"Where can I park?"}'
```

Open `http://<nodebalancer-address>` for the chat page. Show both the successful application request and the cluster in Cloud Manager. If you configured a bucket and PostgreSQL, verify their status and a real read or persistence operation too.

## 5. Diagnose and redeploy

```bash
kubectl -n hackmidwest logs deployment/agent --tail=50
kubectl -n hackmidwest describe pod -l app=agent
kubectl -n hackmidwest get events --sort-by=.metadata.creationTimestamp
```

A failed startup may indicate package download problems, a malformed environment value, or insufficient node capacity. An external address can appear before the NodeBalancer is ready to forward requests. Use [troubleshooting](troubleshooting.md#deployment) to narrow down the failure.

After local changes, rerun `bash scripts/deploy_lke.sh` to replace the Secret and ConfigMap and restart the Deployment. After a database allow-list correction, restart only the application:

```bash
kubectl -n hackmidwest rollout restart deployment/agent
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s
```

If you later add or replace worker nodes, review their database access. Review [database networking guidance](https://techdocs.akamai.com/cloud-computing/docs/aiven-manage-database) for current LKE allow-list behavior. Keep durable application state outside a pod's temporary filesystem.

## Clean up

Use [cleanup](costs.md). Inspect Kubernetes, Linodes, NodeBalancers, and any volumes afterward. A separate VM created by the Linode lab continues running until deleted. Remove retired compute addresses from a database you retain.

Next: [adapt the starter](../agent/README.md#make-it-yours) or inspect [Valkey](05_valkey.md).
