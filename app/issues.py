from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash as flask_flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .extensions import db
from .i18n import translate
from .models import Issue, IssueStatusHistory, MaintenanceSkill, RoomAssignment, User, utcnow

issues_bp = Blueprint("issues", __name__)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def flash(message, category=None):
    flask_flash(translate(message), category)


def has_role(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@issues_bp.get("/issues")
@login_required
def list_issues():
    query = db.select(Issue).order_by(Issue.created_at.desc())
    if current_user.role == "student":
        query = query.where(Issue.student_id == current_user.id)
    elif current_user.role == "technician":
        query = query.where(Issue.technician_id == current_user.id)
    status = request.args.get("status", "")
    if status in {"open", "assigned", "in_progress", "closed"}:
        query = query.where(Issue.status == status)
    return render_template("issues/list.html", issues=db.session.scalars(query).all(), status=status)


@issues_bp.route("/issues/new", methods=["GET", "POST"])
@has_role("student")
def create_issue():
    assignment = db.session.scalar(db.select(RoomAssignment).where(RoomAssignment.student_id == current_user.id, RoomAssignment.end_date.is_(None)))
    if assignment is None:
        flash("Talep gönderebilmeniz için önce yönetici tarafından oda atanmalıdır.", "warning")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        photo = request.files.get("photo")
        if not 4 <= len(title) <= 120 or not 10 <= len(description) <= 3000:
            flash("4–120 karakterlik bir başlık ve 10–3000 karakterlik açıklama girin.", "danger")
            return render_template("issues/new.html"), 400
        filename = None
        if photo and photo.filename:
            extension = photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else ""
            if extension not in ALLOWED_EXTENSIONS:
                flash("Görsel JPG, PNG veya WEBP biçiminde olmalıdır.", "danger")
                return render_template("issues/new.html"), 400
            safe_name = secure_filename(photo.filename)
            filename = f"{uuid4().hex}_{safe_name[:100]}"
            signature = photo.stream.read(12)
            photo.stream.seek(0)
            valid_signature = (
                (extension in {"jpg", "jpeg"} and signature.startswith(b"\xff\xd8\xff"))
                or (extension == "png" and signature.startswith(b"\x89PNG\r\n\x1a\n"))
                or (extension == "webp" and signature.startswith(b"RIFF") and signature[8:12] == b"WEBP")
            )
            if not valid_signature:
                flash("Dosya içeriği geçerli bir görsel gibi görünmüyor.", "danger")
                return render_template("issues/new.html"), 400
            photo.save(Path(current_app.config["UPLOAD_FOLDER"]) / filename)
        issue = Issue(student_id=current_user.id, room_id=assignment.room_id, title=title, description=description, photo_filename=filename)
        db.session.add(issue)
        db.session.flush()
        db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=current_user.id, from_status=None, to_status="open", note="Talep oluşturuldu"))
        db.session.commit()
        flash("Talep gönderildi.", "success")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    return render_template("issues/new.html")


@issues_bp.get("/issues/<int:issue_id>")
@login_required
def issue_detail(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    if current_user.role == "student" and issue.student_id != current_user.id:
        abort(403)
    if current_user.role == "technician" and issue.technician_id != current_user.id:
        abort(403)
    technicians, skills = [], []
    if current_user.role == "manager":
        technicians = db.session.scalars(db.select(User).where(User.role == "technician").order_by(User.name)).all()
        skills = db.session.scalars(db.select(MaintenanceSkill).order_by(MaintenanceSkill.name)).all()
    return render_template("issues/detail.html", issue=issue, technicians=technicians, skills=skills)


@issues_bp.get("/issues/<int:issue_id>/photo")
@login_required
def issue_photo(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    if current_user.role == "student" and issue.student_id != current_user.id:
        abort(403)
    if current_user.role == "technician" and issue.technician_id != current_user.id:
        abort(403)
    if not issue.photo_filename:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], issue.photo_filename)


