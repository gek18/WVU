from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import case, func

from .extensions import db
from .main import roles_required
from .models import Issue, IssueStatusHistory, RoomAssignment, User, utcnow

api_bp = Blueprint("api", __name__, url_prefix="/api")


def issue_json(issue):
    return {
        "id": issue.id,
        "title": issue.title,
        "description": issue.description,
        "status": issue.status,
        "created_at": issue.created_at.isoformat(),
        "room": {"building": issue.room.building, "number": issue.room.number},
        "student": {"id": issue.student.id, "name": issue.student.name},
        "technician": {"id": issue.technician.id, "name": issue.technician.name} if issue.technician else None,
    }


@api_bp.get("/issues")
@login_required
def get_issues():
    query = db.select(Issue).order_by(Issue.created_at.desc())
    if current_user.role == "student":
        query = query.where(Issue.student_id == current_user.id)
    elif current_user.role == "technician":
        query = query.where(Issue.technician_id == current_user.id)
    return jsonify([issue_json(issue) for issue in db.session.scalars(query).all()])


@api_bp.get("/issues/<int:issue_id>")
@login_required
def get_issue(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    if (current_user.role == "student" and issue.student_id != current_user.id) or (current_user.role == "technician" and issue.technician_id != current_user.id):
        return jsonify(error="Erişim reddedildi."), 403
    return jsonify(issue_json(issue))


@api_bp.post("/issues")
@roles_required("student")
def post_issue():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    if not 4 <= len(title) <= 120 or not 10 <= len(description) <= 3000:
        return jsonify(error="Başlık veya açıklama geçersiz."), 400
    assignment = db.session.scalar(db.select(RoomAssignment).where(RoomAssignment.student_id == current_user.id, RoomAssignment.end_date.is_(None)))
    if assignment is None:
        return jsonify(error="Etkin bir oda atamanız yok."), 409
    issue = Issue(student_id=current_user.id, room_id=assignment.room_id, title=title, description=description)
    db.session.add(issue)
    db.session.flush()
    db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=current_user.id, from_status=None, to_status="open", note="API üzerinden"))
    db.session.commit()
    return jsonify(issue_json(issue)), 201


@api_bp.patch("/issues/<int:issue_id>/status")
@login_required
def patch_issue_status(issue_id):
    issue = db.get_or_404(Issue, issue_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    allowed = current_user.role == "technician" and issue.technician_id == current_user.id and new_status in {"in_progress", "closed"}
    transitions = {"open": {"assigned"}, "assigned": {"open", "in_progress"}, "in_progress": {"assigned", "closed"}, "closed": {"assigned"}}
    if not allowed:
        return jsonify(error="Erişim reddedildi."), 403
    if new_status not in transitions.get(issue.status, set()):
        return jsonify(error="İstenen durum geçişine izin verilmiyor."), 409
    previous = issue.status
    issue.status = new_status
    if new_status == "closed":
        issue.closed_at = utcnow()
        issue.resolution_minutes = max(0, int((issue.closed_at - issue.created_at).total_seconds() // 60))
    else:
        issue.closed_at = None
        issue.resolution_minutes = None
    db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=current_user.id, from_status=previous, to_status=new_status, note="API üzerinden"))
    db.session.commit()
    return jsonify(issue_json(issue))


@api_bp.get("/reports/technicians")
@roles_required("manager")
def api_technician_report():
    rows = db.session.execute(
        db.select(User.id, User.name, func.count(Issue.id).label("total"),
                  func.sum(case((Issue.status == "closed", 1), else_=0)).label("closed"),
                  func.avg(Issue.resolution_minutes).label("avg_resolution_minutes"))
        .outerjoin(Issue, Issue.technician_id == User.id)
        .where(User.role == "technician")
        .group_by(User.id, User.name)
        .order_by(func.count(Issue.id).desc())
    ).all()
    return jsonify([{"technician_id": row.id, "name": row.name, "total": row.total, "closed": row.closed or 0,
                     "avg_resolution_minutes": round(row.avg_resolution_minutes, 1) if row.avg_resolution_minutes is not None else None} for row in rows])


@api_bp.errorhandler(403)
def api_forbidden(error):
    return jsonify(error="Erişim reddedildi."), 403


@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify(error="Kayıt bulunamadı."), 404
