from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash as flask_flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func

from .extensions import db
from .i18n import translate
from .models import Issue, MaintenanceSkill, Room, RoomAssignment, User

main_bp = Blueprint("main", __name__)


def flash(message, category=None):
    flask_flash(translate(message), category)


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@main_bp.app_errorhandler(403)
def forbidden(error):
    return render_template("errors/403.html"), 403


@main_bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


@main_bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.role == "student":
        assignment = db.session.scalar(db.select(RoomAssignment).where(RoomAssignment.student_id == current_user.id, RoomAssignment.end_date.is_(None)))
        issues = db.session.scalars(db.select(Issue).where(Issue.student_id == current_user.id).order_by(Issue.created_at.desc()).limit(6)).all()
        return render_template("dashboard.html", assignment=assignment, issues=issues)
    if current_user.role == "technician":
        issues = db.session.scalars(db.select(Issue).where(Issue.technician_id == current_user.id, Issue.status != "closed").order_by(Issue.created_at.asc())).all()
        closed_count = db.session.scalar(db.select(func.count(Issue.id)).where(Issue.technician_id == current_user.id, Issue.status == "closed")) or 0
        return render_template("dashboard.html", issues=issues, closed_count=closed_count)
    open_count = db.session.scalar(db.select(func.count(Issue.id)).where(Issue.status != "closed")) or 0
    room_count = db.session.scalar(db.select(func.count(Room.id)).where(Room.is_active.is_(True))) or 0
    technician_count = db.session.scalar(db.select(func.count(User.id)).where(User.role == "technician")) or 0
    issues = db.session.scalars(db.select(Issue).order_by(Issue.created_at.desc()).limit(8)).all()
    return render_template("dashboard.html", open_count=open_count, room_count=room_count, technician_count=technician_count, issues=issues)


@main_bp.get("/rooms")
@roles_required("manager")
def rooms():
    all_rooms = db.session.scalars(db.select(Room).order_by(Room.building, Room.number)).all()
    students = db.session.scalars(db.select(User).where(User.role == "student").order_by(User.name)).all()
    active_student_ids = set(db.session.scalars(db.select(RoomAssignment.student_id).where(RoomAssignment.end_date.is_(None))).all())
    unassigned_students = [student for student in students if student.id not in active_student_ids]
    technicians = db.session.scalars(db.select(User).where(User.role == "technician").order_by(User.name)).all()
    return render_template("rooms.html", rooms=all_rooms, students=students, unassigned_students=unassigned_students, technicians=technicians)


@main_bp.post("/rooms/new")
@roles_required("manager")
def create_room():
    building = request.form.get("building", "").strip()
    number = request.form.get("number", "").strip()
    try:
        floor = int(request.form.get("floor", "0"))
        capacity = int(request.form.get("capacity", "1"))
    except ValueError:
        floor, capacity = -1, 0
    if not building or not number or len(building) > 80 or len(number) > 20 or floor < 0 or not 1 <= capacity <= 20:
        flash("Oda bilgilerini ve kapasiteyi kontrol edin (1–20).", "danger")
        return redirect(url_for("main.rooms"))
    db.session.add(Room(building=building, number=number, floor=floor, capacity=capacity))
    try:
        db.session.commit()
        flash("Oda eklendi.", "success")
    except Exception:
        db.session.rollback()
        flash("Oda eklenemedi; bina ve oda numarası zaten kullanılıyor olabilir.", "danger")
    return redirect(url_for("main.rooms"))


@main_bp.post("/rooms/<int:room_id>/assign")
@roles_required("manager")
def assign_room(room_id):
    room = db.session.scalar(db.select(Room).where(Room.id == room_id).with_for_update())
    if room is None:
        abort(404)
    try:
        student = db.get_or_404(User, int(request.form.get("student_id", "")))
    except ValueError:
        flash("Geçerli bir öğrenci seçin.", "danger")
        return redirect(url_for("main.rooms"))
    has_active = db.session.scalar(db.select(RoomAssignment.id).where(RoomAssignment.student_id == student.id, RoomAssignment.end_date.is_(None)))
    occupied = db.session.scalar(db.select(func.count(RoomAssignment.id)).where(RoomAssignment.room_id == room.id, RoomAssignment.end_date.is_(None))) or 0
    if student.role != "student" or has_active or occupied >= room.capacity or not room.is_active:
        flash("Atama yapılamadı. Öğrenci rolünü, oda kapasitesini ve mevcut atamayı kontrol edin.", "danger")
        return redirect(url_for("main.rooms"))
    db.session.add(RoomAssignment(student_id=student.id, room_id=room.id, assigned_by_id=current_user.id, start_date=date.today()))
    try:
        db.session.commit()
        flash("Oda öğrenciye atandı.", "success")
    except Exception:
        db.session.rollback()
        flash("Atama sırasında çakışma oluştu. Sayfayı yenileyip tekrar deneyin.", "danger")
    return redirect(url_for("main.rooms"))


