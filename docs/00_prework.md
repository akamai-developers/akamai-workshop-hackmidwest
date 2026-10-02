# Pre-work: account, token, and tools

```
  your laptop                         Akamai Cloud (us-sea, Seattle)
  -----------------                   --------------------------------------------------------
  linode-cli / python  ---creates-->  Linode "hackmidwest-agent" (body)
                                        docker compose
                                          agent (FastAPI, port 8000)   --tools-->  Object Storage bucket (knowledge)
                                          valkey (reflexes)            --sql---->  Managed PostgreSQL + pgvector (memory)
                                                                       --https-->  ws.akamai-workshops.com/v1 (brain)
```

This page adds no role yet. It sets up the left side of the picture: your laptop, and the permission to create things on the right.

## Overview

Do this the night before. Signing up and installing tools is the slow, fiddly part, and it goes faster without a room full of people sharing the Wi-Fi. When you finish, you have an Akamai Cloud account with $300 of credit, `linode-cli` connected to it, this repository on your laptop, and the brain answering. Nothing on this page costs money.

## Learning objectives

By the end of this page you will be able to:

- Create an Akamai Cloud account with $300 of credit
- Install the agent, the notebooks, and `linode-cli` into one Python virtual environment
- Run the agent against the hackathon inference endpoint
- Create a personal access token with only the scopes this kit needs
- Run `linode-cli` against your own account

## Prerequisites

