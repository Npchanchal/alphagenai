#!/usr/bin/env bash
# Deploy CiteAlpha GCI to AWS: Fargate task (API+web), ALB, optional EFS auth + Secrets Manager.
# Local docker-compose remains untouched.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AWS_DIR="$ROOT/deploy/aws"
REGION="${AWS_REGION:-ap-south-1}"
TAG="${IMAGE_TAG:-latest}"

# Load optional secrets from .env into TF_VAR_* (never printed).
_load_tf_env() {
  local envf="$1"
  [[ -f "$envf" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      ""|\#*) continue ;;
    esac
    local key="${line%%=*}"
    local val="${line#*=}"
    val="${val%\"}"
    val="${val#\"}"
    [[ -n "$val" ]] || continue
    case "$key" in
      INTELLENS_FMP_API_KEY|FMP_API_KEY)
        [[ -z "${TF_VAR_fmp_api_key:-}" ]] && export TF_VAR_fmp_api_key="$val"
        ;;
      SSO)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_sso_enabled=true ;; esac
        ;;
      OIDC_CLIENT_ID)
        [[ -z "${TF_VAR_oidc_client_id:-}" ]] && export TF_VAR_oidc_client_id="$val"
        ;;
      OIDC_CLIENT_SECRET)
        [[ -z "${TF_VAR_oidc_client_secret:-}" ]] && export TF_VAR_oidc_client_secret="$val"
        ;;
      OIDC_ISSUER)
        [[ -z "${TF_VAR_oidc_issuer:-}" ]] && export TF_VAR_oidc_issuer="$val"
        ;;
      OIDC_REDIRECT_URI)
        [[ -z "${TF_VAR_oidc_redirect_uri:-}" ]] && export TF_VAR_oidc_redirect_uri="$val"
        ;;
      ALPHAHUNTER_API_URL|FACTS_API_URL)
        [[ -z "${TF_VAR_alphahunter_api_url:-}" ]] && export TF_VAR_alphahunter_api_url="$val"
        ;;
      ALPHAHUNTER_API_KEY|FACTS_API_KEY)
        [[ -z "${TF_VAR_alphahunter_api_key:-}" ]] && export TF_VAR_alphahunter_api_key="$val"
        ;;
      CSM_EMAIL)
        [[ -z "${TF_VAR_csm_email:-}" ]] && export TF_VAR_csm_email="$val"
        ;;
      OPENAI_API_KEY|INTELLENS_LLM_API_KEY)
        [[ -z "${TF_VAR_openai_api_key:-}" ]] && export TF_VAR_openai_api_key="$val"
        ;;
      GEMINI_API_KEY)
        [[ -z "${TF_VAR_gemini_api_key:-}" ]] && export TF_VAR_gemini_api_key="$val"
        ;;
      FORCE_HTTPS)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_force_https=true ;; esac
        ;;
      ENABLE_HSTS)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_enable_hsts=true ;; esac
        ;;
      INTELLENS_PUBLIC_URL)
        [[ -z "${TF_VAR_intellens_public_url:-}" ]] && export TF_VAR_intellens_public_url="$val"
        ;;
      VITE_PLAUSIBLE_DOMAIN|VITE_GA_MEASUREMENT_ID|VITE_GSC_VERIFICATION|VITE_BING_VERIFICATION|VITE_TWITTER_SITE)
        export "$key=$val"
        ;;
      RADAR_DIGEST)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_radar_digest=true ;;
          false|0|no|off) export TF_VAR_radar_digest=false ;;
        esac
        ;;
      IR_MIRROR)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_ir_mirror=true ;;
          false|0|no|off) export TF_VAR_ir_mirror=false ;;
        esac
        ;;
      PORTFOLIO_STRETCH)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_portfolio_stretch=true ;;
          false|0|no|off) export TF_VAR_portfolio_stretch=false ;;
        esac
        ;;
      USE_DB_AUTH)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_use_db_auth=true ;;
          false|0|no|off) export TF_VAR_use_db_auth=false ;;
        esac
        ;;
      AUTH_SQLITE_PATH)
        [[ -z "${TF_VAR_auth_sqlite_path:-}" ]] && export TF_VAR_auth_sqlite_path="$val"
        ;;
      SMTP_HOST)
        # Mailtrap in .env is the local inbox. The AWS task uses SES instead.
        if [[ "${DEPLOY_USE_SES:-}" != "1" && "$val" != *mailtrap* && -z "${TF_VAR_smtp_host:-}" ]]; then
          export TF_VAR_smtp_host="$val"
        fi
        ;;
      SMTP_PORT)
        [[ -z "${TF_VAR_smtp_port:-}" ]] && export TF_VAR_smtp_port="$val"
        ;;
      SMTP_FROM)
        [[ -z "${TF_VAR_smtp_from:-}" ]] && export TF_VAR_smtp_from="$val"
        ;;
      SMTP_USER)
        [[ -z "${TF_VAR_smtp_user:-}" ]] && export TF_VAR_smtp_user="$val"
        ;;
      SMTP_PASS)
        [[ -z "${TF_VAR_smtp_pass:-}" ]] && export TF_VAR_smtp_pass="$val"
        ;;
      INTELLENS_API_KEY)
        [[ -z "${TF_VAR_intellens_api_key:-}" ]] && export TF_VAR_intellens_api_key="$val"
        ;;
      INTELLENS_ABUSE_SECRET)
        [[ -z "${TF_VAR_intellens_abuse_secret:-}" ]] && export TF_VAR_intellens_abuse_secret="$val"
        ;;
      PILOT_REQUEST_TO)
        [[ -z "${TF_VAR_pilot_request_to:-}" ]] && export TF_VAR_pilot_request_to="$val"
        ;;
      INTELLENS_AUTH_DEV_TOKENS)
        v="$(printf '%s' "$val" | tr '[:upper:]' '[:lower:]')"
        case "$v" in true|1|yes|on) export TF_VAR_intellens_auth_dev_tokens=true ;;
          false|0|no|off) export TF_VAR_intellens_auth_dev_tokens=false ;;
        esac
        ;;
    esac
  done < "$envf"
  return 0
}
_load_tf_env "$ROOT/.env"
_load_tf_env "$ROOT/backend/.env"