@main_bp.post("/rooms/<int:room_id>/edit")
@roles_required("manager")
def edit_room(room_id):
    room = db.get_or_404(Room, room_id)
    building = request.form.get("building", "").strip()
    number = request.form.get("number", "").strip()
    try:
        floor = int(request.form.get("floor", "0"))
        capacity = int(request.form.get("capacity", "1"))
    except ValueError:
        floor, capacity = -1, 0
    if not building or not number or len(building) > 80 or len(number) > 20 or floor < 0 or not 1 <= capacity <= 20:
        flash("Oda bilgilerini ve kapasiteyi kontrol edin.", "danger")
        return redirect(url_for("main.rooms"))
    if capacity < room.occupants_count:
        flash("Kapasite, odada kalan öğrenci sayısının altına düşürülemez.", "danger")
        return redirect(url_for("main.rooms"))
    room.building, room.number, room.floor, room.capacity = building, number, floor, capacity
    try:
        db.session.commit()
        flash("Oda bilgileri güncellendi.", "success")
    except Exception:
        db.session.rollback()
        flash("Değişiklik kaydedilemedi; aynı binada bu oda numarası kullanılıyor olabilir.", "danger")
    return redirect(url_for("main.rooms"))


@main_bp.post("/rooms/<int:room_id>/delete")
@roles_required("manager")
def delete_room(room_id):
    room = db.get_or_404(Room, room_id)
    if room.assignments or room.issues:
        flash("Ataması veya arıza geçmişi bulunan oda silinemez; geçmiş kayıtlar korunmalıdır.", "warning")
        return redirect(url_for("main.rooms"))
    db.session.delete(room)
    db.session.commit()
    flash("Oda silindi.", "success")
    return redirect(url_for("main.rooms"))


@main_bp.post("/assignments/<int:assignment_id>/end")
@roles_required("manager")
def end_assignment(assignment_id):
    assignment = db.get_or_404(RoomAssignment, assignment_id)
    if assignment.end_date is None:
        assignment.end_date = date.today()
        db.session.commit()
        flash("Oda ataması sona erdirildi.", "success")
    return redirect(url_for("main.rooms"))


@main_bp.post("/team/new")
@roles_required("manager")
def create_team_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")
    skill_names = list(dict.fromkeys(value.strip()[:80] for value in request.form.get("skills", "").split(",") if value.strip()))[:10]
    if role not in {"technician", "manager"} or len(name) < 2 or "@" not in email or len(password) < 8 or db.session.scalar(db.select(User.id).where(User.email == email)):
        flash("Hesap bilgileri geçersiz veya e-posta adresi zaten kullanılıyor. Şifre en az 8 karakter olmalıdır.", "danger")
        return redirect(url_for("main.rooms"))
    member = User(name=name, email=email, role=role)
    member.set_password(password)
    if role == "technician":
        for skill_name in skill_names[:10]:
            skill = db.session.scalar(db.select(MaintenanceSkill).where(MaintenanceSkill.name == skill_name))
            if skill is None:
                skill = MaintenanceSkill(name=skill_name[:80])
            member.skills.append(skill)
    db.session.add(member)
    db.session.commit()
    flash("Hesap oluşturuldu. Giriş bilgilerini teknisyene güvenli şekilde iletin.", "success")
    return redirect(url_for("main.rooms"))


@main_bp.get("/reports")
@roles_required("manager")
def reports():
    rows = db.session.execute(
        db.select(User.name, func.count(Issue.id).label("total"),
                  func.sum(case((Issue.status == "closed", 1), else_=0)).label("closed"),
                  func.avg(Issue.resolution_minutes).label("avg_minutes"))
        .outerjoin(Issue, Issue.technician_id == User.id)
        .where(User.role == "technician")
        .group_by(User.id, User.name)
        .order_by(func.count(Issue.id).desc(), User.name)
    ).all()
    return render_template("reports.html", rows=rows)
