variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "intellens-gci"
}

variable "environment" {
  type    = string
  default = "aws"
}

variable "vpc_id" {
  type        = string
  description = "VPC for ECS (default VPC recommended for first deploy)"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Public subnet(s); first is used for the single Fargate task (no ALB)"
}

variable "app_cpu" {
  type        = number
  default     = 512
  description = "Combined task CPU (api+web). 512 = 0.5 vCPU"
}

variable "app_memory" {
  type        = number
  default     = 1024
  description = "Combined task memory (MiB)"
}

variable "app_desired_count" {
  type    = number
  default = 1
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "use_fargate_spot" {
  type        = bool
  default     = true
  description = "Use Fargate Spot (~50–70% cheaper compute; OK for demo/pilot)"
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "fmp_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Financial Modeling Prep key for EOD tape (not GCI). Empty = demo history."
}

variable "sso_enabled" {
  type        = bool
  default     = false
  description = "Set SSO=true on the API task for OIDC login"
}

variable "oidc_client_id" {
  type      = string
  default   = ""
  sensitive = true
}

variable "oidc_client_secret" {
  type      = string
  default   = ""
  sensitive = true
}

variable "oidc_issuer" {
  type    = string
  default = ""
}

variable "oidc_redirect_uri" {
  type        = string
  default     = ""
  description = "Must match IdP app registration (usually https://host/api/auth/sso/callback)"
}

variable "openai_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional OpenAI (or compatible) key for LLM extract + embeddings. Empty = heuristic/TF-IDF."
}

variable "gemini_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Gemini key. When set, LLM extract, embeddings and web-search discovery use Gemini instead of OpenAI."
}

variable "gemini_chat_model" {
  type        = string
  default     = "gemini-3.8-flash"
  description = "Gemini model for extract and web-search discovery."
}

variable "gemini_embed_model" {
  type        = string
  default     = "gemini-embedding-001"
  description = "Gemini embedding model for Research ranking."
}

variable "force_https" {
  type        = bool
  default     = false
  description = "Set FORCE_HTTPS=true on the API task (app-level redirect + HSTS with enable_hsts)"
}

variable "enable_hsts" {
  type        = bool
  default     = false
  description = "Set ENABLE_HSTS=true on the API task"
}

variable "intellens_public_url" {
  type        = string
  default     = ""
  description = "Public site URL (e.g. https://citealpha.com) for absolute links / OIDC hints"
}

variable "alphahunter_api_url" {
  type        = string
  default     = ""
  description = "Live facts vendor URL (ALPHAHUNTER_API_URL)"
}

variable "alphahunter_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "csm_email" {
  type    = string
  default = ""
}

variable "radar_digest" {
  type        = bool
  default     = false
  description = "Set RADAR_DIGEST=1 on the API task (email/webhook digests)"
}

variable "ir_mirror" {
  type        = bool
  default     = false
  description = "Set IR_MIRROR=1 on the API task (corporate IR Mirror ledger)"
}

variable "portfolio_stretch" {
  type        = bool
  default     = true
  description = "Set PORTFOLIO_STRETCH on the API task (NCI + workbench; default on)"
}

variable "enable_eip" {
  type        = bool
  default     = false
  description = "Allocate EIP (usually unused — Fargate ENI AssociateAddress is blocked)"
}

variable "acm_certificate_arn" {
  type        = string
  default     = ""
  description = "Optional ACM cert ARN in ap-south-1 for HTTPS :443 on the ALB"
}

variable "https_redirect" {
  type        = bool
  default     = true
  description = "When ACM is set, redirect HTTP→HTTPS"
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "Optional apex domain for HTTPS (e.g. ocotilloinnovation.in). Empty = ALB DNS only."
}

variable "manage_dns" {
  type        = bool
  default     = true
  description = "When domain_name is set, create Route53 zone + ACM validation + A/ALIAS records"
}

