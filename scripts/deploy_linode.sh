#!/usr/bin/env bash
# Deploy the starter on a Linode. See docs/03_body.md for the runtime lab.
# Creates a Cloud Firewall and a Linode in Seattle, waits for cloud-init to install Docker,
# lets the Linode into the database, copies the code and .env over SSH, starts docker compose,
# and waits until http://<ip>:8000/health answers. Safe to run again.
#   bash scripts/deploy_linode.sh
#   SSH_KEY=~/.ssh/other_key bash scripts/deploy_linode.sh
set -euo pipefail
source "$(dirname "$0")/lib.sh"
start=$(date +%s)
elapsed() { echo "$(( ($(date +%s) - start) / 60 )) min $(( ($(date +%s) - start) % 60 )) s"; }

if [[ ! -f $SSH_KEY.pub ]]; then
  echo "No SSH key at $SSH_KEY.pub. Make one with: ssh-keygen -t ed25519"
  exit 1
fi
ssh_opts=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes)

# 1. The Cloud Firewall: SSH and the agent's port come in, everything else is dropped.
fw_id=$(linode-cli firewalls list --label "$FIREWALL_LABEL" --text --no-headers --format id)
if [[ -z $fw_id ]]; then
  fw_id=$(linode-cli firewalls create --label "$FIREWALL_LABEL" \
    --rules.inbound_policy DROP --rules.outbound_policy ACCEPT \
    --rules.inbound '[{"label": "ssh-and-agent", "action": "ACCEPT", "protocol": "TCP", "ports": "22,8000", "addresses": {"ipv4": ["0.0.0.0/0"], "ipv6": ["::/0"]}}]' \
    --text --no-headers --format id)
  echo "Created firewall $FIREWALL_LABEL (id $fw_id)."
else
  echo "Firewall $FIREWALL_LABEL already exists (id $fw_id)."
fi

# 2. The Linode. cloud-init reads deploy/cloud-init.yaml on first boot and installs Docker.
linode_id=$(linode-cli linodes list --label "$LINODE_LABEL" --text --no-headers --format id)
if [[ -z $linode_id ]]; then
  linode_id=$(linode-cli linodes create --label "$LINODE_LABEL" --region "$REGION" --type "$LINODE_TYPE" \
    --image "$LINODE_IMAGE" --root_pass "$(openssl rand -base64 32)" --authorized_keys "$(cat "$SSH_KEY.pub")" \
    --firewall_id "$fw_id" --metadata.user_data "$(base64 < deploy/cloud-init.yaml | tr -d '\n')" \
    --text --no-headers --format id)
  echo "Created Linode $LINODE_LABEL (id $linode_id)."
else
  echo "Linode $LINODE_LABEL already exists (id $linode_id)."
fi
ip=$(linode-cli linodes view "$linode_id" --text --no-headers --format ipv4)
ip=${ip%% *}

running() { [[ $(linode-cli linodes view "$linode_id" --text --no-headers --format status) == running ]]; }
wait_for 600 "$LINODE_LABEL to boot" running
echo "$(elapsed): $LINODE_LABEL is running at $ip. Waiting for SSH."
wait_for 300 "SSH on $ip" ssh "${ssh_opts[@]}" "root@$ip" true
echo "$(elapsed): SSH works. Waiting for cloud-init to finish installing Docker."
ssh "${ssh_opts[@]}" "root@$ip" cloud-init status --wait

# 3. Let the Linode into the database, keeping the addresses already on the allow list.
id=$(db_id)
if [[ -n $id && -n $(get_env DATABASE_URL) ]]; then
  allowed=$(linode-cli databases postgresql-view "$id" --text --no-headers --format allow_list | tr ',' ' ')
  if [[ " $allowed " != *" $ip/32 "* ]]; then
    args=()
    for address in $allowed "$ip/32"; do args+=(--allow_list "$address"); done
    linode-cli databases postgresql-update "$id" "${args[@]}" >/dev/null
    echo "$(elapsed): added $ip/32 to the allow list of $DB_LABEL."
  fi
fi

# 4. Copy the code and .env, then build and start the agent and Valkey. The build log stays on the Linode.
scp "${ssh_opts[@]}" -q -r agent docs Dockerfile compose.yaml .dockerignore .env "root@$ip:/opt/hackmidwest/"
echo "$(elapsed): code and .env copied. Building and starting the containers."
ssh "${ssh_opts[@]}" "root@$ip" "cd /opt/hackmidwest && { docker compose up -d --build > deploy.log 2>&1 || { tail -n 30 deploy.log; exit 1; }; }"

# 5. Wait for the agent to answer. If memory is not live yet, the allow list change may still be
#    rolling out, so restart the agent until it connects.
healthy() { curl -sf --max-time 5 "http://$ip:8000/health"; }
wait_for 600 "http://$ip:8000/health" healthy
echo "$(elapsed): http://$ip:8000/health answers."
if [[ -n $(get_env DATABASE_URL) ]]; then
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    [[ $(healthy) == *'"memory":{"state":"live"'* ]] && break
    echo "Memory is not live yet (attempt $attempt of 10). Restarting the agent in 30 seconds."
    sleep 30
    ssh "${ssh_opts[@]}" "root@$ip" "cd /opt/hackmidwest && docker compose restart agent" >/dev/null 2>&1
    wait_for 120 "the agent to restart" healthy
  done
fi

echo
curl -s "http://$ip:8000/health" | python -m json.tool
echo
echo "The agent is up after $(elapsed): http://$ip:8000"
echo "SSH in with: ssh root@$ip"

