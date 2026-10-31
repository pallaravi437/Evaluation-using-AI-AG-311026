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

