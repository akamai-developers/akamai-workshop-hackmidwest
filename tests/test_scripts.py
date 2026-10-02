"""The bash scripts: line endings and a syntax check for each, the .env helpers in scripts/lib.sh, and every script against a fake account."""
import base64
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((ROOT / "scripts").glob("*.sh"))


@pytest.mark.parametrize("script", SCRIPTS, ids=[s.name for s in SCRIPTS])
def test_every_script_parses(script):
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_git_checks_out_every_file_with_lf_line_endings():
    """Git for Windows checks files out with CRLF by default, and bash cannot run a script with CRLF."""
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    out = subprocess.run(["git", "check-attr", "--stdin", "-z", "eol"], cwd=ROOT, input=files,
                         capture_output=True, text=True, check=True).stdout.split("\0")
    not_lf = [path for path, value in zip(out[0::3], out[2::3]) if value != "lf"]
    assert not not_lf, f"give these eol=lf in .gitattributes: {not_lf}"


def scratch_repo(tmp_path: Path, env_text: str | None) -> Path:
    """A copy of the repository layout lib.sh expects: scripts/lib.sh, a stub linode-cli, and .env."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "lib.sh", tmp_path / "scripts" / "lib.sh")
    fake_cli = tmp_path / ".venv" / "bin" / "linode-cli"  # lib.sh refuses to run without linode-cli
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("#!/bin/sh\nexit 0\n")
    fake_cli.chmod(0o755)
    if env_text is not None:
        (tmp_path / ".env").write_text(env_text)
    return tmp_path


def run_with_lib(tmp_path: Path, env_text: str | None, commands: str) -> subprocess.CompletedProcess:
    """Run commands after sourcing lib.sh, the way every script starts."""
    scratch_repo(tmp_path, env_text)
    script = f"set -euo pipefail\nsource scripts/lib.sh\n{commands}\necho done"
    return subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True,
                          env={**os.environ, "HOME": str(tmp_path)})


def test_get_env_of_a_missing_key_is_empty_and_does_not_stop_the_script(tmp_path):
    result = run_with_lib(tmp_path, "OPENAI_API_KEY=hk_x\n", 'value=$(get_env OBJ_KEY_ID)\necho "[$value]"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["[]", "done"]


def test_get_env_strips_quotes(tmp_path):
    result = run_with_lib(tmp_path, "OBJ_BUCKET='hackmidwest-abc'\nDATABASE_URL=\"postgresql://x\"\n",
                          "get_env OBJ_BUCKET\nget_env DATABASE_URL")
    assert result.stdout.splitlines()[:2] == ["hackmidwest-abc", "postgresql://x"]


def test_get_env_ignores_windows_line_endings(tmp_path):
    result = run_with_lib(tmp_path, "OBJ_BUCKET=hackmidwest-abc\r\nOBJ_KEY_ID='1234567'\r\n",
                          'printf "[%s]\\n" "$(get_env OBJ_BUCKET)" "$(get_env OBJ_KEY_ID)"')
    assert result.stdout.split("\n")[:2] == ["[hackmidwest-abc]", "[1234567]"]


def test_set_env_replaces_in_place_adds_new_keys_and_never_duplicates(tmp_path):
    env_text = "OPENAI_API_KEY=hk_x\nOBJ_BUCKET=\n# OBJ_BUCKET=a comment stays a comment\nDATABASE_URL=\n"
    result = run_with_lib(tmp_path, env_text, "\n".join([
        "set_env OBJ_BUCKET hackmidwest-one",
        "set_env OBJ_BUCKET hackmidwest-two",
        "set_env DATABASE_URL 'postgresql://akmadmin:p%24ss@host:15268/defaultdb?sslmode=require'",
        "set_env NEW_KEY 'a&b\\c$d=e/f'",
    ]))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text().splitlines() == [
        "OPENAI_API_KEY=hk_x",
        "OBJ_BUCKET=hackmidwest-two",
        "# OBJ_BUCKET=a comment stays a comment",
        "DATABASE_URL=postgresql://akmadmin:p%24ss@host:15268/defaultdb?sslmode=require",
        "NEW_KEY=a&b\\c$d=e/f",
    ]


def test_scripts_stop_without_env_file(tmp_path):
    result = run_with_lib(tmp_path, None, "echo should-not-print")
    assert result.returncode != 0
    assert "cp .env.example .env" in result.stdout
    assert "should-not-print" not in result.stdout


def test_down_succeeds_when_everything_is_already_gone(tmp_path):
    """A second run of down.sh, or one after the guides' clean up, finds nothing and still empties .env."""
    scratch_repo(tmp_path, "OBJ_BUCKET=hackmidwest-gone1234\nOBJ_KEY_ID=\nDATABASE_URL=postgresql://x@db:1/d\n")
    shutil.copy(ROOT / "scripts" / "down.sh", tmp_path / "scripts" / "down.sh")
    # A linode-cli that finds nothing, and answers obj ls the way the real one does for a missing bucket.
    fake_cli = tmp_path / ".venv" / "bin" / "linode-cli"
    fake_cli.write_text('#!/bin/sh\nif [ "$1 $2" = "obj ls" ]; then echo "No bucket named $3" >&2; exit 2; fi\nexit 0\n')
    result = subprocess.run(["bash", "scripts/down.sh", "--yes"], cwd=tmp_path, capture_output=True, text=True,
                            env={**os.environ, "HOME": str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "  none" in result.stdout
    settings = dict(line.split("=", 1) for line in (tmp_path / ".env").read_text().splitlines())
    keys = ["OBJ_ENDPOINT", "OBJ_BUCKET", "OBJ_ACCESS_KEY", "OBJ_SECRET_KEY", "OBJ_KEY_ID", "DATABASE_URL"]
    assert {key: settings.get(key) for key in keys} == dict.fromkeys(keys, "")


# The whole kit against a fake account: tests/fake_cloud.py stands in for linode-cli, curl, ssh, scp, kubectl,
# and sleep. Everything else is real: bash, python, openssl, base64, tar, sed, and awk, whichever ones are on your
# PATH. On a stock Mac that means bash 3.2 and the BSD tools, the same ones a student's laptop runs the scripts with.
FAKES = ["linode-cli", "curl", "ssh", "scp", "kubectl", "sleep"]
NOT_OURS = ["1001", "1002", "1003", "hackathon-demo-models"]  # ids and a bucket in the fake account that are not the kit's


def fake_account(repo: Path) -> Path:
    """A copy of the files the scripts use, the fakes and a real python in .venv/bin, and an SSH key in HOME."""
    for folder in ["scripts", "deploy", "k8s", "agent", "docs/sample"]:
        shutil.copytree(ROOT / folder, repo / folder, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["Dockerfile", "compose.yaml", ".dockerignore"]:
        shutil.copy(ROOT / name, repo / name)
    shutil.copy(ROOT / ".env.example", repo / ".env")
    bin_dir = repo / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").symlink_to(sys.executable)
    for name in FAKES:
        (bin_dir / name).write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "tests" / "fake_cloud.py"}" {name} "$@"\n')
        (bin_dir / name).chmod(0o755)
    (repo / ".ssh").mkdir()
    (repo / ".ssh" / "id_ed25519.pub").write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake test\n")
    (repo / "agent" / "__pycache__").mkdir()  # what running the agent leaves behind; the tarball must skip it
    (repo / "agent" / "__pycache__" / "brain.cpython-312.pyc").write_bytes(b"compiled")
    return repo


def read_env(repo: Path) -> dict:
    lines = (repo / ".env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Run the scripts in the order a team would, against one fake account. Each run keeps its result and its calls."""
    repo = fake_account(tmp_path_factory.mktemp("kit"))
    log = repo / "calls.jsonl"
    steps = [("up", "scripts/up.sh", None), ("up again", "scripts/up.sh", None), ("status", "scripts/status.sh", None),
             ("deploy_linode", "scripts/deploy_linode.sh", None), ("deploy_lke", "scripts/deploy_lke.sh", None),
             ("down, answer no", "scripts/down.sh", "no\n"), ("down", "scripts/down.sh", "yes\n")]
    runs = {}
    for name, script, answer in steps:
        before = len(log.read_text().splitlines()) if log.exists() else 0
        result = subprocess.run(["bash", script], cwd=repo, input=answer, capture_output=True, text=True,
                                env={**os.environ, "HOME": str(repo), "FAKE_CLOUD": str(repo)})
        calls = [json.loads(line) for line in log.read_text().splitlines()[before:]]
        kubeconfig = repo / "hackmidwest-kubeconfig.yaml"
        runs[name] = {"result": result, "calls": calls, "env": read_env(repo), "repo": repo,
                      "files": sorted(p.name for p in repo.iterdir()),
                      "kubeconfig": kubeconfig.read_text() if kubeconfig.exists() else None}
    return runs


def cli(run: dict, *prefix: str) -> list[list[str]]:
    """The linode-cli calls of one run that start with these words."""
    return [c["argv"] for c in run["calls"] if c["cmd"] == "linode-cli" and c["argv"][:len(prefix)] == list(prefix)]


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def flags(argv: list[str], name: str) -> list[str]:
    return [argv[i + 1] for i, arg in enumerate(argv) if arg == name]


@pytest.mark.parametrize("name", ["up", "up again", "status", "deploy_linode", "deploy_lke", "down"])
def test_each_script_succeeds(runs, name):
    result = runs[name]["result"]
    assert result.returncode == 0, result.stdout + result.stderr


def test_up_starts_the_database_then_makes_a_bucket_and_a_key_for_it_alone(runs):
    run = runs["up"]
    [create] = cli(run, "databases", "postgresql-create")
    assert [flag(create, f) for f in ["--label", "--region", "--type", "--engine", "--cluster_size"]] == \
        ["hackmidwest-db", "us-sea", "g6-nanode-1", "postgresql/17", "1"]
    assert flags(create, "--allow_list") == ["203.0.113.25/32"]
    bucket = run["env"]["OBJ_BUCKET"]
    assert len(bucket) == len("hackmidwest-") + 8 and bucket.startswith("hackmidwest-")
    assert cli(run, "obj", "mb") == [["obj", "mb", bucket, "--cluster", "us-sea-1"]]
    [key] = cli(run, "object-storage", "keys-create")
    assert json.loads(flag(key, "--bucket_access")) == [{"region": "us-sea", "bucket_name": bucket, "permissions": "read_write"}]
    assert {k: run["env"][k] for k in ["OBJ_ENDPOINT", "OBJ_ACCESS_KEY", "OBJ_SECRET_KEY", "OBJ_KEY_ID"]} == {
        "OBJ_ENDPOINT": "https://us-sea-1.linodeobjects.com", "OBJ_ACCESS_KEY": "ABCDEFGHIJKLMNOPQRST",
        "OBJ_SECRET_KEY": "abcdefghijklmnopqrstuvwxyz0123456789ABCD", "OBJ_KEY_ID": "6635050"}
    assert "hackmidwest-db is provisioning" in run["result"].stdout


def test_up_run_twice_creates_nothing_new(runs):
    run = runs["up again"]
    assert [c for c in cli(run) if c[1] in ("postgresql-create", "mb", "keys-create")] == []
    assert run["env"] == runs["up"]["env"]


def test_status_waits_for_active_and_writes_a_tls_url_with_the_password_encoded(runs):
    run = runs["status"]
    assert run["result"].stdout.count("hackmidwest-db is provisioning") == 1
    assert "hackmidwest-db is active" in run["result"].stdout
    assert run["env"]["DATABASE_URL"] == \
        "postgresql://akmadmin:Pa55%3Aw%40rd%2Fx_1@localhost:15268/defaultdb?sslmode=require"


def test_deploy_linode_builds_the_body_and_lets_it_into_the_database(runs):
    run = runs["deploy_linode"]
    [firewall] = cli(run, "firewalls", "create")
    [rules] = json.loads(flag(firewall, "--rules.inbound"))
    assert (flag(firewall, "--rules.inbound_policy"), rules["ports"]) == ("DROP", "22,8000")
    [linode] = cli(run, "linodes", "create")
    assert [flag(linode, f) for f in ["--label", "--region", "--type", "--image", "--firewall_id"]] == \
        ["hackmidwest-agent", "us-sea", "g6-standard-1", "linode/ubuntu24.04", "187247005"]
    user_data = base64.b64decode(flag(linode, "--metadata.user_data"))
    assert user_data == (ROOT / "deploy" / "cloud-init.yaml").read_bytes()  # the file as is: no secrets in user data
    [update] = cli(run, "databases", "postgresql-update")
    assert flags(update, "--allow_list") == ["203.0.113.25/32", "198.51.100.7/32"]
    [copy] = [c["argv"] for c in run["calls"] if c["cmd"] == "scp"]
    assert ".env" in copy and copy[-1] == "root@198.51.100.7:/opt/hackmidwest/"
    assert "The agent is up after" in run["result"].stdout


def test_deploy_lke_lets_the_node_in_and_names_the_nodebalancer(runs):
    run = runs["deploy_lke"]
    [cluster] = cli(run, "lke", "cluster-create")
    assert [flag(cluster, f) for f in ["--label", "--region", "--k8s_version", "--node_pools.type", "--node_pools.count"]] == \
        ["hackmidwest-lke", "us-sea", "1.36", "g6-standard-1", "1"]
    [update] = cli(run, "databases", "postgresql-update")
    assert flags(update, "--allow_list") == ["203.0.113.25/32", "198.51.100.7/32", "198.51.100.30/32"]
    assert cli(run, "nodebalancers", "update") == [["nodebalancers", "update", "2504574", "--label", "hackmidwest-nb"]]
    assert run["kubeconfig"] == "apiVersion: v1\nkind: Config\n"
    assert "agent.tgz" not in run["files"]
    with tarfile.open(run["repo"] / "configmap-agent.tgz") as code:  # what the pod unpacks and runs
        names = code.getnames()
    assert {"agent/requirements.txt", "agent/server.py", "agent/static/index.html", "docs/sample/parking.md"} <= set(names)
    assert [name for name in names if "__pycache__" in name or "/._" in name] == []
    assert "The agent is up on LKE after" in run["result"].stdout


def test_down_deletes_nothing_unless_you_type_yes(runs):
    run = runs["down, answer no"]
    assert run["result"].returncode == 1
    for kind in ["LKE cluster", "NodeBalancer", "Linode", "Cloud Firewall", "PostgreSQL", "Bucket", "Access key"]:
        assert f"\n  {kind} " in run["result"].stdout
    assert run["result"].stdout.endswith("Nothing deleted.\n")
    assert [c for c in cli(run) if "delete" in c[1] or c[1] == "rb"] == []


def test_down_deletes_every_kit_resource_and_nothing_else(runs):
    run = runs["down"]
    deleted = sorted(c[2] for c in cli(run) if "delete" in c[1] or c[1] == "rb")
    bucket = runs["up"]["env"]["OBJ_BUCKET"]
    assert deleted == sorted(["662761", "2504574", "107237550", "187247005", "533120", bucket, "6635050"])
    for argv in cli(run):
        if argv[1] in ("list", "clusters-list", "postgresql-list"):  # every lookup asks for one name or one address
            label = flag(argv, "--label") if "--label" in argv else ""
            assert label.startswith("hackmidwest-") or "--ipv4" in argv, argv
    left = json.loads((run["repo"] / "state.json").read_text())
    assert set(NOT_OURS) <= set(left["linodes"]) | set(left["nodebalancers"]) | set(left["keys"]) | set(left["buckets"])


def test_down_empties_the_service_settings_and_removes_the_kubeconfig(runs):
    run = runs["down"]
    keys = ["OBJ_ENDPOINT", "OBJ_BUCKET", "OBJ_ACCESS_KEY", "OBJ_SECRET_KEY", "OBJ_KEY_ID", "DATABASE_URL"]
    assert {key: run["env"][key] for key in keys} == dict.fromkeys(keys, "")
    assert run["env"]["OPENAI_BASE_URL"] == "https://api.openai.com/v1"
    assert runs["down, answer no"]["kubeconfig"] and run["kubeconfig"] is None
