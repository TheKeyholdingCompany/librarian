resource "aws_lb" "this" {
  name               = "${var.name}-${var.env}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.public_subnet_ids

  tags = { Name = "${var.name}-${var.env}-alb" }
}

# ── Target Group ───────────────────────────────────────────

resource "aws_lb_target_group" "api" {
  name        = "${var.name}-${var.env}-api"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  # `/health` is the unauthenticated route added in app/__init__.py — every
  # other Flask route is wrapped in @login_required and would 302 to /auth/login,
  # which the target group reads as unhealthy.
  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# ── Listener ──────────────────────────────────────────────
#
# Catch-all: CloudFront is the only client. Plain HTTP between CloudFront
# and the ALB is acceptable here because the ALB's security group only
# accepts traffic from the CloudFront prefix list, and CloudFront → viewer
# is HTTPS.

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── Variables ──────────────────────────────────────────────

variable "name" { type = string }
variable "env" { type = string }

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

# ── Outputs ────────────────────────────────────────────────

output "dns_name" {
  value = aws_lb.this.dns_name
}

output "arn" {
  value = aws_lb.this.arn
}

output "api_target_group_arn" {
  value = aws_lb_target_group.api.arn
}
