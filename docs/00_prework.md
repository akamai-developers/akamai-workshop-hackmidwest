# Setup

[Workshop home](../README.md) · [Live session](workshop.md)

Complete the local setup before the workshop. Add cloud access if you plan to create resources in the extended session or during the hackathon. Allow extra time for account activation and package downloads.

## 1. Prepare your laptop

Use macOS, Linux, or Ubuntu under [WSL 2](https://learn.microsoft.com/windows/wsl/install). The deployment scripts use Bash. Install Git and Python 3.12 to match the workshop container, then check:

```bash
git --version
python3 --version
```

On Ubuntu, install the virtual environment package if needed:

```bash
sudo apt update
sudo apt install -y python3-venv
```

You also need your team's inference key from the organizers. Keep it out of notebook source, frontend code, and screenshots.

## 2. Download and install

```bash
git clone https://github.com/akamai-developers/akamai-workshop-hackmidwest.git
cd akamai-workshop-hackmidwest
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
```

All shell commands in these materials run from `akamai-workshop-hackmidwest`, unless a step says otherwise. The install includes the starter, notebooks, Linode CLI, and tests. In a new terminal, return to this directory and activate `.venv` again.

Open `.env` in your editor and replace the placeholder key:

```ini
OPENAI_BASE_URL=https://ws.akamai-workshops.com/v1
OPENAI_API_KEY=paste_your_team_key_here
```

Leave the other service settings empty for now. `.env` is ignored by Git, but that does not protect a key copied into another file or output.

## 3. Verify inference

```bash
python -m agent --once "Say hello in one sentence."
```

Success is a returned answer. The startup display uses these existing status labels:

| Label | Component | Initial state |
|---|---|---|
| `brain` | Inference client | `live` means configured; the returned answer verifies the call |
| `knowledge` | Document source | `fallback`: local sample files |
| `memory` | Conversation and vector store | `fallback`: process memory |
| `reflexes` | Valkey cache and counters | `off` until configured |

Open the notebooks:

```bash
jupyter notebook notebooks/
```

Select `00_quickstart.ipynb` and the kernel for your workshop environment. During the core session you only need its setup and chat cells. If a key or request fails, see [troubleshooting](troubleshooting.md#inference).

## 4. Create or confirm your cloud account

For the cloud labs, use [the workshop signup link](http://login.linode.com/signup?promo=akm-dev-hack-mid-300-100826-K277). The supplied promotion advertises $300 in credit; confirm eligibility, amount, and expiration with the organizers and in Cloud Manager before creating resources. Credit does not remove the need to track charges.

Sign in to [Cloud Manager](https://cloud.linode.com). Complete any account verification, then check **Administration > Billing**. If activation is pending, follow the email instructions or [account troubleshooting guidance](https://techdocs.akamai.com/cloud-computing/docs/troubleshooting-cloud-manager-errors). You can still use the inference notebooks while waiting.

## 5. Configure the Linode CLI

Create a personal access token at [API Tokens](https://cloud.linode.com/profile/tokens). Use a short expiry that covers the event. The supplied scripts expect these scopes:

| Scope | Access | Used for |
|---|---|---|
| Account | Read Only | Account lookup and Object Storage CLI |
| Object Storage | Read/Write | Buckets and access keys |
| Databases | Read/Write | Database creation and deployment scripts' database checks |
| Linodes | Read/Write | VM deployment |
| Firewalls | Read/Write | VM network rules |
| Kubernetes | Read/Write | LKE deployment and full teardown |
| NodeBalancers | Read/Write | LKE load balancer and full teardown |

If you use only manual commands for one service, grant only the scopes those commands need. The automation and teardown scripts inspect several services even on a partial deployment. Leave unrelated scopes disabled. See [token management](https://techdocs.akamai.com/cloud-computing/docs/manage-personal-access-tokens).

If your shell already sets `LINODE_CLI_TOKEN` for another project, unset it first. With that variable set, `linode-cli obj` cannot save the access key it creates and refuses to run. This prints `set` when the variable is present and nothing when it is not:

```bash
echo ${LINODE_CLI_TOKEN:+set}
```

```bash
linode-cli configure --token
linode-cli profile view --format username
linode-cli regions view us-sea --format id,label,status
linode-cli obj --help
```

Paste the token at the CLI prompt. The scripts specify region and plans, so you can skip CLI defaults. Confirm the displayed account is the one your team intends to use.

## 6. Prepare deployment tools

For a Linode deployment, check for an SSH key:

```bash
ls ~/.ssh/id_ed25519.pub
```

If it is missing, create one:

```bash
ssh-keygen -t ed25519 -C "hackmidwest"
```

If your private key has a passphrase, load it into your SSH agent before using the deployment script:

```bash
ssh-add ~/.ssh/id_ed25519
```

For LKE, install [kubectl](https://kubernetes.io/docs/tasks/tools/) with a version compatible with the cluster version. Docker on your laptop is optional; the Linode script installs Docker on the VM.

## Ready check

- A local model request returns an answer.
- Notebook 00 opens with the intended Python kernel.
- For cloud labs, your account is activated and any credit is visible.
- The CLI shows the correct account, and required tools are installed.
- You have reviewed [costs and cleanup](costs.md).

Continue to the [live session](workshop.md) or choose a [project path](build.md).
