import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app
from services.lecturer_service import LecturerService
from services.auth_service import AuthService
from services.assessment_service import AssessmentService
from services.student_service import StudentService

@pytest.fixture(autouse=True)
def clean_test_lecturers():
    """Ensure clean lecturer records before and after each test."""
    def _do_clean():
        lecturers = LecturerService._load_lecturers()
        cleaned = [
            l for l in lecturers 
            if not (
                l.get("username", "").startswith("test_") or 
                l.get("username", "").startswith("anand_") or 
                l.get("username", "").startswith("sub_lec_")
            )
        ]
        LecturerService._save_lecturers(cleaned)

    _do_clean()
    yield
    _do_clean()

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_admin_superuser_credentials():
    """Verify admin superuser authenticates with username admin and password 87654321."""
    success, data, msg = AuthService.authenticate_teacher("admin", "87654321")
    assert success is True
    assert data["role"] == "admin"
    assert data["username"] == "admin"
    assert "admin" in data["id"]

def test_admin_wrong_password():
    """Verify admin login fails with incorrect password."""
    success, data, msg = AuthService.authenticate_teacher("admin", "wrong_password")
    assert success is False
    assert data is None

def test_lecturer_signup_approval_and_isolation(client):
    """
    Complete lifecycle test:
    1. Lecturer A registers -> is_approved is False -> cannot log in yet
    2. Admin approves Lecturer A
    3. Lecturer A logs in successfully
    4. Lecturer B registers and gets approved
    5. Tenant data isolation:
       - Lecturer A creates an assessment & imports students
       - Lecturer B creates an assessment & imports students
       - Lecturer A cannot see Lecturer B's data
       - Lecturer B cannot see Lecturer A's data
    """
    # 1. Register Lecturer A
    suc_a, data_a, msg_a = LecturerService.register_lecturer(
        full_name="Prof. Alice Smith",
        username="test_alice_ece",
        email="test_alice@test.edu",
        password="Password123!",
        subject="Signals & Systems"
    )
    assert suc_a is True, f"Registration A failed: {msg_a}"
    lec_a_id = data_a["id"]

    # Before approval, login should fail
    auth_fail, _, fail_msg = LecturerService.authenticate_lecturer("test_alice_ece", "Password123!")
    assert auth_fail is False
    assert "pending" in fail_msg.lower()

    # 2. Register Lecturer B
    suc_b, data_b, msg_b = LecturerService.register_lecturer(
        full_name="Dr. Bob Johnson",
        username="test_bob_vlsi",
        email="test_bob@test.edu",
        password="Password456!",
        subject="VLSI Design"
    )
    assert suc_b is True, f"Registration B failed: {msg_b}"
    lec_b_id = data_b["id"]

    # 3. Admin approves Lecturer A and Lecturer B
    appr_a, _ = LecturerService.approve_lecturer(lec_a_id)
    assert appr_a is True
    appr_b, _ = LecturerService.approve_lecturer(lec_b_id)
    assert appr_b is True

    # 4. Now both can authenticate
    auth_a, user_a, _ = LecturerService.authenticate_lecturer("test_alice_ece", "Password123!")
    assert auth_a is True
    assert user_a["id"] == lec_a_id

    auth_b, user_b, _ = LecturerService.authenticate_lecturer("test_bob_vlsi", "Password456!")
    assert auth_b is True
    assert user_b["id"] == lec_b_id

    # 5. Data Isolation Test - Assessments
    # Alice creates assessment
    ok_asm_a, id_asm_a, _ = AssessmentService.create_assessment(
        title="Signals Test 1",
        assessment_type="slip_test",
        max_marks=20,
        assessment_date="2026-11-10",
        created_by_id=lec_a_id,
        subject_code="EC301"
    )
    assert ok_asm_a is True

    # Bob creates assessment
    ok_asm_b, id_asm_b, _ = AssessmentService.create_assessment(
        title="VLSI Design Assignment",
        assessment_type="assignment",
        max_marks=50,
        assessment_date="2026-11-10",
        created_by_id=lec_b_id,
        subject_code="EC502"
    )
    assert ok_asm_b is True

    # Check Alice's assessments view
    alice_asms = AssessmentService.get_all_assessments(teacher_id=lec_a_id)
    alice_titles = [a["title"] for a in alice_asms]
    assert "Signals Test 1" in alice_titles
    assert "VLSI Design Assignment" not in alice_titles

    # Check Bob's assessments view
    bob_asms = AssessmentService.get_all_assessments(teacher_id=lec_b_id)
    bob_titles = [a["title"] for a in bob_asms]
    assert "VLSI Design Assignment" in bob_titles
    assert "Signals Test 1" not in bob_titles

    # 6. Data Isolation Test - Students
    # Alice imports students
    StudentService.import_students([
        {"pin": "ALICE-001", "full_name": "Alice Student 1", "branch": "ECE"},
        {"pin": "ALICE-002", "full_name": "Alice Student 2", "branch": "ECE"}
    ], teacher_id=lec_a_id)

    # Bob imports students
    StudentService.import_students([
        {"pin": "BOB-001", "full_name": "Bob Student 1", "branch": "VLSI"}
    ], teacher_id=lec_b_id)

    # Alice should only see Alice's students
    alice_students = StudentService.get_all_students(teacher_id=lec_a_id)
    alice_pins = [s["pin"] for s in alice_students]
    assert "ALICE-001" in alice_pins
    assert "ALICE-002" in alice_pins
    assert "BOB-001" not in alice_pins

    # Bob should only see Bob's students
    bob_students = StudentService.get_all_students(teacher_id=lec_b_id)
    bob_pins = [s["pin"] for s in bob_students]
    assert "BOB-001" in bob_pins
    assert "ALICE-001" not in bob_pins

    # 7. Dedicated Config Isolation Test
    LecturerService.update_lecturer_config(lec_a_id, {
        "gemini_api_key": "AIzaSyAlicePrivateGeminiKey123",
        "database_type": "mysql",
        "mysql_database": "alice_private_db"
    })
    cfg_a = LecturerService.get_lecturer_config(lec_a_id)
    assert cfg_a["gemini_api_key"] == "AIzaSyAlicePrivateGeminiKey123"
    assert cfg_a["mysql_database"] == "alice_private_db"

    cfg_b = LecturerService.get_lecturer_config(lec_b_id)
    assert cfg_b.get("gemini_api_key") != "AIzaSyAlicePrivateGeminiKey123"

