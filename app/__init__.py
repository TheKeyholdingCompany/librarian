from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from app.extensions import db, migrate, oauth
from app.storage import public_url


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CloudFront → ALB (HTTP) → ECS. CloudFront stamps `X-Forwarded-Proto:
    # https`; ALB appends its own `http`. x_proto=2 picks the CloudFront
    # value so `url_for(..., _external=True)` produces https URLs (e.g.
    # the OIDC redirect_uri Keycloak validates). x_for=2 mirrors the same
    # for client IPs in access logs.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=2, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)

    # Authlib loads the realm's OIDC discovery doc on first use to pick up
    # endpoints and JWKS — no need to hard-code per-realm URLs.
    oauth.init_app(app)
    oauth.register(
        name="keycloak",
        server_metadata_url=f"{app.config['OIDC_ISSUER_URL'].rstrip('/')}/.well-known/openid-configuration",
        client_id=app.config["OIDC_CLIENT_ID"],
        client_secret=app.config["OIDC_CLIENT_SECRET"],
        client_kwargs={"scope": "openid email profile"},
    )

    from app.auth import bp as auth_bp
    from app.library import bp as library_bp
    from app.admin import bp as admin_bp
    from app.about import bp as about_bp
    from app.borrower import bp as borrower_bp
    # url_prefix="/auth" puts login/callback/logout under /auth/* — must
    # match the Valid Redirect URIs registered on the Keycloak client.
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(library_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(borrower_bp)

    # Templates resolve a book's S3 key to its public URL via this helper.
    @app.context_processor
    def inject_image_helpers():
        return {"book_image_url": public_url}

    from app import models  # noqa: F401  ensure models are registered with SQLAlchemy

    # ALB target-group probe. Must be unauthenticated — every other route is
    # behind @login_required, so without this the target group health check
    # gets a 302 to /auth/login and the task is marked unhealthy.
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
