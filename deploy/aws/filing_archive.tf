# Stored filings and transcripts, one private bucket per exchange: NSE, BSE, and
# every other market (intl). The task copies extracted text and the file as served
# from the data volume (app/services/filing_archive.py). Off until enable_filing_archive.

locals {
  filing_archive_exchanges = var.enable_filing_archive ? toset(["nse", "bse", "intl"]) : toset([])
}

resource "aws_s3_bucket" "filings" {
  for_each = local.filing_archive_exchanges
  bucket   = "${local.name_prefix}-filings-${each.key}-${data.aws_caller_identity.current.account_id}"
  tags = {
    Purpose  = "filing-archive"
    Exchange = each.key
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "filings" {
  for_each = aws_s3_bucket.filings
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "filings" {
  for_each                = aws_s3_bucket.filings
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "filings" {
  for_each = aws_s3_bucket.filings
  bucket   = each.value.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_iam_role_policy" "ecs_task_filings_s3" {
  count = var.enable_filing_archive ? 1 : 0
  name  = "${local.name_prefix}-ecs-task-filings-s3"
  role  = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
      Resource = flatten([for b in aws_s3_bucket.filings : [b.arn, "${b.arn}/*"]])
    }]
  })
}