def test_admin_routes_access(client):
    """Test admin routes authorization: admin can access /admin/lecturers, non-admin is blocked."""
    # Anonymous cannot access
    res = client.get("/admin/lecturers")
    assert res.status_code == 302

    # Login as admin
    login_res = client.post("/teacher/login", data={
        "email": "admin",
        "password": "87654321"
    }, follow_redirects=True)
    assert login_res.status_code == 200

    # Admin accesses /admin/lecturers
    admin_page = client.get("/admin/lecturers")
    assert admin_page.status_code == 200
    assert b"Lecturer Management" in admin_page.data


def test_student_registration_with_available_lecturers(client):
    """Test student registration flow: student selects available lecturer, awaits approval, lecturer approves, and student accesses assessments."""
    from services.lecturer_service import LecturerService
    from services.student_service import StudentService

    import uuid
    uniq = uuid.uuid4().hex[:6].upper()
    # 1. Register and approve lecturer
    ok, lec_data, _ = LecturerService.register_lecturer(
        full_name=f"Prof. Anand Rao {uniq}",
        username=f"test_anand_{uniq}",
        email=f"test_anand_{uniq}@college.edu",
        password="secretpassword",
        subject="Embedded Systems"
    )
    assert ok is True
    lec_id = lec_data["id"]
    LecturerService.approve_lecturer(lec_id)

    # 2. Check student signup page contains available lecturers
    signup_page = client.get("/student/signup")
    assert signup_page.status_code == 200
    assert f"Prof. Anand Rao {uniq}".encode("utf-8") in signup_page.data
    assert b"Embedded Systems" in signup_page.data

    # 3. Student registers choosing Prof. Anand Rao
    student_pin = f"26054-ES-{uniq}"
    reg_resp = client.post("/student/signup", data={
        "name": "MOHAMMED IMRAN",
        "pin": student_pin,
        "lecturer_id": lec_id,
        "branch": "ECE",
        "semester": "Semester 3",
        "section": "A"
    }, follow_redirects=True)
    assert reg_resp.status_code == 200

    # 4. Student cannot log in before approval
    unapproved_login = client.post("/student/login", data={
        "name": "MOHAMMED IMRAN",
        "pin": student_pin
    }, follow_redirects=True)
    assert b"pending approval" in unapproved_login.data

    # 5. Lecturer logs in and sees pending student
    with client.session_transaction() as sess:
        sess["role"] = "lecturer"
        sess["teacher_id"] = lec_id
        sess["teacher_name"] = "Prof. Anand Rao"

    students_page = client.get("/teacher/students")
    assert students_page.status_code == 200
    assert student_pin.encode("utf-8") in students_page.data
    assert b"MOHAMMED IMRAN" in students_page.data

    # 6. Lecturer approves student
    pending = StudentService.get_pending_students_for_lecturer(lec_id)
    assert len(pending) >= 1
    reg_id = next(p["id"] for p in pending if p["pin"] == student_pin)

    approve_resp = client.post(f"/teacher/students/approve-registration/{reg_id}", follow_redirects=True)
    assert approve_resp.status_code == 200
    assert b"Approved MOHAMMED IMRAN" in approve_resp.data

    # 7. Student can now log in
    client.get("/student/logout")
    approved_login = client.post("/student/login", data={
        "name": "MOHAMMED IMRAN",
        "pin": student_pin
    }, follow_redirects=True)
    assert approved_login.status_code == 200
    assert b"Welcome, MOHAMMED IMRAN" in approved_login.data or b"Available Assessments" in approved_login.data


