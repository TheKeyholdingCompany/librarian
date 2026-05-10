from flask import Flask

from config import Config
from app.extensions import db, migrate, oauth
from app.storage import public_url


class _CloudFrontHTTPSFix:
    """Flip wsgi.url_scheme to https when the request came in via CloudFront.

    The stack is CloudFront(HTTPS) → ALB(HTTP) → ECS, and ALB *replaces*
    `X-Forwarded-Proto` with its listener's value (http) rather than
    appending — so the standard ProxyFix pattern doesn't help here.
    CloudFront is configured to inject `X-Forwarded-Scheme: https` as an
    immutable origin custom header (see terraform/main/modules/cloudfront/main.tf); ALB
    passes that name through verbatim because it has no special handling
    for it. Presence = the request entered through prod's CloudFront,
    so url_for(_external=True) should generate https URLs (e.g. the OIDC
    redirect_uri that Keycloak validates).
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get("HTTP_X_FORWARDED_SCHEME") == "https":
            environ["wsgi.url_scheme"] = "https"
        return self.wsgi_app(environ, start_response)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.wsgi_app = _CloudFrontHTTPSFix(app.wsgi_app)

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
        # PKCE is required by the Keycloak client config (S256). Authlib
        # doesn't auto-enable it from server metadata; opting in here makes
        # the SDK generate the code_verifier and send code_challenge /
        # code_challenge_method on the authorize redirect.
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
        },
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
