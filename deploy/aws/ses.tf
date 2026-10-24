# Product mail via SES in the same region as the task. Hostinger keeps the
# apex MX, so sales@citealpha.com still arrives in the company mailbox.
# Easy DKIM uses its own selector and does not replace hostingermail1._domainkey.

locals {
  ses_on = var.enable_ses && local.domain_enabled && var.manage_dns
  apex_spf = (
    local.ses_on
    ? "v=spf1 include:_spf.mail.hostinger.com include:amazonses.com ~all"
    : "v=spf1 include:_spf.mail.hostinger.com ~all"
  )
  pilot_notify = [
    for addr in split(",", var.pilot_request_to) : trimspace(addr) if trimspace(addr) != ""
  ]
  # Domain identity covers @citealpha.com. Any other inbox must confirm a
  # one-time SES verification mail before the account leaves the sandbox.
  ses_extra_recipients = local.ses_on ? toset([
    for addr in local.pilot_notify : addr
    if !endswith(lower(addr), "@${lower(var.domain_name)}")
  ]) : toset([])
}

resource "aws_sesv2_email_identity" "domain" {
  count          = local.ses_on ? 1 : 0
  email_identity = var.domain_name
}

resource "aws_sesv2_email_identity_mail_from_attributes" "domain" {
  count                  = local.ses_on ? 1 : 0
  email_identity         = aws_sesv2_email_identity.domain[0].email_identity
  mail_from_domain       = "ses.${var.domain_name}"
  behavior_on_mx_failure = "USE_DEFAULT_VALUE"
}

resource "aws_route53_record" "ses_dkim" {
  count   = local.ses_on ? 3 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "${aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens[count.index]}._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 600
  records = ["${aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
}

resource "aws_route53_record" "ses_mail_from_mx" {
  count   = local.ses_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "ses.${var.domain_name}"
  type    = "MX"
  ttl     = 600
  records = ["10 feedback-smtp.${var.aws_region}.amazonses.com"]
}

resource "aws_route53_record" "ses_mail_from_spf" {
  count   = local.ses_on ? 1 : 0
  zone_id = aws_route53_zone.app[0].zone_id
  name    = "ses.${var.domain_name}"
  type    = "TXT"
  ttl     = 600
  records = ["v=spf1 include:amazonses.com ~all"]
}

resource "aws_sesv2_email_identity" "extra_recipient" {
  for_each       = local.ses_extra_recipients
  email_identity = each.value
}

resource "aws_iam_role_policy" "ecs_task_ses" {
  count = local.ses_on ? 1 : 0
  name  = "${local.name_prefix}-ses-send"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "SendFromDomain"
      Effect = "Allow"
      Action = ["ses:SendEmail", "ses:SendRawEmail"]
      # A verified recipient identity is its own resource. The domain ARN
      # covers @citealpha.com. contact@ocotilloinnovation.com does not.
      Resource = concat(
        [aws_sesv2_email_identity.domain[0].arn],
        [for ident in aws_sesv2_email_identity.extra_recipient : ident.arn],
      )
    }]
  })
}