@issues_bp.route("/issues/<int:issue_id>/edit", methods=["GET", "POST"])
@has_role("student")
def edit_issue(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    if issue.student_id != current_user.id:
        abort(403)
    if issue.status != "open" or issue.technician_id is not None:
        flash("Talep yalnızca teknisyene atanmadan önce düzenlenebilir.", "warning")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not 4 <= len(title) <= 120 or not 10 <= len(description) <= 3000:
            flash("Başlık ve açıklama uzunluğunu kontrol edin.", "danger")
            return render_template("issues/edit.html", issue=issue), 400
        issue.title, issue.description = title, description
        db.session.commit()
        flash("Talep güncellendi.", "success")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    return render_template("issues/edit.html", issue=issue)


@issues_bp.post("/issues/<int:issue_id>/delete")
@has_role("student")
def delete_issue(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    if issue.student_id != current_user.id:
        abort(403)
    if issue.status != "open" or issue.technician_id is not None:
        flash("İşlem başlamış bir talep silinemez.", "warning")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    if issue.photo_filename:
        photo_path = Path(current_app.config["UPLOAD_FOLDER"]) / issue.photo_filename
        photo_path.unlink(missing_ok=True)
    db.session.delete(issue)
    db.session.commit()
    flash("Açık talep silindi.", "success")
    return redirect(url_for("issues.list_issues"))


@issues_bp.post("/issues/<int:issue_id>/assign")
@has_role("manager")
def assign_issue(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    try:
        technician = db.get_or_404(User, int(request.form.get("technician_id", "")))
    except ValueError:
        flash("Geçerli bir teknisyen seçin.", "danger")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    if technician.role != "technician":
        flash("Teknisyen rolündeki bir hesap seçin.", "danger")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    skill_id = request.form.get("skill_id", "")
    if skill_id:
        try:
            skill = db.get_or_404(MaintenanceSkill, int(skill_id))
        except ValueError:
            flash("Uzmanlık türü geçersiz.", "danger")
            return redirect(url_for("issues.issue_detail", issue_id=issue.id))
        if skill not in technician.skills:
            flash("Bu teknisyen bu uzmanlık alanında kayıtlı değil.", "danger")
            return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    old_status = issue.status
    issue.technician_id = technician.id
    issue.status = "assigned"
    issue.closed_at = None
    issue.resolution_minutes = None
    db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=current_user.id, from_status=old_status, to_status="assigned", note=f"Şu teknisyene atandı: {technician.name}"))
    db.session.commit()
    flash("Talep teknisyene atandı.", "success")
    return redirect(url_for("issues.issue_detail", issue_id=issue.id))


@issues_bp.post("/issues/<int:issue_id>/status")
@login_required
def update_status(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    new_status = request.form.get("status", "")
    allowed_by_role = {"technician": {"in_progress", "closed"}}
    if current_user.role not in allowed_by_role or new_status not in allowed_by_role[current_user.role]:
        abort(403)
    if current_user.role == "technician" and issue.technician_id != current_user.id:
        abort(403)
    transitions = {"open": {"assigned"}, "assigned": {"in_progress", "open"}, "in_progress": {"closed", "assigned"}, "closed": {"assigned"}}
    if new_status not in transitions.get(issue.status, set()):
        flash("İstenen durum geçişine izin verilmiyor.", "danger")
        return redirect(url_for("issues.issue_detail", issue_id=issue.id))
    previous = issue.status
    issue.status = new_status
    if new_status == "closed":
        issue.closed_at = utcnow()
        issue.resolution_minutes = max(0, int((issue.closed_at - issue.created_at).total_seconds() // 60))
    else:
        issue.closed_at = None
        issue.resolution_minutes = None
    db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=current_user.id, from_status=previous, to_status=new_status, note=request.form.get("note", "").strip()[:255] or None))
    db.session.commit()
    flash("Talep durumu güncellendi.", "success")
    return redirect(url_for("issues.issue_detail", issue_id=issue.id))

