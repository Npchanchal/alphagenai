locals {
  name_prefix = "${var.project_name}-${var.environment}"
  # Task can live in one public subnet; ALB needs ≥2 AZs.
  app_subnets = slice(var.subnet_ids, 0, 1)
  alb_subnets = slice(var.subnet_ids, 0, min(2, length(var.subnet_ids)))

  domain_enabled = var.domain_name != ""
  # Explicit ACM ARN enables HTTPS immediately. Managed cert waits on validation
  # but must NOT appear in locals used by ECS — otherwise every apply blocks on DNS.
  effective_cert_arn = var.acm_certificate_arn != "" ? var.acm_certificate_arn : ""
  https_on           = local.effective_cert_arn != ""
  managed_https_on   = local.domain_enabled && var.manage_dns
}

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "api" {
  name                 = "${local.name_prefix}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_ecr_repository" "web" {
  name                 = "${local.name_prefix}-web"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "web" {
  repository = aws_ecr_repository.web.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name_prefix}-web"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = 0
  }
}

# Reserved for future Cloudflare / EC2 jump; Fargate ENI AssociateAddress is blocked.
resource "aws_eip" "app" {
  count  = var.enable_eip ? 1 : 0
  domain = "vpc"
  tags = {
    Name = "${local.name_prefix}-app"
  }
}

# Stable review hostname (ALB DNS does not change on redeploy).
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "Public HTTP to review ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Public HTTP to the combined Fargate task (ALB + optional direct IP).
resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs"
  description = "Public HTTP to combined API+web Fargate task"
  vpc_id      = var.vpc_id

  # ALB only: direct task-IP access would bypass HTTPS and per-client rate limits.
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb" "app" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = local.alb_subnets

  tags = {
    Name = "${local.name_prefix}-alb"
  }
}

