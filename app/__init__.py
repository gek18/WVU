import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_wtf.csrf import CSRFError

from .extensions import csrf, db, login_manager, migrate


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, record):
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-development-key-change-before-deploying"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///dorm_maintenance.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bu sayfaya erişmek için giriş yapın."
    login_manager.login_message_category = "warning"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint == "api":
            return jsonify(error="Giriş yapmanız gerekiyor."), 401
        return redirect(url_for("auth.login", next=request.url))

    from . import models  # noqa: F401
    from .api import api_bp
    from .auth import auth_bp
    from .issues import issues_bp
    from .main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template("errors/413.html"), 413

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = "Güvenlik doğrulaması başarısız. Sayfayı yenileyip tekrar deneyin."
        if request.blueprint == "api":
            return jsonify(error=message), 400
        return render_template("errors/400.html"), 400

    @app.cli.command("create-manager")
    def create_manager_command():
        """İlk yönetici hesabını etkileşimli olarak oluştur."""
        import getpass
        import click
        from .models import User

        name = click.prompt("Yönetici adı")
        email = click.prompt("Yönetici e-posta adresi").strip().lower()
        password = getpass.getpass("Şifre (en az 8 karakter): ")
        if len(password) < 8 or db.session.scalar(db.select(User.id).where(User.email == email)):
            raise click.ClickException("Şifre çok kısa veya e-posta adresi zaten kayıtlı.")
        user = User(name=name.strip(), email=email, role="manager")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Yönetici hesabı oluşturuldu.")

    return app
