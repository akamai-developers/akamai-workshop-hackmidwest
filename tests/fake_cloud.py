"""A fake Akamai account for tests/test_scripts.py.

The scripts call linode-cli, curl, ssh, scp, kubectl, and sleep. In the tests, wrappers in the scratch
repository's .venv/bin run this file instead, with the command's name first. It keeps the account in
state.json and logs every call to calls.jsonl, both in $FAKE_CLOUD. It answers the way linode-cli 5.69
did on 2026-10-02: --text prints tab-separated columns, and a list value prints as words joined by spaces.
The account also holds resources that are not the kit's, so a test can show the scripts never touch them.
"""
import base64
import json
import os
import sys
from pathlib import Path

HOME = Path(os.environ["FAKE_CLOUD"])
MY_IP, LINODE_IP, NODE_IP, NB_IP = "203.0.113.25", "198.51.100.7", "198.51.100.30", "198.51.100.20"
DB_HOST = "localhost"  # status.sh waits until the host resolves; localhost does without a network
DB_PASSWORD = "Pa55:w@rd/x_1"  # real ones are letters, digits, and _; these characters test the encoding
HEALTH = {role: {"state": "live", "detail": role} for role in ("brain", "knowledge", "memory", "reflexes")}
NOT_OURS = {"linodes": {"1001": "hackathon-demo-gpu"}, "nodebalancers": {"1002": "hackathon-demo-nb"},
            "keys": {"1003": "hackathon-demo-key"}, "buckets": ["hackathon-demo-models"]}


def load() -> dict:
    path = HOME / "state.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"databases": {}, "firewalls": {}, "linodes": dict(NOT_OURS["linodes"]), "clusters": {},
            "nodebalancers": dict(NOT_OURS["nodebalancers"]), "keys": dict(NOT_OURS["keys"]),
            "buckets": list(NOT_OURS["buckets"]), "allow_list": [], "clock": 0, "service": False}


