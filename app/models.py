from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .i18n import translate


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


technician_skills = db.Table(
    "technician_skills",
    db.Column("technician_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("maintenance_skills.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'technician', 'manager')", name="ck_users_role"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    skills = db.relationship("MaintenanceSkill", secondary=technician_skills, back_populates="technicians")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_role(self):
        return translate({"student": "Öğrenci", "technician": "Teknisyen", "manager": "Yönetici"}.get(self.role, self.role))


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class Room(db.Model):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        UniqueConstraint("building", "number", name="uq_rooms_building_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(80), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer, nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    assignments = db.relationship("RoomAssignment", back_populates="room", lazy="select")
    issues = db.relationship("Issue", back_populates="room", lazy="select")

    @property
    def active_assignments(self):
        return [assignment for assignment in self.assignments if assignment.end_date is None]

    @property
    def occupants_count(self):
        return len(self.active_assignments)


class RoomAssignment(db.Model):
    __tablename__ = "room_assignments"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_assignment_dates"),
        Index("uq_one_active_assignment_per_student", "student_id", unique=True,
              sqlite_where=text("end_date IS NULL"), postgresql_where=text("end_date IS NULL")),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False, default=lambda: utcnow().date())
    end_date = db.Column(db.Date)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    student = db.relationship("User", foreign_keys=[student_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])
    room = db.relationship("Room", back_populates="assignments")


class MaintenanceSkill(db.Model):
    __tablename__ = "maintenance_skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    technicians = db.relationship("User", secondary=technician_skills, back_populates="skills")


class Issue(db.Model):
    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'assigned', 'in_progress', 'closed')", name="ck_issues_status"),
        CheckConstraint("resolution_minutes IS NULL OR resolution_minutes >= 0", name="ck_issue_resolution_nonnegative"),
        Index("ix_issues_status_created_at", "status", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    closed_at = db.Column(db.DateTime)
    resolution_minutes = db.Column(db.Integer)
    student = db.relationship("User", foreign_keys=[student_id])
    technician = db.relationship("User", foreign_keys=[technician_id])
    room = db.relationship("Room", back_populates="issues")
    history = db.relationship("IssueStatusHistory", back_populates="issue", cascade="all, delete-orphan", order_by="IssueStatusHistory.created_at")

    @property
    def display_status(self):
        return translate({"open": "Açık", "assigned": "Atandı", "in_progress": "Onarımda", "closed": "Kapalı"}.get(self.status, self.status))


class IssueStatusHistory(db.Model):
    __tablename__ = "issue_status_history"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    issue = db.relationship("Issue", back_populates="history")
    changed_by = db.relationship("User")
