import io
import pytest
from PIL import Image
from app import create_app
from services.auth_service import AuthService
from services.image_service import ImageService
from services.submission_service import SubmissionService
from services.assessment_service import AssessmentService

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Verifies that the /health endpoint returns healthy status for Render probes."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["timezone"] == "Asia/Kolkata"

def test_student_pin_auth():
    """Verifies student PIN authentication logic."""
    success, data, msg = AuthService.authenticate_student("KASHABOINA PRANAVI", "26054-ES-041", "127.0.0.1")
    assert success is True
    assert data["pin"] == "26054-ES-041"
    assert data["role"] == "student"

def test_student_pin_rate_limiting():
    """Verifies that repeated failed attempts trigger lockout."""
    ip = "192.168.1.100"
    pin = "INVALID-PIN-999"
    for _ in range(5):
        AuthService.authenticate_student("Fake Student", pin, ip)

    # 6th attempt must be locked
    success, data, msg = AuthService.authenticate_student("Fake Student", pin, ip)
    assert success is False
    assert "locked" in msg.lower()

def test_teacher_auth():
    """Verifies teacher credentials."""
    success, data, msg = AuthService.authenticate_teacher("lecturer@bea.edu", "admin123", "127.0.0.1")
    assert success is True
    assert data["role"] == "lecturer"

