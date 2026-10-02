#!/usr/bin/env bash
# Waits for the database to become active, then writes DATABASE_URL into .env.
# The URL asks for TLS (sslmode=require), because Managed Databases refuse unencrypted connections.
#   bash scripts/status.sh
set -euo pipefail
source "$(dirname "$0")/lib.sh"

id=$(db_id)
if [[ -z $id ]]; then
  echo "No database labeled $DB_LABEL. Create it first: guide 01, step 1, or bash scripts/up.sh"
  exit 1
fi

created=$(linode-cli databases postgresql-view "$id" --text --no-headers --format created)
while true; do
  status=$(linode-cli databases postgresql-view "$id" --text --no-headers --format status)
  echo "$(date +%H:%M:%S)  $DB_LABEL is $status, $(minutes_since "$created") after it was created"
  [[ $status == active ]] && break
  sleep 30
done

host=$(linode-cli databases postgresql-view "$id" --text --no-headers --format hosts.primary)
port=$(linode-cli databases postgresql-view "$id" --text --no-headers --format port)

# The host name can take a couple of minutes to appear in DNS after the database turns active.
resolves() { python -c 'import socket, sys; socket.gethostbyname(sys.argv[1])' "$host"; }
if ! resolves 2>/dev/null; then
  echo "Waiting for $host to appear in DNS."
  wait_for 600 "$host to resolve" resolves
fi
echo "$(date +%H:%M:%S)  $host resolves, $(minutes_since "$created") after the database was created"
read -r user password <<<"$(linode-cli databases postgresql-creds-view "$id" --text --no-headers --format username,password)"
password=$(python -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$password")

set_env DATABASE_URL "postgresql://$user:$password@$host:$port/defaultdb?sslmode=require"
echo
echo "Wrote DATABASE_URL for $host:$port to .env. Next: python scripts/db_init.py"
