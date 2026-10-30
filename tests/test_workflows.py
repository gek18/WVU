import io
import shutil
import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Issue, IssueRating, IssueStatusHistory, MaintenanceSkill, Room, RoomAssignment, User


class ApplicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.upload_dir = Path.cwd() / "instance" / "test-uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": str(self.upload_dir),
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.manager = self.make_user("manager@example.test", "manager")
        self.student = self.make_user("student@example.test", "student")
        self.other_student = self.make_user("other@example.test", "student")
        self.technician = self.make_user("tech@example.test", "technician")
        self.room = Room(building="A Blok", number="101", floor=1, capacity=1)
        db.session.add(self.room)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        shutil.rmtree(self.upload_dir, ignore_errors=True)

    def make_user(self, email, role):
        user = User(name=email.split("@")[0].title(), email=email, role=role)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, email):
        role = {
            "manager@example.test": "manager",
            "student@example.test": "student",
            "other@example.test": "student",
            "tech@example.test": "technician",
        }.get(email, "student")
        response = self.client.post(f"/login/{role}", data={"email": email, "password": "password123"})
        self.assertEqual(response.status_code, 302)
        return response

    def assign_room(self, student=None):
        student = student or self.student
        db.session.add(RoomAssignment(student_id=student.id, room_id=self.room.id, assigned_by_id=self.manager.id))
        db.session.commit()

    def make_issue(self, student=None, room=None, **kwargs):
        issue = Issue(
            student_id=(student or self.student).id,
            room_id=(room or self.room).id,
            title=kwargs.get("title", "Broken sink"),
            description=kwargs.get("description", "Water is leaking under the sink."),
            status=kwargs.get("status", "open"),
            technician_id=kwargs.get("technician_id"),
        )
        db.session.add(issue)
        db.session.flush()
        db.session.add(IssueStatusHistory(issue_id=issue.id, changed_by_id=self.student.id, to_status="open", note="Created"))
        db.session.commit()
        return issue

    def test_public_pages_and_turkish_shell_render(self):
        for path, expected in [
            ("/", "Öğrenci yurdu"),
            ("/login", "Giriş türünü seçin"),
            ("/register", "Öğrenci hesabı oluştur"),
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'<html lang="tr" dir="ltr">', response.data)
                self.assertIn(expected.encode(), response.data)
        css = self.client.get("/static/style.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn(b"prefers-reduced-motion", css.data)
        css.close()
        self.assertEqual(self.client.get("/missing-page").status_code, 404)

    def test_language_switch_persists_and_sets_rtl_for_arabic(self):
        response = self.client.get("/language/en", headers={"Referer": "http://localhost/"})
        self.assertEqual(response.status_code, 302)
        english = self.client.get("/")
        self.assertIn(b'<html lang="en" dir="ltr">', english.data)
        self.assertIn(b"Your dorm request", english.data)
        self.assertIn(b"Room plan", english.data)

        response = self.client.get("/language/ar", headers={"Referer": "http://localhost/"})
        self.assertEqual(response.status_code, 302)
        arabic = self.client.get("/")
        self.assertIn(b'<html lang="ar" dir="rtl">', arabic.data)
        self.assertIn("السكن".encode(), arabic.data)
        self.assertIn(b"bootstrap.rtl.min.css", arabic.data)
        register = self.client.get("/register")
        self.assertIn("إنشاء حساب".encode(), register.data)
        self.assertNotIn(b"olu\xc5\x9ftur", register.data)

        self.assertEqual(self.client.get("/language/fr").status_code, 404)

    def test_historical_assignment_note_uses_selected_language(self):
        issue = self.make_issue(status="assigned", technician_id=self.technician.id)
        db.session.add(IssueStatusHistory(
            issue_id=issue.id,
            changed_by_id=self.manager.id,
            from_status="open",
            to_status="assigned",
            note=f"Şu teknisyene atandı: {self.technician.name}",
        ))
        db.session.commit()
        self.login("manager@example.test")
        with self.client.session_transaction() as session:
            session["language"] = "ar"

        response = self.client.get(f"/issues/{issue.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"أُسند إلى الفني: {self.technician.name}".encode(), response.data)
        self.assertNotIn("Şu teknisyene atandı".encode(), response.data)

    def test_manager_and_technician_dashboards_render(self):
        self.login("manager@example.test")
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.assertIn("Odaları ve ekibi yönet".encode(), self.client.get("/dashboard").data)
        self.client.post("/logout")
        self.login("tech@example.test")
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.assertIn("İş listemi aç".encode(), self.client.get("/dashboard").data)

    def test_registration_login_and_role_access(self):
        response = self.client.post("/register", data={
            "name": "New Student", "email": "new@example.test", "password": "password123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.client.post("/logout")
        self.login("student@example.test")
        self.assertEqual(self.client.get("/rooms").status_code, 403)

    def test_role_login_pages_enforce_account_role(self):
        chooser = self.client.get("/login")
        self.assertEqual(chooser.status_code, 200)
        for role in ("student", "technician", "manager"):
            with self.subTest(role=role):
                response = self.client.get(f"/login/{role}")
                self.assertEqual(response.status_code, 200)
                self.assertIn('name="email"'.encode(), response.data)
        mismatch = self.client.post("/login/student", data={
            "email": "manager@example.test", "password": "password123",
        })
        self.assertEqual(mismatch.status_code, 401)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertEqual(self.client.post("/login/manager", data={
            "email": "manager@example.test", "password": "password123",
        }).status_code, 302)

    def test_student_rates_assigned_technician_after_issue_is_closed(self):
        open_issue = self.make_issue(technician_id=self.technician.id)
        closed_issue = self.make_issue(technician_id=self.technician.id, status="closed")
        self.login("student@example.test")

        self.assertEqual(self.client.post(f"/issues/{open_issue.id}/rating", data={"stars": "5"}).status_code, 302)
        self.assertIsNone(db.session.get(IssueRating, open_issue.id))
        detail = self.client.get(f"/issues/{closed_issue.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b'name="stars"', detail.data)
        self.assertEqual(self.client.post(f"/issues/{closed_issue.id}/rating", data={"stars": "6"}).status_code, 302)
        self.assertIsNone(db.session.get(IssueRating, closed_issue.id))
        self.assertEqual(self.client.post(f"/issues/{closed_issue.id}/rating", data={
            "stars": "4", "comment": "x" * 1001,
        }).status_code, 302)
        self.assertIsNone(db.session.get(IssueRating, closed_issue.id))
        self.assertEqual(self.client.post(f"/issues/{closed_issue.id}/rating", data={
            "stars": "5", "comment": "Great work",
        }).status_code, 302)
        rating = db.session.get(IssueRating, closed_issue.id)
        self.assertEqual(rating.stars, 5)
        self.assertEqual(rating.technician_id, self.technician.id)
        self.assertEqual(rating.comment, "Great work")
        self.assertEqual(self.client.post(f"/issues/{closed_issue.id}/rating", data={"stars": "4"}).status_code, 302)
        db.session.refresh(rating)
        self.assertEqual(rating.stars, 5)

        self.client.post("/logout")
        self.login("other@example.test")
        self.assertEqual(self.client.post(f"/issues/{closed_issue.id}/rating", data={"stars": "3"}).status_code, 403)
        self.client.post("/logout")
        self.login("manager@example.test")
        report = self.client.get("/reports")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"5.0/5", report.data)
        self.assertIn("1 değerlendirme".encode(), report.data)

    def test_room_management_capacity_and_assignment_end(self):
        self.login("manager@example.test")
        self.assertEqual(self.client.post("/rooms/new", data={
            "building": "A Blok", "number": "101", "floor": 1, "capacity": 1,
        }).status_code, 302)
        self.assertEqual(Room.query.count(), 1)  # Duplicate room is rejected.
        self.assertEqual(self.client.post("/rooms/new", data={
            "building": "B Blok", "number": "201", "floor": 2, "capacity": 2,
        }).status_code, 302)
        spare_room = Room.query.filter_by(number="201").one()
        self.assertEqual(self.client.post(f"/rooms/{spare_room.id}/edit", data={
            "building": "B Blok", "number": "202", "floor": 2, "capacity": 2,
        }).status_code, 302)
        self.assertEqual(self.client.post(f"/rooms/{spare_room.id}/delete").status_code, 302)
        self.assertIsNone(db.session.get(Room, spare_room.id))
        response = self.client.post(f"/rooms/{self.room.id}/assign", data={"student_id": self.student.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RoomAssignment.query.filter_by(end_date=None).count(), 1)
        self.assertEqual(self.client.post(f"/rooms/{self.room.id}/assign", data={"student_id": self.other_student.id}).status_code, 302)
        self.assertEqual(RoomAssignment.query.filter_by(end_date=None).count(), 1)  # Room is full.

    def test_manager_can_create_team_member_and_skill(self):
        self.login("manager@example.test")
        response = self.client.post("/team/new", data={
            "name": "Tech One", "email": "created-tech@example.test", "password": "password123",
            "role": "technician", "skills": "Electrical, Plumbing",
        })
        self.assertEqual(response.status_code, 302)
        created = User.query.filter_by(email="created-tech@example.test").one()
        self.assertEqual(created.role, "technician")
        self.assertEqual({skill.name for skill in created.skills}, {"Electrical", "Plumbing"})

    def test_manager_can_end_room_assignment(self):
        self.assign_room()
        assignment = RoomAssignment.query.filter_by(student_id=self.student.id).one()
        self.login("manager@example.test")
        response = self.client.post(f"/assignments/{assignment.id}/end")
        self.assertEqual(response.status_code, 302)
        db.session.refresh(assignment)
        self.assertIsNotNone(assignment.end_date)

    def test_student_issue_create_update_photo_and_ownership(self):
        self.assign_room()
        self.login("student@example.test")
        response = self.client.post("/issues/new", data={
            "title": "Broken sink", "description": "Water is leaking under the sink.",
            "photo": (io.BytesIO(b"\x89PNG\r\n\x1a\n"), "sink.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        issue = Issue.query.one()
        self.assertEqual(issue.status, "open")
        self.assertTrue((self.upload_dir / issue.photo_filename).is_file())
        photo_response = self.client.get(f"/issues/{issue.id}/photo")
        self.assertEqual(photo_response.status_code, 200)
        photo_response.close()
        self.assertEqual(self.client.get(f"/issues/{issue.id}/edit").status_code, 200)
        self.assertEqual(self.client.post(f"/issues/{issue.id}/edit", data={
            "title": "Updated sink", "description": "The leak is getting worse each day.",
        }).status_code, 302)
        self.client.post("/logout")
        self.login("other@example.test")
        self.assertEqual(self.client.get(f"/issues/{issue.id}").status_code, 403)
        self.assertEqual(self.client.get(f"/issues/{issue.id}/photo").status_code, 403)

    def test_skill_assignment_technician_workflow_and_report(self):
        skill = MaintenanceSkill(name="Plumbing")
        self.technician.skills.append(skill)
        db.session.add(skill)
        db.session.commit()
        issue = self.make_issue()
        self.login("manager@example.test")
        self.assertEqual(self.client.get("/rooms").status_code, 200)
        self.assertEqual(self.client.get("/reports").status_code, 200)
        response = self.client.post(f"/issues/{issue.id}/assign", data={
            "technician_id": self.technician.id, "skill_id": skill.id,
        })
        self.assertEqual(response.status_code, 302)
        self.client.post("/logout")
        self.login("tech@example.test")
        self.assertEqual(self.client.get(f"/issues/{issue.id}").status_code, 200)
        self.assertEqual(self.client.post(f"/issues/{issue.id}/status", data={"status": "in_progress"}).status_code, 302)
        self.assertEqual(self.client.post(f"/issues/{issue.id}/status", data={"status": "closed", "note": "Fixed"}).status_code, 302)
        db.session.refresh(issue)
        self.assertEqual(issue.status, "closed")
        self.assertIsNotNone(issue.closed_at)
        self.assertGreaterEqual(issue.resolution_minutes, 0)
        self.assertEqual(len(issue.history), 4)
        self.client.post("/logout")
        self.login("manager@example.test")
        report = self.client.get("/api/reports/technicians")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json[0]["closed"], 1)

    def test_rest_api_authorization_and_validation(self):
        self.assign_room()
        self.assertEqual(self.client.get("/api/issues").status_code, 401)
        self.login("student@example.test")
        self.assertEqual(self.client.post("/api/issues", json={"title": "bad", "description": "short"}).status_code, 400)
        created = self.client.post("/api/issues", json={
            "title": "Broken sink", "description": "Water is leaking under the sink.",
        })
        self.assertEqual(created.status_code, 201)
        issue_id = created.json["id"]
        self.assertEqual(self.client.get(f"/api/issues/{issue_id}").status_code, 200)
        self.assertEqual(self.client.get("/api/reports/technicians").status_code, 403)

    def test_rest_api_status_transition(self):
        issue = self.make_issue(technician_id=self.technician.id, status="assigned")
        self.login("tech@example.test")
        started = self.client.patch(f"/api/issues/{issue.id}/status", json={"status": "in_progress"})
        self.assertEqual(started.status_code, 200)
        closed = self.client.patch(f"/api/issues/{issue.id}/status", json={"status": "closed"})
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json["status"], "closed")

    def test_csrf_rejects_missing_token(self):
        csrf_app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "UPLOAD_FOLDER": str(self.upload_dir),
        })
        csrf_client = csrf_app.test_client()
        response = csrf_client.post("/login", data={"email": "nobody@example.test", "password": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Form güvenlik kontrolünden geçemedi".encode(), response.data)


if __name__ == "__main__":
    unittest.main()
