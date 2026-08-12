# ── ECS Cluster ─────────────────────────────────────────────

resource "aws_ecs_cluster" "this" {
  name = "${var.name}-${var.env}"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

# ── CloudWatch Log Group ───────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.name}-${var.env}/api"
  retention_in_days = 14
}

# ── IAM ────────────────────────────────────────────────────

# Execution role: what ECS itself needs (pull image, write logs, fetch
# secrets). Distinct from the task role, which is what the running
# container's code can do.
resource "aws_iam_role" "ecs_execution" {
  name = "${var.name}-${var.env}-ecs-execution"

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

# Scoped narrowly to the two secrets we actually inject + the KMS key
# they're encrypted with. AmazonECSTaskExecutionRolePolicy doesn't include
# secretsmanager:GetSecretValue.
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${var.name}-${var.env}-ecs-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.secret_arns
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = var.secrets_kms_key_arn
      },
    ]
  })
}

# Task role: what the running Flask process can call. Currently empty —
# Flask doesn't talk to S3 / SQS / SES. Kept as a separate role so adding
# a permission later is one resource, not a refactor.
resource "aws_iam_role" "ecs_task" {
  name = "${var.name}-${var.env}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# ── API Service ────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-${var.env}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  # 256 CPU / 512 MiB is the smallest valid Fargate combo. Flask + gunicorn
  # with 3 workers + Alembic on boot fits comfortably; if we add background
  # work or large image processing later, bump this and remember it's
  # billed per-second, not per-deploy.
  cpu                = 256
  memory             = 512
  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.api_image}:latest"

    portMappings = [{
      containerPort = 8080
      protocol      = "tcp"
    }]

    # Plain DB_* envs only — DB_PASSWORD is a secret, and entrypoint.sh
    # assembles DATABASE_URL inside the container so the password never
    # appears in the task-definition output.
    environment = [
      { name = "PORT", value = "8080" },
      { name = "HOST", value = "0.0.0.0" },
      { name = "DB_USER", value = var.db_username },
      { name = "DB_HOST", value = var.db_address },
      { name = "DB_PORT", value = tostring(var.db_port) },
      { name = "DB_NAME", value = var.db_name },
      { name = "AWS_REGION", value = var.region },
      { name = "S3_BUCKET", value = var.s3_uploads_bucket },
      { name = "S3_PUBLIC_BASE_URL", value = var.s3_uploads_public_base_url },
      { name = "OIDC_ISSUER_URL", value = var.oidc_issuer_url },
      { name = "OIDC_CLIENT_ID", value = var.oidc_client_id },
      { name = "OIDC_ADMIN_ROLE", value = var.oidc_admin_role },
    ]

    # `valueFrom` accepts a Secrets Manager ARN with a JSON-pointer suffix:
    # `:json-key::` selects a single field from the JSON-encoded secret.
    # ECS materialises these as env vars at container start.
    secrets = [
      { name = "DB_PASSWORD", valueFrom = "${var.rds_secret_arn}:password::" },
      { name = "SECRET_KEY", valueFrom = "${var.flask_secret_arn}:secret_key::" },
      { name = "OIDC_CLIENT_SECRET", valueFrom = "${var.oidc_secret_arn}:client_secret::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.name}-${var.env}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  propagate_tags  = "SERVICE"

  # 50/200: a deploy can run two old + two new tasks, traffic shifts only
  # after the new ones pass /health. Zero-downtime at the cost of one
  # extra Fargate task for the rollout window.
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = var.api_target_group_arn
    container_name   = "api"
    container_port   = 8080
  }
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "service_name" {
  value = aws_ecs_service.api.name
}

output "task_role_name" {
  value       = aws_iam_role.ecs_task.name
  description = "Name of the IAM role assumed by the running container; attach extra policies to grant the app new permissions."
}