def option(args: list, name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def options(args: list, name: str) -> list:
    return [args[i + 1] for i, arg in enumerate(args) if arg == name]


def table(args: list, **fields) -> str:
    """One row the way --text prints it: the --format columns, tab-separated, with a header unless --no-headers."""
    columns = (option(args, "--format") or ",".join(fields)).split(",")
    row = "\t".join(" ".join(map(str, v)) if isinstance(v, list) else str(v) for v in (fields[c] for c in columns))
    return row if "--no-headers" in args else "\t".join(columns) + "\n" + row


def by_label(resources: dict, args: list, **fields) -> str:
    """A list command. With --label, only an exact match, like the API's filter."""
    label = option(args, "--label")
    rows = [table(args, id=i, label=l, **fields) for i, l in resources.items() if label is None or l == label]
    return "\n".join(rows)


def fail(message: str, code: int = 1):
    print(message, file=sys.stderr)
    sys.exit(code)


def linode_cli(args: list, state: dict) -> str:
    group, action = args[0], args[1]
    target = args[2] if len(args) > 2 and not args[2].startswith("--") else None
    if group == "account":
        return table(args, euuid="E1AF5EEC-526F-487D-B317EBEB34C87D71")
    if group == "databases":
        databases = state["databases"]
        if action == "postgresql-list":
            return by_label(databases, args, status="active")
        if action == "postgresql-create":
            databases["533120"] = option(args, "--label")
            state["allow_list"] = options(args, "--allow_list")
            state["db_created"] = state["clock"]
            return table(args, id=533120, label=option(args, "--label"), region=option(args, "--region"),
                         type=option(args, "--type"), engine="postgresql", version="17", status="provisioning")
        if target not in databases:
            fail("Request failed: 404")
        if action == "postgresql-view":
            status = "active" if state["clock"] - state["db_created"] >= 30 else "provisioning"  # sleep moves the clock
            return table(args, status=status, created="2026-10-02T01:14:28", port=15268,
                         allow_list=state["allow_list"], **{"hosts.primary": DB_HOST})
        if action == "postgresql-creds-view":
            return table(args, username="akmadmin", password=DB_PASSWORD)
        if action == "postgresql-update":
            state["allow_list"] = options(args, "--allow_list")
            return table(args, id=target, label=databases[target], status="updating")
        if action == "postgresql-delete":
            del databases[target]
            return ""
    if group == "obj":
        bucket = args[2]
        if action == "ls":
            if bucket not in state["buckets"]:
                fail(f"No bucket named {bucket}", 2)  # what the real plugin prints, with exit code 2
            return "2026-10-02 01:15  1260  parking.md"
        if action == "mb":
            state["buckets"].append(bucket)
            return f"Bucket {bucket} created"
        if action == "rb":
            state["buckets"].remove(bucket)
            return f"Bucket {bucket} removed"
    if group == "object-storage":
        keys = state["keys"]
        if action == "keys-create":
            keys["6635050"] = option(args, "--label")
            return table(args, id=6635050, access_key="ABCDEFGHIJKLMNOPQRST", secret_key="abcdefghijklmnopqrstuvwxyz0123456789ABCD")
        if target not in keys:
            fail("Request failed: 404")
        if action == "keys-view":
            return table(args, id=target, label=keys[target])
        if action == "keys-delete":
            del keys[target]
            return ""
    if group in ("firewalls", "linodes", "lke", "nodebalancers"):
        resources = state["clusters" if group == "lke" else group]
        new_id = {"firewalls": "187247005", "linodes": "107237550", "lke": "662761", "nodebalancers": "2504574"}[group]
        if action in ("list", "clusters-list"):
            if group == "nodebalancers" and option(args, "--ipv4"):
                return table(args, id=new_id) if option(args, "--ipv4") == NB_IP and new_id in resources else ""
            return by_label(resources, args, ipv4=LINODE_IP)
        if action == "versions-list":
            return "1.36\n1.35"
        if action in ("create", "cluster-create"):
            resources[new_id] = option(args, "--label")
            return table(args, id=new_id, label=option(args, "--label"), region=option(args, "--region"),
                         status="provisioning", ipv4=LINODE_IP, k8s_version=option(args, "--k8s_version"))
        if target not in resources:
            fail("Request failed: 404")
        if action == "view":
            return table(args, id=target, label=resources[target], status="running", ipv4=LINODE_IP)
        if action == "kubeconfig-view":
            return base64.b64encode(b"apiVersion: v1\nkind: Config\n").decode()
        if action == "update":
            resources[target] = option(args, "--label")
            return table(args, id=target, label=resources[target], ipv4=NB_IP)
        if action in ("delete", "cluster-delete"):
            del resources[target]
            return ""
    fail(f"fake linode-cli does not know: {' '.join(args)}")


def kubectl(args: list, state: dict, piped: str) -> str:
    words = " ".join(args)
    if words.startswith("get nodes"):
        if "jsonpath" in words:
            return f"{NODE_IP} 2600:3c0a::f03c:95ff:fe00:1"
        return "lke662761-981465-w54sh   Ready    <none>   12s   v1.36.3"
    if "--dry-run=client" in args:
        if "--from-file=agent.tgz" in args:  # keep the code the pod would unpack, for the test to read
            (HOME / "configmap-agent.tgz").write_bytes(Path("agent.tgz").read_bytes())
        return "apiVersion: v1\nkind: Placeholder\n"
    if words == "apply -f -":
        return "configured" if piped else fail("no input")
    if words.startswith("apply -f k8s/"):
        state["service"] = True
        state["nodebalancers"]["2504574"] = "lke662761-97045693dd69"  # the cluster makes its own NodeBalancer
        return "deployment.apps/agent created"
    if "get deployment agent" in words:
        return "deployment.apps/agent" if state["service"] else fail("Error from server (NotFound)")
    if "get service agent" in words:
        return NB_IP if state["service"] else fail("Error from server (NotFound)")
    if words.startswith("-n hackmidwest rollout"):
        return "deployment.apps/agent rolled out"
    fail(f"fake kubectl does not know: {words}")


def curl(args: list, state: dict) -> str:
    url = next(arg for arg in args if arg.startswith("http"))
    if "ipify" in url or "icanhazip" in url:
        return MY_IP
    up = (LINODE_IP in url and "107237550" in state["linodes"]) or (NB_IP in url and state["service"])
    return json.dumps({"status": "ok", **HEALTH}) if up else fail("curl: (7) Failed to connect", 7)


def main():
    name, args = sys.argv[1], sys.argv[2:]
    piped = sys.stdin.read() if name == "kubectl" and args[-1:] == ["-"] else None
    with open(HOME / "calls.jsonl", "a") as log:
        log.write(json.dumps({"cmd": name, "argv": args}) + "\n")
    state = load()
    if name == "linode-cli":
        out = linode_cli(args, state)
    elif name == "kubectl":
        out = kubectl(args, state, piped)
    elif name == "curl":
        out = curl(args, state)
    elif name == "ssh" and args[-3:] == ["cloud-init", "status", "--wait"]:
        out = "status: done"
    elif name == "sleep":  # returns at once, but the account sees the time pass
        state["clock"] += int(args[0])
        out = ""
    else:  # ssh and scp succeed
        out = ""
    (HOME / "state.json").write_text(json.dumps(state))
    if out:
        print(out)


if __name__ == "__main__":
    main()
