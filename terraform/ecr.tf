resource "aws_ecr_repository" "this" {
  for_each = local.ecr_repositories

  name                 = "${var.project}/${each.key}"
  image_tag_mutability = local.ecr_tag_mutability
  force_delete         = local.ecr_force_delete

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after ${local.ecr_untagged_expiry_day} days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = local.ecr_untagged_expiry_day
      }
      action = { type = "expire" }
    }]
  })
}