if [[ -n "${TF_VAR_fmp_api_key:-}" ]]; then
  echo "== FMP key detected (wiring INTELLENS_FMP_API_KEY into ECS task) =="
else
  echo "== No FMP key — market tape stays demo_deterministic =="
fi
if [[ -n "${TF_VAR_gemini_api_key:-}" ]]; then
  echo "== Gemini key detected (LLM extract, embeddings and web search use Gemini) =="
elif [[ -n "${TF_VAR_openai_api_key:-}" ]]; then
  echo "== LLM key detected (wiring OPENAI_API_KEY into ECS task) =="
else
  echo "== No LLM key — extract/embeddings stay local fallback =="
fi
if [[ "${TF_VAR_force_https:-}" == "true" ]]; then
  echo "== FORCE_HTTPS=true (app-level HTTPS redirect + HSTS) =="
fi
if [[ "${TF_VAR_sso_enabled:-}" == "true" ]]; then
  echo "== SSO=true (OIDC env will be wired if CLIENT_ID/ISSUER/REDIRECT set) =="
fi
if [[ -n "${TF_VAR_alphahunter_api_url:-}" ]]; then
  echo "== AlphaHunter live URL detected =="
fi
if [[ "${TF_VAR_radar_digest:-}" == "true" ]]; then
  echo "== RADAR_DIGEST=1 (no effect: digests and webhooks moved to CiteAlpha Analyst) =="
fi
if [[ "${TF_VAR_ir_mirror:-}" == "true" ]]; then
  echo "== IR_MIRROR=1 (IR Mirror ledger) =="
fi
if [[ "${TF_VAR_portfolio_stretch:-}" == "false" ]]; then
  echo "== PORTFOLIO_STRETCH=0 (NCI/workbench off) =="
elif [[ "${TF_VAR_portfolio_stretch:-}" == "true" ]]; then
  echo "== PORTFOLIO_STRETCH=1 =="
fi
if [[ "${TF_VAR_use_db_auth:-true}" == "true" ]]; then
  echo "== USE_DB_AUTH=1 (SQLite on EFS at ${TF_VAR_auth_sqlite_path:-/data/auth.db}) =="
fi
if [[ -n "${TF_VAR_smtp_host:-}" ]]; then
  echo "== SMTP configured (${TF_VAR_smtp_host}:${TF_VAR_smtp_port:-587}) =="
elif [[ "${DEPLOY_USE_SES:-}" == "1" || "${TF_VAR_smtp_host:-}" == "" ]]; then
  echo "== SES mail — Mailtrap in .env is not copied onto the task =="
else
  echo "== No SMTP — verify/reset mail stays stubbed =="
fi
if [[ -n "${TF_VAR_intellens_api_key:-}" ]]; then
  echo "== INTELLENS_API_KEY set (admin attest / ops) =="
else
  echo "== WARN: INTELLENS_API_KEY unset — run scripts/production-go-live.sh setup =="
fi

echo "== AWS identity =="
aws sts get-caller-identity --region "$REGION"

echo "== Terraform init =="
cd "$AWS_DIR"
terraform init -input=false