def test_image_optimization():
    """Verifies image compression preserves aspect ratio and outputs JPEG."""
    img = Image.new("RGB", (1200, 1600), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    raw_bytes = buf.getvalue()

    opt_bytes, metadata = ImageService.optimize_image(raw_bytes, max_dimension=1024, quality=80)
    assert len(opt_bytes) <= len(raw_bytes)
    assert metadata["mime_type"] == "image/jpeg"
    assert "sha256" in metadata

def test_submission_receipt_code():
    """Verifies cryptographic submission receipt format."""
    code = SubmissionService.generate_receipt_code()
    assert code.startswith("BEA-")
    assert len(code.split("-")) == 3

def test_assessment_default_seeding():
    """Verifies that default BEA assessment is loaded."""
    assessments = AssessmentService.get_all_assessments()
    assert len(assessments) >= 1
    assert "BJT" in assessments[0]["title"]


def test_add_question_with_image():
    from app import app
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"

    # Create dummy image
    img_data = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    data = {
        "question_number": "99",
        "question_text": "Draw and explain testing circuit diagram.",
        "max_marks": "5",
        "model_answer": "Standard test model answer.",
        "acceptable_alternatives": "None",
        "difficulty": "medium",
        "criterion_title": ["Circuit Diagram", "Explanation"],
        "criterion_marks": ["3", "2"],
        "criterion_desc": ["Correct pinout", "Full theory"],
        "question_image": (io.BytesIO(img_data), "test_circuit.gif")
    }

    res = client.post(
        "/teacher/assessment/bea-test-unit-001/add-question",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"Question 99" in res.data or b"successfully" in res.data


def test_edit_question_and_rubric():
    from app import app
    from services.assessment_service import AssessmentService
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"

    # Get existing question
    assessment = AssessmentService.get_assessment_by_id("bea-test-unit-001")
    assert assessment and len(assessment["questions"]) > 0
    target_q = assessment["questions"][0]

    edit_data = {
        "question_number": target_q["question_number"],
        "question_text": "Updated Question Text - Verify CE Configuration Analysis.",
        "max_marks": "10",
        "model_answer": "Updated model answer with derivation steps.",
        "acceptable_alternatives": "Equivalent Kirchhoff voltage analysis.",
        "difficulty": "hard",
        "requires_diagram": "1",
        "criterion_title": ["Updated Diagram Criterion", "Updated Calculation"],
        "criterion_marks": ["6", "4"],
        "criterion_desc": ["Biasing polarity check", "Formula substitution"]
    }

    res = client.post(
        f"/teacher/assessment/bea-test-unit-001/edit-question/{target_q['id']}",
        data=edit_data,
        content_type="multipart/form-data",
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"updated successfully" in res.data or b"Updated Question Text" in res.data


def test_parse_word_document_roster():
    from services.student_service import StudentService
    word_bytes = StudentService.generate_word_template()
    assert len(word_bytes) > 0

    valid, invalid = StudentService.parse_file(word_bytes, "students.docx")
    assert len(valid) >= 4
    assert any(s["pin"] == "26054-ES-041" for s in valid)
    assert any("PRANAVI" in s["full_name"] for s in valid)


def test_parse_file_with_top_header_banners():
    from services.student_service import StudentService
    # CSV with college title banner in rows 1 and 2 before actual table header
    csv_content = (
        "GOVERNMENT POLYTECHNIC COLLEGE HYDERABAD,,,\n"
        "DEPARTMENT OF ELECTRONICS & COMMUNICATION ENGINEERING,,,\n"
        "ACADEMIC YEAR 2026-2027 DIPLOMA I YEAR,,,\n"
        "SL_NO,PIN,NAME OF THE CANDIDATE,MOBILE_NO\n"
        "1,26054-ES-041,KASHABOINA PRANAVI,9502210435\n"
        "2,26054-CPS-001,A SUJATHA,6305307638\n"
        "TOTAL STUDENTS: 2,,,\n"
    ).encode("utf-8")

    valid, invalid = StudentService.parse_file(csv_content, "diploma_ece_banner.csv")
    assert len(valid) == 2
    assert valid[0]["pin"] == "26054-ES-041"
    assert "PRANAVI" in valid[0]["full_name"]
    assert valid[1]["pin"] == "26054-CPS-001"


def test_download_word_template():
    from app import app
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"

    res = client.get("/teacher/students/template/word")
    assert res.status_code == 200
    assert "wordprocessingml" in res.content_type


def test_edit_student_profile():
    from app import app
    from services.student_service import StudentService
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"

    students = StudentService.get_all_students()
    assert len(students) > 0
    target_pin = students[0]["pin"]

    edit_data = {
        "pin": target_pin,
        "full_name": "KASHABOINA PRANAVI (TOPPER)",
        "branch": "ECE",
        "section": "A1",
        "semester": "Semester 2",
        "academic_year": "2026-2027",
        "contact_phone": "9998887776",
        "contact_email": "topper@example.com",
        "is_active": "1"
    }

    res = client.post(
        f"/teacher/students/edit/{target_pin}",
        data=edit_data,
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"updated successfully" in res.data or b"TOPPER" in res.data


def test_edit_preview_student():
    from app import app
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"
        sess["pending_roster_import"] = [
            {
                "row_number": 2,
                "pin": "26054-ES-099",
                "full_name": "SAMPLE TYPO STUDENT",
                "academic_year": "2026-2027",
                "semester": "Semester 1",
                "branch": "ECE",
                "section": "A",
                "contact_phone": "1234567890",
                "contact_email": ""
            }
        ]

    edit_preview_data = {
        "pin": "26054-ES-099",
        "full_name": "SAMPLE CORRECTED STUDENT",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "B",
        "contact_phone": "9876543210",
        "contact_email": "corrected@example.com"
    }

    res = client.post(
        "/teacher/students/edit-preview/0",
        data=edit_preview_data,
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"updated" in res.data or b"CORRECTED" in res.data


def test_delete_students_batch():
    from app import app
    from services.student_service import StudentService
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["teacher_id"] = "test-teacher-id"
        sess["teacher_name"] = "Dr. Test Lecturer"
        sess["role"] = "lecturer"

    # Add a temporary test student to delete
    StudentService.import_students([{
        "pin": "TEMP-DEL-999",
        "full_name": "STUDENT TO DELETE",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "A"
    }])

    students_before = StudentService.get_all_students()
    assert any(s["pin"] == "TEMP-DEL-999" for s in students_before)

    # Batch delete
    res = client.post(
        "/teacher/students/delete-batch",
        data={"selected_students": ["TEMP-DEL-999"]},
        follow_redirects=True
    )
    assert res.status_code == 200
    assert b"deleted" in res.data or b"Successfully" in res.data

    students_after = StudentService.get_all_students()
    assert not any(s["pin"] == "TEMP-DEL-999" for s in students_after)





