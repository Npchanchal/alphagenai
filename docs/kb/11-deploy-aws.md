# 11 — Deploy & AWS

## Local

```bash
docker compose up --build -d
# API :8000 · web :8080 (or Vite :5173 in dev)
curl -sf http://127.0.0.1:8000/health
```

## AWS

- Stack: `deploy/aws/` (ECS Fargate **ARM64 on-demand**, 1 task + ECR + **ALB** + EFS). ~$40/mo — see `docs/AWS_COST.md`.
- `cpu_architecture` in `terraform.tfvars` drives the image platform; the deploy script pushes images before `terraform apply`.
- Scripts: `aws-deploy.sh`, `aws-app-url.sh`, `aws-idle.sh`, `aws-wake.sh`.
- Region default historically `ap-south-1`.
- **Credentials:** run with `AWS_PROFILE=ocotillo` (account 884686184601, see `deploy/aws/OPERATOR_OCOTILLO.md`). The `default` profile's key is invalid (`InvalidClientTokenId`).
- **Static review URL:** ALB DNS via `./scripts/aws-app-url.sh`.
- Package claims audit: `docs/PACKAGE_CLAIMS_GAPS.md`.
- Cost notes: `docs/AWS_COST.md`; procedure: `docs/AWS_DEPLOYMENT.md`.

## CiteAlpha Analyst settings on AWS

| Env | Default | Notes |
|---|---|---|
| `ANALYST_MONITORS` | on | New-filing Monitors after each refresh |
| `ANALYST_LLM` | off | Optional model summary (still verified per sentence) |
| `ANALYST_EVENT_FILINGS` | off | NSE event announcements for the India event Skills. Not wired in `main.tf`; add to the task environment to turn on |
| `PUBLIC_API_RPM` | 60 | Per-key limit on `/api/v1` + `/api/mcp`. Not wired in `main.tf` |
| `RADAR_DIGEST` | — | No effect since 2026-10-17 (digest and webhooks moved to CiteAlpha Analyst); still set by `main.tf` |

Analyst stores (`analyst_*.json`, `analyst_house_style/`, `analyst_uploads/`) live under `INTELLENS_DATA_DIR` on EFS. Team accounts in `protected_users.json` are re-applied on every start and open on India once per `universe.version`.

## Mail (SES)

Product mail uses Amazon SES in `ap-south-1` (`deploy/aws/ses.tf`). The task role calls `ses:SendEmail`. `INTELLENS_MAIL_TRANSPORT=ses` and `SMTP_FROM` are set when the domain is managed and `smtp_host` is empty. An `SMTP_HOST` still wins, for a staging inbox.

Hostinger keeps the apex MX. SES adds three Easy DKIM CNAMEs, an MX and SPF on `ses.citealpha.com`, and `include:amazonses.com` on the apex SPF. `sales@citealpha.com` is covered by the domain. `contact@ocotilloinnovation.com` gets a one-time SES verification message until the account is out of the sandbox. Pilot requests go to `PILOT_REQUEST_TO` (default those two addresses).

At this volume SES is about $0.10 per 1,000 messages. It does not change the ~$40/month stack.

## Rules

- Do not force-push or destroy infra unless explicitly requested.
- After web/API image push, wait for ECS stable before claiming live.
- Verify `/health`, `/api/meta`, and UI asset hash when checking deploys.

## Idle / wake

Use idle/wake scripts to control cost on non-prod; document URL changes if EIP/ALB shifts.
