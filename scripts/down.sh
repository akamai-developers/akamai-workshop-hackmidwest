#!/usr/bin/env bash
# The safety net: deletes what this kit created, so nothing keeps billing after the event.
# It looks up each kit resource by its exact hackmidwest- name, shows what it found, and asks
# you to type yes. Then it deletes them and empties the OBJ_* and DATABASE_URL lines in .env.
# It never lists or touches anything else on your account.
#   bash scripts/down.sh          asks before deleting
#   bash scripts/down.sh --yes    deletes without asking
set -uo pipefail  # no -e: one failed delete should not stop the others
source "$(dirname "$0")/lib.sh"

# The id of the one resource with exactly this label, or nothing.
lookup() { linode-cli "$1" "$2" --label "$3" --text --no-headers --format id 2>/dev/null; }

lke_id=$(lookup lke clusters-list "$LKE_LABEL")
nb_id=$(lookup nodebalancers list "$NB_LABEL")
linode_id=$(lookup linodes list "$LINODE_LABEL")
fw_id=$(lookup firewalls list "$FIREWALL_LABEL")
database_id=$(db_id)

# The bucket named in .env (if you made it by hand), otherwise the name scripts/up.sh derives from your account.
bucket=$(get_env OBJ_BUCKET)
[[ $bucket == hackmidwest-* ]] || bucket=$(bucket_name)
if out=$(linode-cli obj ls "$bucket" --cluster "$CLUSTER" 2>&1); then
  bucket_state=found
elif [[ $out == *NoSuchBucket* || $out == *"does not exist"* || $out == *"not found"* ]]; then
  bucket_state=none
else
  bucket_state=unknown
  echo "Could not check bucket $bucket: $out"
fi

key_id=$(get_env OBJ_KEY_ID)
if [[ -n $key_id ]]; then
  key_label=$(linode-cli object-storage keys-view "$key_id" --text --no-headers --format label 2>/dev/null)
  [[ $key_label == hackmidwest-* ]] || key_id=""  # gone already, or not one of ours
fi

echo "Resources from this kit in your account:"
found=0
show() { printf "  %-16s %-26s %s\n" "$1" "$2" "$3"; found=$((found + 1)); }
[[ -n $lke_id ]] && show "LKE cluster" "$LKE_LABEL (id $lke_id)" "\$0.018 an hour per node"
[[ -n $nb_id ]] && show "NodeBalancer" "$NB_LABEL (id $nb_id)" "\$0.015 an hour"
[[ -n $linode_id ]] && show "Linode" "$LINODE_LABEL (id $linode_id)" "\$0.018 an hour"
[[ -n $fw_id ]] && show "Cloud Firewall" "$FIREWALL_LABEL (id $fw_id)" "free"
[[ -n $database_id ]] && show "PostgreSQL" "$DB_LABEL (id $database_id)" "\$0.024 an hour"
[[ $bucket_state == found ]] && show "Bucket" "$bucket" "part of the \$5 a month Object Storage fee"
[[ -n $key_id ]] && show "Access key" "$KEY_LABEL (id $key_id)" "free"

if (( found == 0 )); then
  echo "  none"
else
  if [[ ${1:-} != --yes ]]; then
    read -r -p "Delete these $found resources? Type yes to continue: " answer
    [[ $answer == yes ]] || { echo "Nothing deleted."; exit 1; }
  fi
  failed=0
  run() { echo "  $1"; shift; "$@" >/dev/null || { echo "    FAILED: $*"; failed=$((failed + 1)); }; }
  [[ -n $lke_id ]] && run "Deleting LKE cluster $LKE_LABEL" linode-cli lke cluster-delete "$lke_id"
  [[ -n $nb_id ]] && run "Deleting NodeBalancer $NB_LABEL" linode-cli nodebalancers delete "$nb_id"
  [[ -n $linode_id ]] && run "Deleting Linode $LINODE_LABEL" linode-cli linodes delete "$linode_id"
  [[ -n $fw_id ]] && run "Deleting firewall $FIREWALL_LABEL" linode-cli firewalls delete "$fw_id"
  [[ -n $database_id ]] && run "Deleting database $DB_LABEL" linode-cli databases postgresql-delete "$database_id"
  [[ $bucket_state == found ]] && run "Deleting bucket $bucket and its files" \
    linode-cli obj rb "$bucket" --recursive --cluster "$CLUSTER"
  [[ -n $key_id ]] && run "Revoking access key $KEY_LABEL" linode-cli object-storage keys-delete "$key_id"
  if (( failed > 0 )); then
    echo "$failed delete(s) failed. Fix the cause and run this script again. .env is unchanged."
    exit 1
  fi
fi

if [[ $bucket_state != unknown ]]; then
  for key in OBJ_ENDPOINT OBJ_BUCKET OBJ_ACCESS_KEY OBJ_SECRET_KEY OBJ_KEY_ID DATABASE_URL; do set_env "$key" ""; done
  echo "Emptied OBJ_* and DATABASE_URL in .env. The agent is back on its local fallbacks."
fi
if [[ -f $KUBECONFIG_FILE && -z $(lookup lke clusters-list "$LKE_LABEL") ]]; then
  rm -f "$KUBECONFIG_FILE"
  echo "Removed $KUBECONFIG_FILE, the credential for the deleted cluster."
fi
echo
echo "Object Storage itself still bills \$5 a month until you cancel it. Cancelling deletes every bucket"
echo "on the account, so do it yourself when you are sure: Cloud Manager, Object Storage, Cancel Object Storage."
if [[ $bucket_state == unknown ]]; then
  echo "The bucket $bucket was not checked. See the error above, then run this script again."
  exit 1
fi
