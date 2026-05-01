from flask import Flask

from config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.auth import bp as auth_bp
    from app.library import bp as library_bp
    from app.admin import bp as admin_bp
    from app.about import bp as about_bp
    from app.borrower import bp as borrower_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(borrower_bp)

    from app import models  # noqa: F401  ensure models are registered with SQLAlchemy

    # ALB target-group probe. Must be unauthenticated — every other route is
    # behind @login_required, so without this the target group health check
    # gets a 302 to /auth/login and the task is marked unhealthy.
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
