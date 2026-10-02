#!/usr/bin/env bash
# Create or reuse the workshop bucket, access key, and optional PostgreSQL database.
# See docs/01_knowledge.md and docs/02_memory.md for the individual service labs.
#   bash scripts/up.sh           the database, the bucket, and the bucket's access key
#   bash scripts/up.sh --no-db   the bucket and its access key only (the 30-minute path)
set -euo pipefail
source "$(dirname "$0")/lib.sh"

with_db=yes
if [[ ${1:-} == --no-db ]]; then with_db=no; fi

# 1. Managed PostgreSQL first, because it takes the longest to become active.
if [[ $with_db == yes ]]; then
  id=$(db_id)
  if [[ -n $id ]]; then
    echo "Database $DB_LABEL already exists (id $id)."
  else
    ip=$(my_ip)
    [[ -n $ip ]] || { echo "Could not find your public IP address for the allow list."; exit 1; }
    echo "Creating database $DB_LABEL in $REGION. Only $ip may connect."
    linode-cli databases postgresql-create --label "$DB_LABEL" --region "$REGION" --type "$DB_TYPE" \
      --engine "$DB_ENGINE" --cluster_size 1 --allow_list "$ip/32" \
      --text --format id,label,region,type,engine,version,status
  fi
fi

# 2. The bucket for the agent's documents: the one in .env if you made it by hand, otherwise a name from your account.
bucket=$(get_env OBJ_BUCKET)
[[ $bucket == hackmidwest-* ]] || bucket=$(bucket_name)
if linode-cli obj ls "$bucket" --cluster "$CLUSTER" >/dev/null 2>&1; then
  echo "Bucket $bucket already exists."
else
  linode-cli obj mb "$bucket" --cluster "$CLUSTER"
fi

# 3. An access key that can reach only that bucket. The secret is shown once, so it goes straight into .env.
key_id=$(get_env OBJ_KEY_ID)
if [[ -n $key_id && $(get_env OBJ_BUCKET) == "$bucket" ]] && linode-cli object-storage keys-view "$key_id" >/dev/null 2>&1; then
  echo "Access key $KEY_LABEL (id $key_id) is already in .env."
else
  key=$(linode-cli object-storage keys-create --label "$KEY_LABEL" \
    --bucket_access "[{\"region\": \"$REGION\", \"bucket_name\": \"$bucket\", \"permissions\": \"read_write\"}]" \
    --text --no-headers --format id,access_key,secret_key)
  read -r key_id access_key secret_key <<<"$key"
  set_env OBJ_ENDPOINT "$OBJ_ENDPOINT"
  set_env OBJ_BUCKET "$bucket"
  set_env OBJ_ACCESS_KEY "$access_key"
  set_env OBJ_SECRET_KEY "$secret_key"
  set_env OBJ_KEY_ID "$key_id"
  echo "Created access key $KEY_LABEL (id $key_id) for $bucket and wrote OBJ_* to .env."
fi

echo
echo "Knowledge: bucket $bucket at $OBJ_ENDPOINT"
if [[ $with_db == yes ]]; then
  id=$(db_id)
  echo "Memory: database $DB_LABEL is $(linode-cli databases postgresql-view "$id" --text --no-headers --format status)."
  echo "It takes 10 to 15 minutes to become active. Run: bash scripts/status.sh"
fi

