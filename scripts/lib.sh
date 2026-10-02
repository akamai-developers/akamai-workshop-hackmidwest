# Settings and helpers shared by the scripts in this folder. They source it; you do not run it.
# Every resource the kit creates lives in Seattle (us-sea) and has a label that starts with hackmidwest-.
# Written for bash 3.2 too, because that is what macOS ships.

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO" || exit 1
export PATH="$REPO/.venv/bin:$PATH"  # linode-cli and python from the repository's virtual environment

REGION=us-sea
CLUSTER=us-sea-1  # the Object Storage cluster in Seattle
OBJ_ENDPOINT=https://us-sea-1.linodeobjects.com
DB_LABEL=hackmidwest-db
DB_TYPE=g6-nanode-1
DB_ENGINE=postgresql/17
KEY_LABEL=hackmidwest-key
FIREWALL_LABEL=hackmidwest-fw
LINODE_LABEL=hackmidwest-agent
LINODE_TYPE=g6-standard-1
LINODE_IMAGE=linode/ubuntu24.04
LKE_LABEL=hackmidwest-lke
SSH_KEY=${SSH_KEY:-$HOME/.ssh/id_ed25519}

if [[ ! -f .env ]]; then
  echo "No .env file. Run: cp .env.example .env"
  exit 1
fi
if ! command -v linode-cli >/dev/null; then
  echo "linode-cli not found. Run: pip install -r requirements.txt"
  exit 1
fi

# get_env KEY: print KEY's value from .env, without surrounding quotes. Prints nothing if KEY is missing.
get_env() {
  { grep "^$1=" .env || true; } | tail -n 1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']\$//"
}

# set_env KEY VALUE: replace the KEY= line in .env, or add one at the end. Never adds a second KEY line.
set_env() {
  local tmp
  tmp=$(mktemp)
  KEY="$1" VALUE="$2" awk '
    BEGIN { key = ENVIRON["KEY"]; line = key "=" ENVIRON["VALUE"] }
    index($0, key "=") == 1 { if (!done) print line; done = 1; next }
    { print }
    END { if (!done) print line }
  ' .env > "$tmp" && cat "$tmp" > .env
  rm -f "$tmp"
}

# my_ip: this machine's public IPv4 address, for the database allow list.
my_ip() {
  curl -s --max-time 10 https://api.ipify.org || curl -s --max-time 10 https://ipv4.icanhazip.com
}

# bucket_name: hackmidwest- plus 8 characters derived from your account, the same every time you run it.
# Bucket names are shared by every Akamai customer in a region, so a fixed name would be taken.
bucket_name() {
  local euuid
  euuid=$(linode-cli account view --text --no-headers --format euuid)
  echo "hackmidwest-$(python -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:8])' "$euuid")"
}

# db_id: the id of the database labeled hackmidwest-db, or nothing.
db_id() {
  linode-cli databases postgresql-list --label "$DB_LABEL" --text --no-headers --format id
}

# minutes_since TIMESTAMP: how long ago an API timestamp such as 2026-10-02T01:23:45 was, like "12 min 5 s".
minutes_since() {
  python -c '
import sys
from datetime import datetime, timezone
start = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
seconds = int((datetime.now(timezone.utc) - start).total_seconds())
print(f"{seconds // 60} min {seconds % 60} s")' "$1"
}

# wait_for SECONDS WHAT COMMAND...: run COMMAND every 5 seconds until it succeeds. Fail after SECONDS.
wait_for() {
  local limit=$1 what=$2 waited=0
  shift 2
  until "$@" >/dev/null 2>&1; do
    if (( waited >= limit )); then
      echo "Gave up after $limit seconds waiting for $what."
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
}
