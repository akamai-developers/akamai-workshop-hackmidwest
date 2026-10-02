# Costs and cleanup

[Workshop home](../README.md) · [Setup](00_prework.md)

Cloud labs create billable resources. Check the selected region, plan, account promotion, and current price before creation. Powering off a resource does not necessarily stop billing.

## What each path creates

| Path | Resources to track |
|---|---|
| Inference notebooks only | Uses the shared service's team quota; creates no resources in your cloud account |
| Object Storage lab | Bucket, application access key, and possibly a CLI-generated key |
| PostgreSQL lab | One Managed PostgreSQL instance |
| `scripts/up.sh --no-db` | Bucket and application access key |
| `scripts/up.sh` | Bucket, access key, and Managed PostgreSQL |
| Linode deployment | Linode, Cloud Firewall, app and Valkey containers on that VM |
| LKE deployment | Cluster, worker node, NodeBalancer, app and Valkey pods |

A Valkey container has no separate managed-service charge but uses your compute resources. Running both deployment paths leaves both the standalone Linode and the LKE resources active.

## Check current prices

Use [Akamai Cloud pricing](https://www.akamai.com/cloud/pricing), Cloud Manager, and the CLI:

```bash
linode-cli linodes types
linode-cli databases type-view g6-nanode-1
linode-cli object-storage types
linode-cli nodebalancers types
linode-cli lke types
```

The supplied scripts use `g6-standard-1` for compute and `g6-nanode-1` for PostgreSQL. Prices depend on service and region. Include storage and transfer overages, load balancers, extra nodes, and any add-ons in your estimate. Check the remaining promotional credit and its expiry under **Administration > Billing**.

## Review before deleting

Export any data you want to retain. From the workshop directory:

```bash
bash scripts/down.sh
```

The script shows candidate resources and requires `yes` before deleting them. Read every name and ID. It selects resources using fixed workshop labels, the bucket and key in `.env`, and, when needed, the LKE Service address. Names are not proof of ownership: an existing resource with a matching name can be selected.

It may select the workshop Linode, firewall, database, cluster, NodeBalancer, bucket, and application access key. Do not confirm if another project uses them. Use Cloud Manager for selective removal instead. The script does not cancel the account-wide Object Storage service.

## Confirm the result

- Check **Linodes**, **Kubernetes**, **NodeBalancers**, **Databases**, **Firewalls**, and **Object Storage** in Cloud Manager.
- Inspect any volumes or resources you created outside the workshop scripts.
- Revoke unused API tokens and Object Storage keys, including CLI-generated keys.
- Remove retired compute addresses from any database allow list you retain.
- Check Billing for remaining services and charges.

Deleting a bucket does not cancel Object Storage service billing. To cancel the service, follow [Cancel Object Storage](https://techdocs.akamai.com/cloud-computing/docs/cancel-object-storage). Cancellation deletes every bucket and object in the account, including data outside this workshop. Only cancel when none of that data is needed.

References: [How billing works](https://techdocs.akamai.com/cloud-computing/docs/understanding-how-billing-works), [Object Storage pricing](https://techdocs.akamai.com/cloud-computing/docs/object-storage-pricing), [Stop further billing](https://techdocs.akamai.com/cloud-computing/docs/stop-further-billing).
