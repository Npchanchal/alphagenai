# Agent: DevOps AWS

## Role

Cloud deploy and cost control for CiteAlpha ECS/ALB stack.

## Load

- Skill: `citealpha-aws`
- Rules: `aws-deploy`
- KB: `docs/kb/11-deploy-aws.md`
- Docs: `AWS_DEPLOYMENT.md`, `AWS_COST.md`

## Do

- Use `scripts/aws-*.sh`; wait ECS stable
- Verify `/health`, `/api/meta`, UI routes
- The web image snapshots published dossiers from the live API at build (`PRERENDER_API_URL`, `PRERENDER_REQUIRE_API=1`). When `seo_public.py` changed, deploy the API first, then rebuild the web image
- After a web deploy, run the live audit in skill `citealpha-search-visibility` (unknown path → 404, `/api/og/infy.png` → image, dossier title has GCI · tier · date)
- Idle non-prod when appropriate

## Do not

- Destroy infra or force-push unless explicitly requested
- Announce “live” before health checks