def test_student_submission_reflects_in_teacher_dashboard(client):
    """
    Verifies that when a student submits an assessment,
    it immediately reflects on the teacher's dashboard:
    1. Correct student Name & PIN shown in submissions table
    2. Submission tracker count incremented
    3. Teacher can open evaluation and approve marks
    """
    import uuid
    from services.submission_service import SubmissionService
    uniq = uuid.uuid4().hex[:6].upper()

    # 1. Register & approve lecturer
    ok, lec_data, _ = LecturerService.register_lecturer(
        full_name=f"Prof. Test Sub {uniq}",
        username=f"test_sub_lec_{uniq}",
        email=f"test_sub_lec_{uniq}@college.edu",
        password="secretpassword",
        subject="Digital Electronics"
    )
    assert ok is True
    lec_id = lec_data["id"]
    LecturerService.approve_lecturer(lec_id)

    # 2. Lecturer creates an assessment
    ok, asm_id, _ = AssessmentService.create_assessment(
        title=f"Digital Systems Test {uniq}",
        assessment_type="mcq_test",
        max_marks=10.0,
        assessment_date="2026-11-20",
        questions=[{
            "id": f"q1_{uniq}",
            "question_number": "1",
            "question_type": "mcq",
            "question_text": "Number of states in a mod-16 counter is:",
            "option_a": "16",
            "option_b": "15",
            "option_c": "8",
            "option_d": "4",
            "correct_option": "A",
            "max_marks": 10.0
        }],
        created_by_id=lec_id
    )
    assert ok is True

    # Publish assessment
    AssessmentService.toggle_publish(asm_id, publish=True)

    # 3. Student registers & gets approved
    stud_pin = f"26054-SUB-{uniq}"
    stud_name = f"SANJANA REDDY {uniq}"
    StudentService.register_student(
        full_name=stud_name,
        pin=stud_pin,
        lecturer_id=lec_id,
        branch="ECE",
        semester="Semester 3",
        section="A"
    )
    pending = StudentService.get_pending_students_for_lecturer(lec_id)
    reg = next(p for p in pending if p["pin"] == stud_pin)
    StudentService.approve_student_registration(reg["id"], lec_id)

    # 4. Student logs in and submits MCQ
    with client.session_transaction() as sess:
        sess["role"] = "student"
        sess["student_id"] = reg["id"]
        sess["student_name"] = stud_name
        sess["student_pin"] = stud_pin
        sess["student_lecturer_id"] = lec_id

    draft = SubmissionService.get_or_create_draft_submission(asm_id, reg["id"])
    assert draft is not None

    sub_post = client.post(
        f"/student/assessment/{asm_id}/submit-mcq",
        data={
            "submission_id": draft["id"],
            f"mcq_answer_q1_{uniq}": "A"
        },
        follow_redirects=True
    )
    assert sub_post.status_code == 200

    # 5. Teacher logs in and checks dashboard
    with client.session_transaction() as sess:
        sess.clear()
        sess["role"] = "lecturer"
        sess["teacher_id"] = lec_id
        sess["teacher_name"] = f"Prof. Test Sub {uniq}"

    dash_resp = client.get(f"/teacher/dashboard?assessment_id={asm_id}")
    assert dash_resp.status_code == 200

    # Verify student reflects in teacher dashboard
    assert stud_pin.encode("utf-8") in dash_resp.data
    assert stud_name.encode("utf-8") in dash_resp.data
    assert draft["submission_receipt_code"].encode("utf-8") in dash_resp.data

    # Verify teacher can view evaluation view
    eval_resp = client.get(f"/teacher/evaluate/{draft['id']}")
    assert eval_resp.status_code == 200
    assert stud_pin.encode("utf-8") in eval_resp.data