# Images are pushed before apply so the task definition never references an
# architecture (cpu_architecture) whose image is not in ECR yet.
ECR_API="$(terraform output -raw ecr_api_url)"
ECR_WEB="$(terraform output -raw ecr_web_url)"
ACCOUNT_ID="$(terraform output -raw account_id)"
CLUSTER="$(terraform output -raw ecs_cluster_name)"
SERVICE="$(terraform output -raw ecs_service_name)"

# Isolated Docker config: the Desktop credential helper can block on a hidden
# macOS Keychain prompt. Set DEPLOY_USE_HOST_DOCKER_CONFIG=1 to opt out.
if [[ "${DEPLOY_USE_HOST_DOCKER_CONFIG:-0}" != "1" ]]; then
  HOST_DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}"
  DEPLOY_DOCKER_CONFIG="$(mktemp -d)"
  trap 'rm -rf "$DEPLOY_DOCKER_CONFIG"' EXIT
  echo '{}' > "$DEPLOY_DOCKER_CONFIG/config.json"
  [[ -d "$HOST_DOCKER_CONFIG/cli-plugins" ]] && ln -s "$HOST_DOCKER_CONFIG/cli-plugins" "$DEPLOY_DOCKER_CONFIG/cli-plugins"
  if [[ -z "${DOCKER_HOST:-}" && -S "$HOME/.docker/run/docker.sock" ]]; then
    export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
  fi
  export DOCKER_CONFIG="$DEPLOY_DOCKER_CONFIG"
fi

echo "== ECR login =="
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Must match cpu_architecture in terraform.tfvars (ARM64 = Graviton, cheaper; X86_64 default).
CPU_ARCH="$(sed -nE 's/^[[:space:]]*cpu_architecture[[:space:]]*=[[:space:]]*"([A-Z0-9_]+)".*/\1/p' "$AWS_DIR/terraform.tfvars" 2>/dev/null | head -1)"
case "${CPU_ARCH:-X86_64}" in
  ARM64) DOCKER_PLATFORM=linux/arm64 ;;
  *) DOCKER_PLATFORM=linux/amd64 ;;
esac
echo "== Image platform: ${DOCKER_PLATFORM} =="
BUILD_OPTS=(--platform "$DOCKER_PLATFORM" --provenance=false --sbom=false)

echo "== Build & push API image =="
docker build "${BUILD_OPTS[@]}" -t "${ECR_API}:${TAG}" "$ROOT/backend"
docker push "${ECR_API}:${TAG}"

echo "== Build & push Web image (nginx -> localhost:8000) =="
WEB_BUILD_ARGS=()
[[ -n "${VITE_PLAUSIBLE_DOMAIN:-}" ]] && WEB_BUILD_ARGS+=(--build-arg "VITE_PLAUSIBLE_DOMAIN=${VITE_PLAUSIBLE_DOMAIN}")
[[ -n "${VITE_GA_MEASUREMENT_ID:-}" ]] && WEB_BUILD_ARGS+=(--build-arg "VITE_GA_MEASUREMENT_ID=${VITE_GA_MEASUREMENT_ID}")
[[ -n "${VITE_GSC_VERIFICATION:-}" ]] && WEB_BUILD_ARGS+=(--build-arg "VITE_GSC_VERIFICATION=${VITE_GSC_VERIFICATION}")
[[ -n "${VITE_BING_VERIFICATION:-}" ]] && WEB_BUILD_ARGS+=(--build-arg "VITE_BING_VERIFICATION=${VITE_BING_VERIFICATION}")
[[ -n "${VITE_TWITTER_SITE:-}" ]] && WEB_BUILD_ARGS+=(--build-arg "VITE_TWITTER_SITE=${VITE_TWITTER_SITE}")
docker build "${BUILD_OPTS[@]}" "${WEB_BUILD_ARGS[@]}" -f "$ROOT/frontend/Dockerfile.aws" -t "${ECR_WEB}:${TAG}" "$ROOT/frontend"
docker push "${ECR_WEB}:${TAG}"

echo "== Terraform apply (ECS task env — skip ACM wait) =="
cd "$AWS_DIR"
# production.overlay.tfvars wins over terraform.tfvars for the keys it sets
# (on-demand Fargate, index bucket). Auto-loaded terraform.tfvars still supplies VPC and secrets.
TF_VAR_FILES=(-var-file=production.overlay.tfvars)
# Full apply can block 10m+ on ACM DNS validation until Hostinger NS cutover.
# Default deploy only refreshes the task definition (and service when safe).
if [[ "${TF_FULL_APPLY:-}" == "1" ]]; then
  terraform apply -input=false -auto-approve "${TF_VAR_FILES[@]}"
