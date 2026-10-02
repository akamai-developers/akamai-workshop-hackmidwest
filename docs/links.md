# Links

Every page this kit relies on, with one line on when you need it. The guides link here instead of repeating these.

## Your account

| Link | When you need it |
|---|---|
| [Sign up with $300 in free credit](http://login.linode.com/signup?promo=akm-dev-git-300-72326-P153) | The night before. One account per person. |
| [Add a promo code](https://techdocs.akamai.com/cloud-computing/docs/add-a-promo-code) | You signed up in the last 90 days without the link above. |
| [Cloud Manager](https://cloud.linode.com) | The whole event. Every resource the kit creates appears here. |
| [API tokens page](https://cloud.linode.com/profile/tokens) | Creating or revoking the token linode-cli uses. |
| [Manage personal access tokens](https://techdocs.akamai.com/cloud-computing/docs/manage-personal-access-tokens) | Choosing token scopes and expiry. |
| [How billing works](https://techdocs.akamai.com/cloud-computing/docs/understanding-how-billing-works) | You want to know when the hourly charges stop. |
| [Stop further billing](https://techdocs.akamai.com/cloud-computing/docs/stop-further-billing) | The hackathon is over. |
| [Status page](https://status.linode.com) | Something that worked an hour ago fails. Check here first. |

## linode-cli

| Link | When you need it |
|---|---|
| [Getting started with linode-cli](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-the-linode-cli) | First time using the CLI. |
| [Install and configure the CLI](https://techdocs.akamai.com/cloud-computing/docs/install-and-configure-the-cli) | `linode-cli configure` asks something the pre-work did not cover. |
| [linode-cli on GitHub](https://github.com/linode/linode-cli) | You hit a CLI bug or want the changelog. |
| [API reference](https://techdocs.akamai.com/linode-api/reference/api) | You want every field a command accepts. CLI flags match the API fields. |

## Object Storage (knowledge)

| Link | When you need it |
|---|---|
| [Object Storage overview](https://techdocs.akamai.com/cloud-computing/docs/object-storage) | You want the big picture. |
| [Create and manage buckets](https://techdocs.akamai.com/cloud-computing/docs/create-and-manage-buckets) | Bucket names, regions, and deleting buckets. |
| [Manage access keys](https://techdocs.akamai.com/cloud-computing/docs/manage-access-keys) | Making a key that can only reach one bucket, like the agent's. |
| [Use linode-cli with Object Storage](https://techdocs.akamai.com/cloud-computing/docs/using-the-linode-cli-with-object-storage) | The `linode-cli obj` commands: `mb`, `put`, `ls`, `rb`. |
| [Endpoint types](https://techdocs.akamai.com/cloud-computing/docs/endpoint-types) | You wonder why Seattle is `us-sea-1.linodeobjects.com`. |
| [boto3 with Object Storage](https://techdocs.akamai.com/cloud-computing/docs/using-the-aws-sdk-for-python-boto3-with-object-storage) | Changing `agent/knowledge.py`. It uses boto3. |
| [Object Storage limits](https://techdocs.akamai.com/cloud-computing/docs/object-storage-product-limits) | Uploading many or large files. |
| [Object Storage pricing](https://techdocs.akamai.com/cloud-computing/docs/object-storage-pricing) | Checking what the flat monthly fee covers. |
| [Cancel Object Storage](https://techdocs.akamai.com/cloud-computing/docs/cancel-object-storage) | Stopping the $5 a month after the event. It deletes every bucket on the account. |

## Managed Databases (memory)

| Link | When you need it |
|---|---|
| [Managed Databases overview](https://techdocs.akamai.com/cloud-computing/docs/managed-databases) | You want the big picture. |
| [Get started with Managed Databases](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-managed-databases) | Creating a database in Cloud Manager instead of the CLI. |
| [PostgreSQL on Managed Databases](https://techdocs.akamai.com/cloud-computing/docs/aiven-postgresql) | Default user `akmadmin`, database `defaultdb`, and TLS settings. |
| [Manage a database](https://techdocs.akamai.com/cloud-computing/docs/aiven-manage-database) | Access controls: the allow list of IP addresses that may connect. |
| [Engines and plans](https://techdocs.akamai.com/cloud-computing/docs/database-engines-plans) | Picking a bigger plan or a three-node cluster. |
| [Aiven-powered databases on Akamai](https://www.akamai.com/blog/developers/2025/aug/open-source-fully-managed-aiven-powered-databases-on-akamai) | Akamai's announcement, which names pgvector and pgvectorscale support. |
| [pgvector](https://github.com/pgvector/pgvector) | The `vector` type, the `<=>` distance operator, and HNSW indexes. |
| [pgvector for Python](https://github.com/pgvector/pgvector-python) | Changing `agent/memory.py`. It uses this package with psycopg. |

## Linodes (body)

| Link | When you need it |
|---|---|
| [Getting started on Akamai Cloud](https://techdocs.akamai.com/cloud-computing/docs/getting-started) | First Linode. |
| [Create a compute instance](https://techdocs.akamai.com/cloud-computing/docs/create-a-compute-instance) | Creating a Linode in Cloud Manager instead of the CLI. |
| [Choose a plan](https://techdocs.akamai.com/cloud-computing/docs/how-to-choose-a-compute-instance-plan) | Your project needs more memory or CPU. |
| [Manage SSH keys](https://techdocs.akamai.com/cloud-computing/docs/manage-ssh-keys) | Making or adding the key you log in with. |
| [Troubleshoot SSH](https://techdocs.akamai.com/cloud-computing/docs/troubleshooting-ssh-on-compute-instances) | `ssh` hangs or says permission denied. |
| [Metadata service](https://techdocs.akamai.com/cloud-computing/docs/overview-of-the-metadata-service) | How cloud-init on a new Linode receives your user data. |
| [Add user data to a new Linode](https://techdocs.akamai.com/cloud-computing/docs/add-user-data-when-deploying-a-compute-instance) | Writing your own cloud-init file. |
| [cloud-init documentation](https://cloudinit.readthedocs.io/en/latest/) | Every cloud-config key, such as `packages` and `runcmd`. |

## Cloud Firewall

| Link | When you need it |
|---|---|
| [Cloud Firewall overview](https://techdocs.akamai.com/cloud-computing/docs/cloud-firewall) | You want the big picture. |
| [Get started with Cloud Firewalls](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-cloud-firewalls) | First firewall. |
| [Create a Cloud Firewall](https://techdocs.akamai.com/cloud-computing/docs/create-a-cloud-firewall) | Creating one in Cloud Manager instead of the CLI. |
| [Manage firewall rules](https://techdocs.akamai.com/cloud-computing/docs/manage-firewall-rules) | Opening another port, for example 443. |

## LKE and NodeBalancers (optional module)

| Link | When you need it |
|---|---|
| [Linode Kubernetes Engine](https://techdocs.akamai.com/cloud-computing/docs/linode-kubernetes-engine) | You want the big picture. |
| [Install kubectl](https://kubernetes.io/docs/tasks/tools/) | Before guide 04. Pick a version within one minor version of your cluster. |
| [Get started with LKE](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-lke-linode-kubernetes-engine) | First cluster. |
| [Manage a cluster with kubectl](https://techdocs.akamai.com/cloud-computing/docs/manage-a-cluster-with-kubectl) | Getting the kubeconfig and running `kubectl`. |
| [Load balancing on LKE](https://techdocs.akamai.com/cloud-computing/docs/get-started-with-load-balancing-on-an-lke-cluster) | How a `LoadBalancer` Service becomes a NodeBalancer. |
| [NodeBalancers](https://techdocs.akamai.com/cloud-computing/docs/nodebalancer) | You want the big picture on load balancers. |

## Valkey (optional module)

| Link | When you need it |
|---|---|
| [Valkey](https://valkey.io) | Commands and data types. |
| [Managed Valkey on Akamai](https://techdocs.akamai.com/cloud-computing/docs/aiven-valkey) | You outgrow the container. Managed Valkey runs on dedicated plans only. |

## Prices

| Link | When you need it |
|---|---|
| [costs.md](costs.md) | The hourly price of everything this kit creates. |
| [Akamai Cloud pricing](https://www.akamai.com/cloud/pricing) | Prices for anything else, by region. |

## Help and going further

| Link | When you need it |
|---|---|
| [Community questions](https://www.linode.com/community/questions/) | Searching for an answer someone already got. At the event, ask the mentors and the event Discord first. |
| [Docker Desktop](https://docs.docker.com/get-started/get-docker/) | Running the agent in a container on your laptop. Optional. |
| [Solution architect agent workshop](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent) | After this kit. Eight modules: tools, MCP, guardrails, memory, diagrams, evals, multi-agent, and deploying to LKE. |
| [Its module 8: deploy to LKE](https://github.com/akamai-developers/akamai-workshop-solution-architect-agent/tree/main/workshop/08_deploy_to_lke) | Moving guide 04 to production: an image in a registry, two replicas. |
| [The inference notebooks](../notebooks/00_quickstart.ipynb) | Learning the brain: chat, embeddings, images, tools, and structured output. |
