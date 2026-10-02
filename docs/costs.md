# Costs

Every resource this kit creates, with its price in Seattle (`us-sea`). Prices were read from the public API with `linode-cli` on 2026-10-02. Run the command in the last column to check them yourself.

Akamai bills each resource by the hour, up to a monthly cap. In the words of the billing docs: "Charges accrue for any service present on an account, even if it's powered off or otherwise not actively being used." A stopped Linode still costs money. Delete what you are done with.

## What each resource costs

| Resource | Created in | Plan | Per hour | Monthly cap | Check it with |
|---|---|---|---|---|---|
| Managed PostgreSQL `hackmidwest-db` | Guide 01, step 1 | `g6-nanode-1`, 1 node | $0.024 | $16 | `linode-cli databases type-view g6-nanode-1` |
| Object Storage, which holds the bucket `hackmidwest-<id>` | Guide 01 | Flat fee per account | $0.0075 | $5 | `linode-cli object-storage types` |
| Object Storage access key `hackmidwest-key` | Guide 01 | | free | free | |
| Linode `hackmidwest-agent` | Guide 03 | `g6-standard-1`: 1 CPU, 2 GB | $0.018 | $12 | `linode-cli linodes types` |
| Cloud Firewall `hackmidwest-fw` | Guide 03 | | free | free | [Cloud Firewall docs](https://techdocs.akamai.com/cloud-computing/docs/cloud-firewall): "available at no charge across all regions" |
| Valkey | Guide 03 | A container on the Linode | free | free | |
| LKE cluster `hackmidwest-lke`, control plane | Guide 04 (optional) | Standard (`lke-sa`) | $0.00 | $0 | `linode-cli lke types` |
| LKE worker node | Guide 04 (optional) | `g6-standard-1` | $0.018 | $12 | `linode-cli linodes types` |
| NodeBalancer for the LoadBalancer Service | Guide 04 (optional) | Basic | $0.015 | $10 | `linode-cli nodebalancers types` |

The Linode includes 2 TB of outbound transfer a month and Object Storage includes 1 TB, both shown as `transfer` in the commands above. Object Storage beyond the flat fee costs $0.02 per GB (`objectstorage-overage`). The kit stores a few kilobytes.

## Totals

| What is running | Per hour | Per day | Monthly cap |
|---|---|---|---|
| Guided path: database, bucket, Linode, firewall | $0.0495 | $1.19 | $33 |
| 30-minute path: bucket, Linode, firewall, no database | $0.0255 | $0.61 | $17 |
| The optional LKE module on top | +$0.033 | +$0.79 | +$22 |

## What the $300 credit covers

At $1.19 a day, the guided stack uses about $3 of credit over a hackathon weekend. Cloud Manager shows your credit and when it expires under **Administration > Billing**.

Two charges outlive a normal teardown:

- **Object Storage** bills $5 a month for the account until you cancel it. Deleting the bucket does not stop it. Cancelling deletes every bucket on the account, so `scripts/down.sh` never does it for you. Follow [Cancel Object Storage](https://techdocs.akamai.com/cloud-computing/docs/cancel-object-storage) when you are sure.
- **Anything you created outside the kit.** `scripts/down.sh` only deletes resources whose label starts with `hackmidwest-`.

## Stop the charges

Each guide ends with a Clean up section that deletes what that guide created. `scripts/down.sh` deletes everything labeled `hackmidwest-*` after asking you to confirm:

```bash
bash scripts/down.sh
```
