import re

from flask import Blueprint, flash as flask_flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from .extensions import db
from .i18n import translate
from .models import User

auth_bp = Blueprint("auth", __name__)


def flash(message, category=None):
    flask_flash(translate(message), category)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if not 2 <= len(name) <= 100:
            errors.append("Ad 2 ile 100 karakter arasında olmalıdır.")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 255:
            errors.append("Geçerli bir e-posta adresi girin.")
        if len(password) < 8 or len(password) > 128:
            errors.append("Şifre en az 8 karakter olmalıdır.")
        if db.session.scalar(db.select(User.id).where(func.lower(User.email) == email)):
            errors.append("Bu e-posta adresi zaten kayıtlı.")
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html"), 400
        user = User(name=name, email=email, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Hesap başarıyla oluşturuldu.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(func.lower(User.email) == email))
        if user is None or not user.check_password(password):
            flash("E-posta adresi veya şifre yanlış.", "danger")
            return render_template("auth/login.html"), 401
        login_user(user, remember=request.form.get("remember") == "on")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Oturum kapatıldı.", "info")
    return redirect(url_for("auth.login"))
