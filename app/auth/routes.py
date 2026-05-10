import logging
from urllib.parse import urlencode

from authlib.integrations.base_client.errors import OAuthError
from flask import current_app, redirect, request, session, url_for

from app.auth import bp
from app.extensions import db, oauth
from app.models import User

logger = logging.getLogger(__name__)


@bp.route("/login")
def login():
    # Authlib generates state + PKCE verifier and stashes them in the session;
    # `authorize_redirect` returns a 302 to Keycloak's /auth endpoint.
    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.keycloak.authorize_redirect(redirect_uri)


@bp.route("/callback")
def callback():
    # Keycloak surfaces auth-time errors by redirecting back here with
    # ?error=...&error_description=... (no `code`), which makes Authlib's
    # token exchange raise OAuthError. Logging the upstream description
    # makes the cause obvious in CloudWatch instead of a generic 500.
    try:
        token = oauth.keycloak.authorize_access_token()
    except OAuthError as exc:
        logger.warning(
            "OIDC callback rejected by Keycloak: %s — %s",
            exc.error,
            exc.description,
        )
        return redirect(url_for("auth.login"))

    claims = token.get("userinfo") or {}

    sub = claims.get("sub")
    if not sub:
        logger.error("OIDC callback returned no sub claim: %s", claims)
        return redirect(url_for("auth.login"))

    user = _upsert_user_from_claims(claims)

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    # id_token kept for RP-initiated logout (`id_token_hint`).
    session["id_token"] = token.get("id_token")
    return redirect(url_for("library.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    id_token = session.get("id_token")
    session.clear()

    issuer = current_app.config.get("OIDC_ISSUER_URL")
    if not (id_token and issuer):
        return redirect(url_for("auth.login"))

    # RP-initiated logout: tells Keycloak to end its session too, otherwise
    # the next /login bounces straight back without a credential prompt.
    params = {
        "id_token_hint": id_token,
        "post_logout_redirect_uri": url_for("auth.login", _external=True),
    }
    end_session = f"{issuer.rstrip('/')}/protocol/openid-connect/logout"
    return redirect(f"{end_session}?{urlencode(params)}")


def _upsert_user_from_claims(claims):
    """Find-or-create the local mirror row for the authenticated Keycloak user.

    Lookup order is sub → email, so the existing seeded admin (no sub yet)
    gets linked the first time they sign in via Keycloak.
    """
    sub = claims["sub"]
    email = claims.get("email") or f"{sub}@unknown.local"
    username = claims.get("preferred_username") or email

    # Keycloak realm roles are surfaced into userinfo via a realm-roles mapper
    # configured on the client (see the keycloak-config repo). Without that
    # mapper, every user defaults to borrower.
    admin_role = current_app.config["OIDC_ADMIN_ROLE"]
    realm_roles = (claims.get("realm_access") or {}).get("roles", [])
    role = "admin" if admin_role in realm_roles else "borrower"

    user = User.query.filter_by(keycloak_sub=sub).first()
    if user is None:
        user = User.query.filter_by(email=email).first()

    if user is None:
        user = User(keycloak_sub=sub, username=username, email=email, role=role)
        db.session.add(user)
    else:
        user.keycloak_sub = sub
        user.username = username
        user.email = email
        user.role = role

    db.session.commit()
    return user
