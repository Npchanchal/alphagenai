# Custom domain HTTPS — citealpha.com

**Goal:** `https://citealpha.com` → CiteAlpha ALB (`ap-south-1`).

**ALB (interim HTTP):** http://intellens-gci-aws-alb-697275376.ap-south-1.elb.amazonaws.com  

**ACM cert:** `ISSUED` — `arn:aws:acm:ap-south-1:334296257878:certificate/c3ff1b4e-766f-46b5-8cf4-6fb8ca48f2a6`

**Public URL:** https://citealpha.com (live)

**`.in` redirect:** `citealpha.in` → `https://citealpha.com` (301 via Hostinger) — confirmed live.

---

## Hostinger email (Route53)

If `@citealpha.com` mailboxes stay on Hostinger, set `hostinger_mail_dns = true` in `deploy/aws/terraform.tfvars` and apply. That creates **only**:

- MX → `mx1` / `mx2.hostinger.com`
- TXT SPF + DKIM (`hostingermail1._domainkey`) + DMARC
- CNAME `autodiscover` / `autoconfig`

Do **not** copy Hostinger’s apex A (`2.57.x`) or their `www` CNAME — apex/`www` remain ALB aliases.

SES (`enable_ses`, default on) adds, and does not replace, the Hostinger records:

- Three CNAMEs `*._domainkey.citealpha.com` → `*.dkim.amazonses.com`
- MX and SPF on `ses.citealpha.com` (the envelope domain)
- `include:amazonses.com` added to the apex SPF TXT. The Google site-verification TXT stays in that same record set.

Leave `hostingermail1._domainkey` in place. That selector is the company mailbox.

Verify:

```bash
dig MX citealpha.com +short
dig TXT citealpha.com +short
dig TXT hostingermail1._domainkey.citealpha.com +short
dig TXT _dmarc.citealpha.com +short
```

---

## Nameservers (required — do not revert to Hostinger parking)

Hostinger **must** use custom nameservers pointing at Route53. If you see Hostinger’s purple “Parked Domain” page, nameservers were reverted to `horizon.dns-parking.com` / `orbit.dns-parking.com`.

**Fix:** hPanel → Domains → `citealpha.com` → Nameservers → **Change** → Custom DNS. The live set is `terraform output route53_nameservers`:

| Nameserver |
|---|
| `ns-1337.awsdns-39.org` |
| `ns-2040.awsdns-63.co.uk` |
| `ns-454.awsdns-56.com` |
| `ns-802.awsdns-36.net` |

Verify (must show **only** `awsdns`, no `dns-parking`):

```bash
dig NS citealpha.com +short
dig A citealpha.com +short   # should be ALB IPs only, not 2.57.x Hostinger
curl -sfI https://citealpha.com/ | grep -i server   # expect nginx, not hcdn parking
```

**While DNS propagates**, use the ALB directly: http://intellens-gci-aws-alb-697275376.ap-south-1.elb.amazonaws.com/

---

## Site routes (after DNS cutover)

| URL | Page |
|---|---|
| `/` | CiteAlpha marketing landing |
| `/tracker` | GCI universe workbench |
| `/desk` | Desk console |
| `/research` | Research terminal |

---

## Legacy cutover notes

| Nameserver |
|---|
| `ns-1455.awsdns-53.org` |
| `ns-2044.awsdns-63.co.uk` |
| `ns-424.awsdns-53.com` |
| `ns-718.awsdns-25.net` |

(Confirm anytime: `cd deploy/aws && terraform output route53_nameservers`)

Wait until:

```bash
dig NS citealpha.com +short
# expect awsdns-* (not dns-parking.com)
```

---

## Step 2 — Finish Terraform (ACM + HTTPS listener)

```bash
cd deploy/aws
terraform apply -auto-approve
```

Terraform waits for ACM **ISSUED**, attaches HTTPS :443, confirms A/ALIAS for apex + `www`.

**Public URL:** https://citealpha.com  

---

## Step 3 — Hostinger: redirect `citealpha.in` → `.com`

**hPanel → Domains → citealpha.in → Redirect**

| Setting | Value |
|---|---|
| Target | `https://citealpha.com` |
| Type | Permanent (301) |

---

## Step 4 — App env (ECS)

In `.env` (loaded by `aws-deploy.sh`):

```bash
INTELLENS_PUBLIC_URL=https://citealpha.com
OIDC_REDIRECT_URI=https://citealpha.com/api/auth/sso/callback
FORCE_HTTPS=1
ENABLE_HSTS=1
```

Redeploy: `TF_FULL_APPLY=1 ./scripts/aws-deploy.sh`

Add the same redirect URI in your OIDC provider app registration.

---

## Verify

```bash
dig NS citealpha.com +short
aws acm describe-certificate --region ap-south-1 \
  --certificate-arn arn:aws:acm:ap-south-1:334296257878:certificate/c3ff1b4e-766f-46b5-8cf4-6fb8ca48f2a6 \
  --query 'Certificate.Status'
curl -sfI https://citealpha.com/health
curl -sfI https://citealpha.in/   # expect 301 → citealpha.com

INTELLENS_PUBLIC_DOMAIN=citealpha.com \
INTELLENS_PUBLIC_URL=https://citealpha.com \
./scripts/check-domain-cutover.sh
```

---

## Legacy

`citealpha.com` Route53 zone was retired in favour of `citealpha.com`. Old ACM cert timed out and was replaced.