- A laptop running macOS or Linux. On Windows, install [WSL 2](https://learn.microsoft.com/windows/wsl/install) and do everything inside its Ubuntu terminal, because the scripts are bash.
- Python 3.10 or newer and git. Check with `python3 --version` and `git --version`. macOS ships Python 3.9, which is too old: install 3.12 with `brew install python@3.12` or from [python.org](https://www.python.org/downloads/), and type `python3.12` where the steps say `python3`. On Ubuntu and in WSL, also run `sudo apt install -y python3-venv`.
- A credit card or PayPal account for sign-up. Akamai uses it to verify you. The credit pays for what the kit uses.
- Your team's inference key from the organizers. It starts with `hk_`.
- About 15 minutes

## Step 1: Create your account with $300 of credit

Open the sign-up link and create the account:

**[http://login.linode.com/signup?promo=akm-dev-git-300-72326-P153](http://login.linode.com/signup?promo=akm-dev-git-300-72326-P153)**

The link carries the promo code, so the credit lands on the account by itself. Confirm your email when asked. You end up in Cloud Manager at [cloud.linode.com](https://cloud.linode.com), the web console where everything you create appears.

To check the credit, open **Administration > Billing** in Cloud Manager. The promotion shows with the amount remaining and the date it expires.

> NOTE: If you signed up without the link and the account is less than 90 days old, open **Administration > Billing**, choose **Add a promo code**, and enter `akm-dev-git-300-72326-P153`. See [Add a promo code](https://techdocs.akamai.com/cloud-computing/docs/add-a-promo-code) for the rules.

## Step 2: Get the code and install everything

Clone the repository and create a virtual environment inside it:

```bash
git clone https://github.com/akamai-developers/akamai-workshop-hackmidwest.git
cd akamai-workshop-hackmidwest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

One install covers the notebooks, the agent, the tests, and `linode-cli`. It also installs `boto3`, which the agent uses for Object Storage and which turns on the `linode-cli obj` commands for buckets. Everything lands in `.venv`, so nothing touches your system Python.

Your prompt now starts with `(.venv)`. Every command in the guides assumes it does. In a new terminal, run `source .venv/bin/activate` from the repository folder first.

## Step 3: Put your team key in .env

The agent reads its settings from `.env`, which git ignores so the key never reaches GitHub.

```bash
cp .env.example .env
```

Open `.env` in a text editor, for example `nano .env`, and replace `hk_paste_your_team_key_here` with your team key. In nano, save with Ctrl+O and Enter, then quit with Ctrl+X. Finder and some file pickers hide files whose names start with a dot. Leave the other values empty. The guides fill them in as you create each service.

Ask the brain something:

```bash
python -m agent --once "Say hello"
```

```
brain      live      hackathon-chat at https://ws.akamai-workshops.com/v1
knowledge  fallback  reading docs/sample/ on this machine. Set OBJ_* in .env to use your bucket.
memory     fallback  kept in this process only, forgotten on restart. Set DATABASE_URL in .env.
reflexes   off       no cache and no rate limit. Set VALKEY_URL to turn them on.
Hello!
```

The first four lines say which parts of the agent are live. Right now only the brain is. The guides turn on the rest, one line at a time. You do not need an Akamai account for this step; the brain is the hackathon's shared endpoint.

## Step 4: Create a personal access token

`linode-cli` acts on your account with a personal access token. A token is a password with a scope: it can only touch the products you allow, and it stops working on the expiry date.

In Cloud Manager, open your user name in the top right, then **API Tokens**, then **Create a Personal Access Token**. You can also go straight to [cloud.linode.com/profile/tokens](https://cloud.linode.com/profile/tokens). Fill it in like this:

| Field | Value | Why |
|---|---|---|
| Label | `hackmidwest` | So you can find and revoke it later |
| Expiry | 1 month | Long enough for the event. If you forget to delete it, it stops working on its own |
| Account | Read Only | `linode-cli obj` checks the account before it touches buckets |
| Databases | Read/Write | Guide 01 creates the PostgreSQL database |
| Firewalls | Read/Write | Guide 03 creates the Cloud Firewall |
| Kubernetes | Read/Write | Guide 04 (optional) creates the LKE cluster |
| Linodes | Read/Write | Guide 03 creates the Linode |
| NodeBalancers | Read/Write | Guide 04 (optional) puts a load balancer in front of the cluster |
| Object Storage | Read/Write | Guide 01 creates the bucket and its access key |
| Everything else | No Access | The kit does not use it |

Choose **Create Token** and copy the token. Cloud Manager shows it once. Keep it in your password manager until step 5, and never paste it into a chat or a commit.

## Step 5: Connect linode-cli to your account

```bash
linode-cli configure --token
```

Paste the token when it asks for a Personal Access Token. It then offers defaults for region, plan, and image. Press Enter to skip each one, and Enter again for the two yes or no questions. Every command in this kit names its region, plan, and image, so the defaults never matter.

The output ends with your user name:

```
Configuring your-username
...
Active user is now your-username
```

The token is saved in `~/.config/linode-cli`. Check that it works:

```bash
linode-cli regions view us-sea --format id,label,status
```

```
┌────────┬─────────────┬────────┐
│ id     │ label       │ status │
├────────┼─────────────┼────────┤
│ us-sea │ Seattle, WA │ ok     │
└────────┴─────────────┴────────┘
```

Everything in this kit runs in `us-sea`. Seattle has every service the kit uses: Linodes, Object Storage, Managed Databases, Kubernetes, and Cloud Firewall.

## Step 6: Make an SSH key

Guide 03 logs in to your Linode with an SSH key instead of a password. Check whether you have one:

```bash
ls ~/.ssh/id_ed25519.pub
```

If the file is missing, make one. Press Enter to accept the default file name. A passphrase is optional.

```bash
ssh-keygen -t ed25519 -C "hackmidwest"
```

## Step 7 (optional): Install Docker Desktop

The agent runs in Docker on your Linode, and Docker installs itself there. You only need [Docker Desktop](https://docs.docker.com/get-started/get-docker/) on your laptop if you want to run the container locally. Skip it if the download is slow.

## Validation

Run the night-before checklist. Every line should match before you go to bed.

| Check | Command | You should see |
|---|---|---|
| $300 credit | Cloud Manager, **Administration > Billing** | The promotion and its remaining credit |
| linode-cli installed | `linode-cli --version` | `linode-cli v5.69.0` or newer |
| Token works | `linode-cli profile view --format username` | Your user name |
| Seattle is open | `linode-cli regions view us-sea --format id,label,status` | `us-sea`, `Seattle, WA`, `ok` |
| Bucket commands work | `linode-cli obj --help` | A table that includes `mb  Creates a new bucket` |
| SSH key exists | `ls ~/.ssh/id_ed25519.pub` | The file path, no error |
| Brain answers | `python -m agent --once "Say hello"` | A one-line greeting after the status lines |
| Docker (optional) | `docker --version` | Any version |

**Show the judges:** nothing to show yet. `linode-cli profile view` proves your laptop is talking to your own Akamai Cloud account.

## Clean up

Nothing to clean up. This page created no cloud resources and nothing is billed.

Two things to protect: the token and `.env`. Both stay on your laptop. After the event, delete the token at [cloud.linode.com/profile/tokens](https://cloud.linode.com/profile/tokens).

## Next steps

On the day, start with [Guide 01: Knowledge in Object Storage](01_knowledge.md). Its first step starts the database, because the database takes the longest to create.
