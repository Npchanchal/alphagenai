# AWS cost profile — CiteAlpha GCI (`deploy/aws`)

Audited 2026-09-28 (account `884686184601`, ap-south-1). Cost Explorer is not enabled for the
`ocotillo` IAM user, so figures are list-price estimates from the live inventory (730 h/month).

## Live footprint

| Resource | Config | ~USD/mo |
|---|---|---|
| ECS Fargate ×1 (API + nginx) | **ARM64 (Graviton)**, 0.5 vCPU / 1 GB, on-demand | **10.60** |
| ALB | HTTPS (ACM) + HTTP→HTTPS redirect; ~0.0001 LCU avg | 17.45 |
| Public IPv4 | 2 ALB + 1 task ENI @ $0.005/h | 10.95 |
| Route 53 zone `citealpha.com` | 12 records | 0.50 |
| Secrets Manager | 1 secret | 0.40 |
| CloudWatch | 3 alarms, logs 7-day retention (~20 MB) | ~0.35 |
| EFS (`auth.db`) + AWS Backup | ~100 KB, 8 recovery points | <0.10 |
| ECR ×2 | lifecycle keep 3 (~0.3 GB) | ~0.03 |
| SES | Product mail, $0.10 / 1,000 messages | <0.10 |
| **Total** | | **~$40** |

No NAT gateway, EC2, EBS, snapshots, VPC endpoints or Container Insights; nothing in other regions.

Network: the task security group accepts port 80 **only from the ALB** (the task public IP exists
for image pulls/egress, not ingress). ALB port 80 returns 301 → HTTPS.

Before 2026-09-28 the task ran on x86 on-demand (~$18.90/mo, total ~$49). ARM64 Fargate in
ap-south-1 is $0.02383/vCPU-h + $0.00261/GB-h vs $0.04256 + $0.004655 for x86 (−44%).

## Utilisation (7 days)

- Memory: max 15% of 1 GB (~150 MB). CPU: avg 2.8%, spikes to ~88% (startup / scoring).
- ALB: 1.5k–15k requests/day — load-based charges are effectively zero.

## Further options (not applied — trade-offs)

| Option | Saves ~/mo | Trade-off |
|---|---|---|
| 0.25 vCPU / 1 GB ARM64 | ~4.35 | Halves CPU headroom; slower cold start and scoring spikes |
| x86 Fargate Spot instead of ARM on-demand | ~5 | Single task: Spot reclaim = minutes of downtime. Spot is x86-only |
| Drop ALB (+2 IPv4) | ~25 | Needs another HTTPS front; Lightsail/App Runner lack EFS (SQLite auth) |
| Compute Savings Plan (1 yr) | ~2 | Commitment for a ~$10 line item |

## Knobs (`terraform.tfvars`)

- `cpu_architecture = "ARM64"` — `scripts/aws-deploy.sh` builds images for the matching platform
  and pushes them **before** `terraform apply`, so the task definition never points at a missing arch.
- `app_cpu` / `app_memory`, `fargate_on_demand_base`, `fargate_spot_weight` (x86 only).

## Ops

```bash
./scripts/aws-deploy.sh
./scripts/aws-idle.sh      # non-prod only: Fargate → 0; ALB + IPv4 still bill (~$25)
./scripts/aws-wake.sh
```