else
  # Task def + service + persistent auth EFS + secrets + alarms when enabled
  TF_TARGETS=(
    -target=aws_security_group.ecs
    -target=aws_lb_listener.http
    -target=aws_security_group.efs
    -target=aws_efs_file_system.auth
    -target=aws_efs_mount_target.auth
    -target=aws_efs_access_point.auth
    -target=aws_iam_role_policy.ecs_task_efs
    -target=aws_secretsmanager_secret.app
    -target=aws_secretsmanager_secret_version.app
    -target=aws_iam_role_policy.ecs_execution_secrets
    -target=aws_sns_topic.alarms
    -target=aws_sns_topic_subscription.alarms_email
    -target=aws_cloudwatch_metric_alarm.alb_5xx
    -target=aws_cloudwatch_metric_alarm.alb_unhealthy_hosts
    -target=aws_cloudwatch_metric_alarm.ecs_cpu_high
    -target=aws_iam_role.backup
    -target=aws_iam_role_policy_attachment.backup
    -target=aws_backup_vault.auth
    -target=aws_backup_plan.auth_efs
    -target=aws_backup_selection.auth_efs
    -target=aws_ecs_cluster_capacity_providers.main
    -target=aws_s3_bucket.index
    -target=aws_s3_bucket_versioning.index
    -target=aws_s3_bucket_server_side_encryption_configuration.index
    -target=aws_s3_bucket_public_access_block.index
    -target=aws_iam_role_policy.ecs_task_index_s3
    -target=aws_ecs_task_definition.app
    -target=aws_ecs_service.app
  )
  terraform apply -input=false -auto-approve "${TF_VAR_FILES[@]}" "${TF_TARGETS[@]}"
  echo "== Tip: TF_FULL_APPLY=1 for ALB/HTTPS/ACM; needs Route53 NS live =="
fi


echo "== Force ECS redeploy =="
aws ecs update-service --region "$REGION" --cluster "$CLUSTER" \
  --service "$SERVICE" --force-new-deployment >/dev/null

echo "== Waiting for ECS rollout =="
for i in $(seq 1 60); do
  read -r RUNNING ROLLOUT <<<"$(aws ecs describe-services --region "$REGION" --cluster "$CLUSTER" \
    --services "$SERVICE" \
    --query 'services[0].deployments[?status==`PRIMARY`].[runningCount,rolloutState] | [0]' \
    --output text 2>/dev/null || echo "0 IN_PROGRESS")"
  if [[ "${RUNNING:-0}" -ge 1 && "${ROLLOUT:-}" == "COMPLETED" ]]; then
    echo "ECS steady after ~$((i * 5))s"
    break
  fi
  sleep 5
  if [[ "$i" -eq 60 ]]; then
    echo "Timed out waiting for ECS rollout — continuing health check anyway"
  fi
done

echo "== Waiting for ALB /health =="
APP_URL="$(cd "$AWS_DIR" && terraform output -raw app_url 2>/dev/null || true)"
if [[ -z "$APP_URL" || "$APP_URL" != https://* ]]; then
  APP_URL="https://$(cd "$AWS_DIR" && terraform output -raw alb_dns_name)"
fi
for i in $(seq 1 60); do
  if curl -sf "${APP_URL}/health" >/dev/null 2>&1; then
    echo "Healthy after ~$((i * 5))s via ${APP_URL}"
    break
  fi
  sleep 5
  if [[ "$i" -eq 60 ]]; then
    echo "Timed out waiting for ${APP_URL}/health — try task IP via aws-app-url fallback"
    exit 1
  fi
done

echo ""
echo "AWS deployment ready"
echo "  App:      ${APP_URL}"
echo "  Package:  ${APP_URL}/package"
echo "  Health:   ${APP_URL}/health"
echo "  API docs: ${APP_URL}/docs"
echo "  Meta:     ${APP_URL}/api/meta"
curl -sf "${APP_URL}/api/meta" | python3 -m json.tool | head -20

if [[ -n "${BOOTSTRAP_SUPER_EMAIL:-}" && -n "${BOOTSTRAP_SUPER_PASSWORD:-}" ]]; then
  echo "== Bootstrap platform super user =="
  python3 "$ROOT/scripts/bootstrap-super-user.py" --api "$APP_URL"
fi

if [[ -n "${TF_VAR_intellens_api_key:-}" ]]; then
  echo "== Apply SQL auth schema on production =="
  curl -sf -X POST "${APP_URL}/api/infra/db/migrate" \
    -H "X-API-Key: ${TF_VAR_intellens_api_key}" >/dev/null \
    && echo "SQL auth schema applied" \
    || echo "WARN: db/migrate failed — check admin key and USE_DB_AUTH on task"
fi