variable "hostinger_mail_dns" {
  type        = bool
  default     = false
  description = "When true (and manage_dns), create Hostinger MX/SPF/DKIM/DMARC + autodiscover/autoconfig in Route53"
}

variable "use_db_auth" {
  type        = bool
  default     = true
  description = "Set USE_DB_AUTH=1 on the API task (SQLite or Postgres persistence)"
}

variable "auth_sqlite_path" {
  type        = string
  default     = "/data/auth.db"
  description = "SQLite auth DB path when USE_DB_AUTH=1 and Postgres is not configured"
}

variable "enable_auth_efs" {
  type        = bool
  default     = true
  description = "Mount EFS at /data so auth.db survives ECS redeploys"
}

variable "smtp_host" {
  type        = string
  default     = ""
  description = "SMTP_HOST for verify/reset/invite mail (empty = stubbed)"
}

variable "smtp_port" {
  type        = string
  default     = "587"
  description = "SMTP_PORT (587 or 2525 for Mailtrap)"
}

variable "smtp_from" {
  type        = string
  default     = ""
  description = "SMTP_FROM — e.g. CiteAlpha <no-reply@citealpha.com>"
}

variable "smtp_user" {
  type        = string
  default     = ""
  sensitive   = true
  description = "SMTP_USER"
}

variable "smtp_pass" {
  type        = string
  default     = ""
  sensitive   = true
  description = "SMTP_PASS"
}

variable "intellens_auth_dev_tokens" {
  type        = bool
  default     = false
  description = "Expose one-time tokens in API when SMTP unset (never true in prod)"
}

variable "use_secrets_manager" {
  type        = bool
  default     = true
  description = "Store vendor keys in Secrets Manager instead of plaintext ECS environment"
}

variable "enable_cloudwatch_alarms" {
  type        = bool
  default     = true
  description = "Create ALB/ECS CloudWatch alarms (SNS email when alarm_email set)"
}

variable "alarm_email" {
  type        = string
  default     = ""
  description = "Optional email for CloudWatch alarm SNS subscription"
}

variable "enable_efs_backup" {
  type        = bool
  default     = true
  description = "Daily AWS Backup plan for auth EFS volume"
}

variable "efs_backup_retention_days" {
  type        = number
  default     = 14
  description = "Retain EFS backups for N days"
}

variable "fargate_on_demand_base" {
  type        = number
  default     = 1
  description = "On-demand Fargate tasks to keep running (0 = Spot-only; 1 = one stable task)"
}

variable "fargate_spot_weight" {
  type        = number
  default     = 0
  description = "Fargate Spot weight when on_demand_base >= 1 (0 = on-demand only)"
}

variable "cpu_architecture" {
  type        = string
  default     = "X86_64"
  description = "Task CPU architecture. ARM64 (Graviton) is ~44% cheaper in ap-south-1 but cannot use Fargate Spot."

  validation {
    condition     = contains(["X86_64", "ARM64"], var.cpu_architecture)
    error_message = "cpu_architecture must be X86_64 or ARM64."
  }
}

variable "intellens_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Production admin API key (INTELLENS_API_KEY) — not intellens-demo"
}

variable "intellens_abuse_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "HMAC secret for abuse challenge (INTELLENS_ABUSE_SECRET)"
}

variable "pilot_request_to" {
  type        = string
  default     = "sales@citealpha.com,contact@ocotilloinnovation.com"
  description = "Comma-separated inboxes for a new pilot request (PILOT_REQUEST_TO)"
}

variable "enable_ses" {
  type        = bool
  default     = true
  description = "Verify the site domain in SES and let the task send mail. Hostinger MX is unchanged."
}

variable "enable_index_bucket" {
  type        = bool
  default     = false
  description = "S3 bucket for frozen GCI CSV/Parquet (W9.2). Off until the production overlay is applied."
}

variable "ledger_digest_to" {
  type        = string
  default     = ""
  description = "Comma-separated licensee emails for the weekly ledger digest (INTELLENS_LEDGER_DIGEST_TO)"
}
