#!/usr/bin/env bash
# The optional body on Kubernetes: the same commands as guide 04, in one file, for when you rebuild.
# Creates a one-node LKE cluster in Seattle, loads your code and .env into the cluster, lets the node
# into the database, starts the agent and Valkey, names the NodeBalancer the cluster makes for them,
# and waits until http://<nodebalancer>/health answers. Safe to run again: it reuses what exists and rolls out changes.
#   bash scripts/deploy_lke.sh
set -euo pipefail
source "$(dirname "$0")/lib.sh"
start=$(date +%s)
elapsed() { echo "$(( ($(date +%s) - start) / 60 )) min $(( ($(date +%s) - start) % 60 )) s"; }

if ! command -v kubectl >/dev/null; then
  echo "kubectl not found. Install it: https://kubernetes.io/docs/tasks/tools/"
  exit 1
fi

# 1. The cluster: one g6-standard-1 node on the newest Kubernetes version LKE offers.
cluster_id=$(linode-cli lke clusters-list --label "$LKE_LABEL" --text --no-headers --format id)
if [[ -z $cluster_id ]]; then
  version=$(linode-cli lke versions-list --text --no-headers --format id | head -n 1)
  cluster_id=$(linode-cli lke cluster-create --label "$LKE_LABEL" --region "$REGION" --k8s_version "$version" \
    --node_pools.type "$LINODE_TYPE" --node_pools.count 1 --text --no-headers --format id)
  echo "Created LKE cluster $LKE_LABEL (id $cluster_id) on Kubernetes $version."
else
  echo "LKE cluster $LKE_LABEL already exists (id $cluster_id)."
fi

# 2. The kubeconfig lets kubectl talk to the cluster. It is a credential, so .gitignore keeps it out of git.
kubeconfig() { linode-cli lke kubeconfig-view "$cluster_id" --text --no-headers; }
wait_for 600 "the cluster's kubeconfig" kubeconfig
kubeconfig | python -c 'import base64, sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))' > "$KUBECONFIG_FILE"
chmod 600 "$KUBECONFIG_FILE"
export KUBECONFIG="$REPO/$KUBECONFIG_FILE"
node_ready() { kubectl get nodes --no-headers 2>/dev/null | grep -q " Ready "; }
wait_for 900 "a Ready node" node_ready
echo "$(elapsed): the node is Ready."

# 3. The namespace, the Secret from .env, and the code as a ConfigMap. "create --dry-run | apply" updates them on a rerun.
kubectl create namespace hackmidwest --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl -n hackmidwest create secret generic agent-env --from-env-file=.env --dry-run=client -o yaml \
  | kubectl apply -f - >/dev/null
COPYFILE_DISABLE=1 tar -czf agent.tgz --exclude=__pycache__ agent docs/sample
kubectl -n hackmidwest create configmap agent-code --from-file=agent.tgz --dry-run=client -o yaml \
  | kubectl apply -f - >/dev/null
rm -f agent.tgz

# 4. Let the node into the database, keeping the addresses already on the allow list.
node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' \
  | tr ' ' '\n' | grep -E '^[0-9.]+$' | head -n 1)
id=$(db_id)
if [[ -n $id && -n $(get_env DATABASE_URL) ]]; then
  allowed=$(linode-cli databases postgresql-view "$id" --text --no-headers --format allow_list | tr ',' ' ')
  if [[ " $allowed " != *" $node_ip/32 "* ]]; then
    args=()
    for address in $allowed "$node_ip/32"; do args+=(--allow_list "$address"); done
    linode-cli databases postgresql-update "$id" "${args[@]}" >/dev/null
    echo "$(elapsed): added the node, $node_ip/32, to the allow list of $DB_LABEL."
  fi
fi

# 5. Start Valkey, the agent, and the Service. On a rerun, restart the agent so it picks up new code or settings.
existed=$(kubectl -n hackmidwest get deployment agent -o name 2>/dev/null || true)
kubectl apply -f k8s/valkey.yaml -f k8s/agent.yaml -f k8s/service.yaml
if [[ -n $existed ]]; then kubectl -n hackmidwest rollout restart deployment/agent; fi
kubectl -n hackmidwest rollout status deployment/agent --timeout=600s

# 6. The Service makes the cluster create a NodeBalancer named lke<cluster id>-<12 characters>.
#    Find it by its address and name it hackmidwest-nb, so you and scripts/down.sh can find it later.
lb_ip() { kubectl -n hackmidwest get service agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}'; }
has_lb_ip() { [[ -n $(lb_ip) ]]; }
wait_for 600 "the cluster to create a NodeBalancer" has_lb_ip
nb_ip=$(lb_ip)
nb_id=$(linode-cli nodebalancers list --ipv4 "$nb_ip" --text --no-headers --format id)
named=$(linode-cli nodebalancers list --label "$NB_LABEL" --text --no-headers --format id)
if [[ -n $named && $named != "$nb_id" ]]; then
  echo "Another NodeBalancer is already named $NB_LABEL (id $named). Delete it: linode-cli nodebalancers delete $named"
  exit 1
elif [[ -z $named ]]; then
  linode-cli nodebalancers update "$nb_id" --label "$NB_LABEL" >/dev/null
  echo "$(elapsed): named the cluster's NodeBalancer $NB_LABEL (id $nb_id)."
fi

# 7. Wait for the agent to answer through the NodeBalancer. If memory is not live yet, the allow list
#    change may still be rolling out, so restart the agent until it connects.
healthy() { curl -sf --max-time 5 "http://$nb_ip/health"; }
wait_for 600 "http://$nb_ip/health" healthy
if [[ -n $(get_env DATABASE_URL) ]]; then
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    [[ $(healthy) == *'"memory":{"state":"live"'* ]] && break
    echo "Memory is not live yet (attempt $attempt of 10). Restarting the agent in 30 seconds."
    sleep 30
    kubectl -n hackmidwest rollout restart deployment/agent >/dev/null
    kubectl -n hackmidwest rollout status deployment/agent --timeout=600s >/dev/null
    wait_for 120 "the agent to restart" healthy
  done
fi

echo
healthy | python -m json.tool
echo
echo "The agent is up on LKE after $(elapsed): http://$nb_ip"
echo "Use kubectl with: export KUBECONFIG=$REPO/$KUBECONFIG_FILE"