resource "aws_lb_target_group" "app" {
  name        = "${local.name_prefix}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = (local.https_on || local.managed_https_on) && var.https_redirect ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = (local.https_on || local.managed_https_on) && var.https_redirect ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.app.arn
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = local.https_on ? 1 : 0
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = local.effective_cert_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# HTTPS after ACM DNS validation (does not gate ECS task updates).
resource "aws_lb_listener" "https_managed" {
  count             = local.managed_https_on && !local.https_on ? 1 : 0
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.app[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Canonical host: www → apex (SEO). Applies when HTTPS listener exists.
resource "aws_lb_listener_rule" "www_to_apex_https" {
  count        = local.https_on && local.domain_enabled ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 1

  action {
    type = "redirect"
    redirect {
      host        = var.domain_name
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
      path        = "/#{path}"
      query       = "#{query}"
    }
  }

  condition {
    host_header {
      values = ["www.${var.domain_name}"]
    }
  }
}

resource "aws_lb_listener_rule" "www_to_apex_https_managed" {
  count        = local.managed_https_on && !local.https_on && local.domain_enabled ? 1 : 0
  listener_arn = aws_lb_listener.https_managed[0].arn
  priority     = 1

  action {
    type = "redirect"
    redirect {
      host        = var.domain_name
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
      path        = "/#{path}"
      query       = "#{query}"
    }
  }

  condition {
    host_header {
      values = ["www.${var.domain_name}"]
    }
  }
}

# --- Optional custom domain HTTPS (Route53 + ACM) ---

resource "aws_route53_zone" "app" {
  count = local.domain_enabled && var.manage_dns ? 1 : 0
  name  = var.domain_name

  tags = {
    Name = "${local.name_prefix}-zone"
  }
}

resource "aws_acm_certificate" "app" {
  count                     = local.domain_enabled && var.manage_dns ? 1 : 0
  domain_name               = var.domain_name
  subject_alternative_names = ["www.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-cert"
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = local.domain_enabled && var.manage_dns ? {
    for dvo in aws_acm_certificate.app[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.app[0].zone_id
}

resource "aws_acm_certificate_validation" "app" {
  count                   = local.domain_enabled && var.manage_dns ? 1 : 0
  certificate_arn         = aws_acm_certificate.app[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]

  timeouts {
    create = "45m"
  }
}

resource "aws_route53_record" "apex" {
  count   = local.domain_enabled && var.manage_dns && (local.https_on || local.managed_https_on) ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "www" {
  count   = local.domain_enabled && var.manage_dns && (local.https_on || local.managed_https_on) ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

# Hostinger mailbox DNS (site apex/www stay ALB aliases — never Hostinger A 2.57.x)
locals {
  hostinger_mail_on = local.domain_enabled && var.manage_dns && var.hostinger_mail_dns
}

resource "aws_route53_record" "mx" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "MX"
  ttl     = 14400
  records = [
    "5 mx1.hostinger.com",
    "10 mx2.hostinger.com",
  ]
}

resource "aws_route53_record" "spf" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "TXT"
  ttl     = 14400
  # Apex TXT is one RRset — SPF + Google Search Console verification together.
  records = [
    local.apex_spf,
    "google-site-verification=yo37H-rnMsn-bMsyzOearpVxl4VISl6S7wVb6mZYEZE",
  ]
}

resource "aws_route53_record" "dkim_hostinger" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "hostingermail1._domainkey.${var.domain_name}"
  type    = "TXT"
  ttl     = 3600
  # Provider stores long TXT as chunk1 + `" "` + chunk2 (255-char DNS character-strings).
  records = [
    "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtPL2TiEboNfZGBqFiZEauZKtqAkF0A/ACw++eTbLreUxAt6ndtE5S+27CjLN7410+yooFvniFdveBp2jpav/2/xFqnDFXeyx8n1n95L/Hz/twa47i+6WwSsl59kJP23iYScw8DzSI2+hVCpoNYeN4a++sOc1KAWeRLuGng0+2rUj28BSX6Kcfuq6L+Qr55qJt\" \"1eOTF+77haFyBCmcmmUygvKQj+UlEDC4kbWtSKsG7xND9g/sWFKZKOhUohK1O89XXE381b4DIPNZQWbIYXQEv+p3xIbd2MlwxTvuQ5KPfPf1/ZRsSipPx47KQ8cyvCCIjZ0U4OU1oFg+mqtZLhAkQIDAQAB"
  ]
}

resource "aws_route53_record" "dmarc" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 3600
  records = ["v=DMARC1; p=none"]
}

resource "aws_route53_record" "autodiscover" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "autodiscover.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["autodiscover.mail.hostinger.com"]
}

resource "aws_route53_record" "autoconfig" {
  count   = local.hostinger_mail_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "autoconfig.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["autoconfig.mail.hostinger.com"]
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# Persistent auth SQLite (auth.db) — survives ECS task replacement.
resource "aws_security_group" "efs" {
  count       = var.enable_auth_efs && var.use_db_auth ? 1 : 0
  name        = "${local.name_prefix}-efs"
  description = "NFS from ECS tasks to auth EFS"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_efs_file_system" "auth" {
  count          = var.enable_auth_efs && var.use_db_auth ? 1 : 0
  creation_token = "${local.name_prefix}-auth"
  encrypted      = true

  tags = {
    Name = "${local.name_prefix}-auth"
  }
}

resource "aws_efs_mount_target" "auth" {
  count           = var.enable_auth_efs && var.use_db_auth ? length(local.app_subnets) : 0
  file_system_id  = aws_efs_file_system.auth[0].id
  subnet_id       = local.app_subnets[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

resource "aws_efs_access_point" "auth" {
  count          = var.enable_auth_efs && var.use_db_auth ? 1 : 0
  file_system_id = aws_efs_file_system.auth[0].id

  posix_user {
    uid = 0
    gid = 0
  }

  root_directory {
    path = "/auth"
    creation_info {
      owner_uid   = 0
      owner_gid   = 0
      permissions = "755"
    }
  }

  tags = {
    Name = "${local.name_prefix}-auth-ap"
  }
}

resource "aws_iam_role_policy" "ecs_task_efs" {
  count = var.enable_auth_efs && var.use_db_auth ? 1 : 0
  name  = "${local.name_prefix}-ecs-task-efs"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite"
      ]
      Resource = aws_efs_file_system.auth[0].arn
      Condition = {
        StringEquals = {
          "elasticfilesystem:AccessPointArn" = aws_efs_access_point.auth[0].arn
        }
      }
    }]
  })
}

# Single task: API + nginx (proxies /api|/health|/docs → localhost:8000).
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.app_cpu
  memory                   = var.app_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

  dynamic "volume" {
    for_each = var.enable_auth_efs && var.use_db_auth ? [1] : []
    content {
      name = "auth-data"
      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.auth[0].id
        transit_encryption = "ENABLED"
        authorization_config {
          access_point_id = aws_efs_access_point.auth[0].id
          iam             = "ENABLED"
        }
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      mountPoints = var.enable_auth_efs && var.use_db_auth ? [
        {
          sourceVolume  = "auth-data"
          containerPath = "/data"
          readOnly      = false
        }
      ] : []
      environment = concat(
        [
          { name = "INTELLENS_ENV", value = "aws" },
          { name = "SSO", value = var.sso_enabled ? "true" : "false" }
        ],
        var.use_db_auth ? [
          { name = "USE_DB_AUTH", value = "1" },
          { name = "AUTH_SQLITE_PATH", value = var.auth_sqlite_path }
        ] : [],
        var.fmp_api_key != "" && !local.secrets_enabled ? [
          { name = "INTELLENS_FMP_API_KEY", value = var.fmp_api_key }
        ] : [],
        var.openai_api_key != "" && !local.secrets_enabled ? [
          { name = "OPENAI_API_KEY", value = var.openai_api_key }
        ] : [],
        var.gemini_api_key != "" && !local.secrets_enabled ? [
          { name = "GEMINI_API_KEY", value = var.gemini_api_key }
        ] : [],
        var.gemini_api_key != "" ? [
          { name = "INTELLENS_LLM_BASE_URL", value = "https://generativelanguage.googleapis.com/v1beta/openai" },
          { name = "INTELLENS_LLM_MODEL", value = var.gemini_chat_model },
          { name = "INTELLENS_EMBED_MODEL", value = var.gemini_embed_model }
        ] : [],
        var.force_https ? [
          { name = "FORCE_HTTPS", value = "true" }
        ] : [],
        var.enable_hsts || var.force_https ? [
          { name = "ENABLE_HSTS", value = "true" }
        ] : [],
        var.intellens_public_url != "" ? [
          { name = "INTELLENS_PUBLIC_URL", value = var.intellens_public_url }
          ] : (
          var.domain_name != "" ? [
            { name = "INTELLENS_PUBLIC_URL", value = "https://${var.domain_name}" }
          ] : []
        ),
        var.oidc_client_id != "" ? [
          { name = "OIDC_CLIENT_ID", value = var.oidc_client_id }
        ] : [],
        var.oidc_client_secret != "" && !local.secrets_enabled ? [
          { name = "OIDC_CLIENT_SECRET", value = var.oidc_client_secret }
        ] : [],
        var.oidc_issuer != "" ? [
          { name = "OIDC_ISSUER", value = var.oidc_issuer }
        ] : [],
        var.oidc_redirect_uri != "" ? [
          { name = "OIDC_REDIRECT_URI", value = var.oidc_redirect_uri }
          ] : (
          var.domain_name != "" ? [
            { name = "OIDC_REDIRECT_URI", value = "https://${var.domain_name}/api/auth/sso/callback" }
          ] : []
        ),
        var.alphahunter_api_url != "" ? [
          { name = "ALPHAHUNTER_API_URL", value = var.alphahunter_api_url }
        ] : [],
        var.alphahunter_api_key != "" && !local.secrets_enabled ? [
          { name = "ALPHAHUNTER_API_KEY", value = var.alphahunter_api_key }
        ] : [],
        var.csm_email != "" ? [
          { name = "CSM_EMAIL", value = var.csm_email }
        ] : [],
        var.pilot_request_to != "" ? [
          { name = "PILOT_REQUEST_TO", value = var.pilot_request_to }
        ] : [],
        local.ses_on && var.smtp_host == "" ? [
          { name = "INTELLENS_MAIL_TRANSPORT", value = "ses" },
          { name = "SMTP_FROM", value = var.smtp_from != "" ? var.smtp_from : "CiteAlpha <no-reply@${var.domain_name}>" },
          { name = "AWS_REGION", value = var.aws_region },
        ] : [],
        var.smtp_host != "" ? [
          { name = "SMTP_HOST", value = var.smtp_host },
          { name = "SMTP_PORT", value = var.smtp_port },
          { name = "SMTP_FROM", value = var.smtp_from },
          { name = "SMTP_USER", value = var.smtp_user }
        ] : [],
        var.smtp_host != "" && var.smtp_pass != "" && !local.secrets_enabled ? [
          { name = "SMTP_PASS", value = var.smtp_pass }
        ] : [],
        var.intellens_auth_dev_tokens ? [
          { name = "INTELLENS_AUTH_DEV_TOKENS", value = "1" }
          ] : [
          { name = "INTELLENS_AUTH_DEV_TOKENS", value = "0" }
        ],
        var.intellens_api_key != "" && !local.secrets_enabled ? [
          { name = "INTELLENS_API_KEY", value = var.intellens_api_key }
        ] : [],
        var.intellens_abuse_secret != "" && !local.secrets_enabled ? [
          { name = "INTELLENS_ABUSE_SECRET", value = var.intellens_abuse_secret }
        ] : [],
        [
          { name = "RADAR_DIGEST", value = var.radar_digest ? "1" : "0" },
          { name = "IR_MIRROR", value = var.ir_mirror ? "1" : "0" },
          { name = "PORTFOLIO_STRETCH", value = var.portfolio_stretch ? "1" : "0" },
          { name = "INTELLENS_GUIDANCE_REVIEW", value = "1" }
        ],
        var.enable_auth_efs && var.use_db_auth ? [
          { name = "INTELLENS_DATA_DIR", value = "/data/citealpha" },
          { name = "INTELLENS_INDIA_COVERAGE", value = "1" },
          { name = "INTELLENS_FILING_LIVE", value = "1" },
          { name = "INTELLENS_FILING_FETCH_DAILY_CAP", value = "40000" },
          { name = "INTELLENS_FILING_DISCOVERY_DAILY_CAP", value = "10000" },
          { name = "INTELLENS_INDIA_COVERAGE_COHORT", value = "nifty50,nifty500" },
          { name = "INTELLENS_FILING_DISCOVERY_SINCE", value = "2024-01-01" },
          { name = "INTELLENS_US_COVERAGE", value = "1" },
          { name = "INTELLENS_SEC_USER_AGENT", value = "CiteAlpha filings research ops@citealpha.com" },
          { name = "INTELLENS_EXTRACT_LLM_DAILY_CAP", value = "100000" },
          { name = "INTELLENS_LLM_RATE_PER_MIN", value = "200" },
          { name = "INTELLENS_DISCLOSURE_READ_WORKERS", value = "8" },
          { name = "INTELLENS_DISCLOSURE_SERVICE_TIER", value = "flex" },
          { name = "MALLOC_ARENA_MAX", value = "2" },
          { name = "INTELLENS_WEB_SEARCH_DISCOVERY", value = "1" },
          { name = "INTELLENS_IR_CRAWL_DISCOVERY", value = "1" }
        ] : [],
        var.enable_index_bucket ? [
          { name = "INTELLENS_INDEX_S3_BUCKET", value = aws_s3_bucket.index[0].bucket },
          { name = "INTELLENS_INDEX_S3_PREFIX", value = "index" },
          { name = "INTELLENS_LEDGER_DIGEST", value = "1" }
        ] : [],
        var.ledger_digest_to != "" ? [
          { name = "INTELLENS_LEDGER_DIGEST_TO", value = var.ledger_digest_to }
        ] : []
      )
      secrets = local.secrets_enabled ? local.api_secret_refs : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 20
      }
    },
    {
      name      = "web"
      image     = "${aws_ecr_repository.web.repository_url}:${var.image_tag}"
      essential = true
      dependsOn = [{
        containerName = "api"
        condition     = "HEALTHY"
      }]
      portMappings = [{
        containerPort = 80
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.web.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 100 - var.fargate_spot_weight
    base              = var.fargate_on_demand_base
  }

  dynamic "capacity_provider_strategy" {
    for_each = var.fargate_spot_weight > 0 && var.cpu_architecture == "X86_64" ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = var.fargate_spot_weight
      base              = 0
    }
  }

  network_configuration {
    subnets          = local.app_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "web"
    container_port   = 80
  }

  depends_on = [
    aws_ecs_cluster_capacity_providers.main,
    aws_lb_listener.http,
  ]
}
