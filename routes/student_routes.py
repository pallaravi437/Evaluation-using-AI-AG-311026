import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.auth_service import AuthService
from services.assessment_service import AssessmentService
from services.submission_service import SubmissionService
from services.image_service import ImageService
from database.db_manager import db_manager

logger = logging.getLogger("bea.student_routes")
student_bp = Blueprint("student", __name__, url_prefix="/student")

def student_required(f):
    """Decorator to enforce student session."""
    def wrapper(*args, **kwargs):
        if session.get("role") != "student" or not session.get("student_id"):
            flash("Please enter your Name and PIN to log in.", "warning")
            return redirect(url_for("student.login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@student_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()
        client_ip = request.remote_addr or ""

        success, student_data, message = AuthService.authenticate_student(name, pin, client_ip)
        if success and student_data:
            session.clear()
            session["role"] = "student"
            session["student_id"] = student_data["id"]
            session["student_name"] = student_data["full_name"]
            session["student_pin"] = student_data["pin"]
            session["student_branch"] = student_data.get("branch", "ECE")
            session.permanent = True
            flash(f"Welcome, {student_data['full_name']}!", "success")
            return redirect(url_for("student.dashboard"))
        else:
            flash(message, "danger")

    recent_submissions = SubmissionService.get_recent_submissions()
    return render_template("login.html", active_tab="student", recent_submissions=recent_submissions)

@student_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("student.login"))

@student_bp.route("/dashboard")
@student_required
def dashboard():
    assessments = AssessmentService.get_all_assessments()
    student_id = session.get("student_id")
    
    # Attach submission status for this student
    for asm in assessments:
        draft = SubmissionService.get_or_create_draft_submission(asm["id"], student_id)
        asm["user_submission_status"] = draft.get("status", "not_started")
        asm["user_submission_id"] = draft.get("id")
        asm["is_locked"] = draft.get("is_locked", False)
        asm["receipt_code"] = draft.get("submission_receipt_code")

    return render_template("student/dashboard.html", assessments=assessments)

@student_bp.route("/assessment/<assessment_id>/upload")
@student_required
def upload_answers(assessment_id):
    student_id = session.get("student_id")
    assessment = AssessmentService.get_assessment_by_id(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("student.dashboard"))

    submission = SubmissionService.get_or_create_draft_submission(assessment_id, student_id)
    if submission.get("is_locked", False):
        flash("This assessment was already submitted and locked. You can view your receipt or results.", "info")
        return redirect(url_for("student.submission_receipt", submission_id=submission["id"]))

    pages = SubmissionService.get_pages_for_submission(submission["id"])
    
    # Organize pages by question_id
    question_pages = {}
    for p in pages:
        qid = p["question_id"]
        question_pages.setdefault(qid, []).append(p)

    return render_template(
        "student/upload.html",
        assessment=assessment,
        submission=submission,
        question_pages=question_pages
    )

@student_bp.route("/api/upload-page", methods=["POST"])
@student_required
def api_upload_page():
    """AJAX endpoint for question-wise script page upload & optimization."""
    submission_id = request.form.get("submission_id")
    question_id = request.form.get("question_id")
    page_number = int(request.form.get("page_number", 1))
    file = request.files.get("file")

    if not file or not submission_id or not question_id:
        return jsonify({"success": False, "message": "Missing file or required parameters."}), 400

    # Parse optional crop bounds from client Canvas
    crop_data = None
    if "crop_x" in request.form and "crop_w" in request.form:
        try:
            crop_data = {
                "x": float(request.form.get("crop_x")),
                "y": float(request.form.get("crop_y")),
                "width": float(request.form.get("crop_w")),
                "height": float(request.form.get("crop_h"))
            }
        except ValueError:
            crop_data = None

    valid, opt_bytes, metadata, msg = ImageService.validate_and_process_upload(file, crop_data)
    if not valid or not opt_bytes:
        return jsonify({"success": False, "message": msg}), 400

    mime_type = metadata.get("mime_type", "image/jpeg")
    saved, path, save_msg = SubmissionService.save_answer_page(
        submission_id=submission_id,
        question_id=question_id,
        page_number=page_number,
        file_bytes=opt_bytes,
        mime_type=mime_type,
        metadata=metadata
    )

    if not saved:
        return jsonify({"success": False, "message": save_msg}), 400

    return jsonify({
        "success": True,
        "message": "Page saved and compressed successfully.",
        "metadata": metadata,
        "storage_path": path,
        "question_id": question_id,
        "page_number": page_number
    })

@student_bp.route("/submit", methods=["POST"])
@student_required
def finalize_submission():
    submission_id = request.form.get("submission_id")
    client_ip = request.remote_addr or ""
    user_agent = request.headers.get("User-Agent", "")

    success, sub, msg = SubmissionService.finalize_submission(submission_id, client_ip, user_agent)
    if success and sub:
        flash("Your assessment answer script has been officially submitted!", "success")
        return redirect(url_for("student.submission_receipt", submission_id=sub["id"]))
    else:
        flash(f"Submission error: {msg}", "danger")
        return redirect(url_for("student.dashboard"))

@student_bp.route("/receipt/<submission_id>")
@student_required
def submission_receipt(submission_id):
    student_id = session.get("student_id")
    sub = SubmissionService.get_submission_by_id(submission_id)
    if not sub:
        flash("Submission record not found.", "danger")
        return redirect(url_for("student.dashboard"))

    # Security: Verify ownership
    if sub.get("student_id") != student_id:
        flash("Unauthorized access. You can only view your own submission receipt.", "danger")
        return redirect(url_for("student.dashboard"))

    pages = SubmissionService.get_pages_for_submission(submission_id)
    return render_template("student/submission_receipt.html", submission=sub, pages=pages)

@student_bp.route("/results/<assessment_id>")
@student_required
def results(assessment_id):
    student_id = session.get("student_id")
    assessment = AssessmentService.get_assessment_by_id(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("student.dashboard"))

    # Fetch this student's submission
    sub = SubmissionService.get_or_create_draft_submission(assessment_id, student_id)
    
    # Fetch questions and approved evaluations
    supabase = db_manager.get_supabase(use_service_role=True)
    evaluations = {}
    rechecks = {}

    if supabase:
        try:
            ev_res = supabase.table("question_evaluations").select("*").eq("submission_id", sub["id"]).execute()
            for ev in (ev_res.data or []):
                evaluations[ev["question_id"]] = ev

            rc_res = supabase.table("recheck_requests").select("*").eq("submission_id", sub["id"]).execute()
            for rc in (rc_res.data or []):
                rechecks[rc["question_id"]] = rc
        except Exception as e:
            logger.error(f"Error fetching student results: {e}")

    return render_template(
        "student/results.html",
        assessment=assessment,
        submission=sub,
        evaluations=evaluations,
        rechecks=rechecks
    )

@student_bp.route("/recheck", methods=["POST"])
@student_required
def submit_recheck():
    """Allows student to raise an objection on a specific question evaluation."""
    submission_id = request.form.get("submission_id")
    question_id = request.form.get("question_id")
    student_reason = request.form.get("reason", "").strip()
    student_id = session.get("student_id")

    if not student_reason or len(student_reason) < 10:
        flash("Please provide a detailed explanation of your objection (at least 10 characters).", "warning")
        return redirect(request.referrer or url_for("student.dashboard"))

    supabase = db_manager.get_supabase(use_service_role=True)
    if supabase:
        try:
            # Check question evaluation
            ev_res = supabase.table("question_evaluations").select("id, approved_marks, ai_marks_awarded").eq(
                "submission_id", submission_id
            ).eq("question_id", question_id).execute()

            if not ev_res.data:
                flash("Evaluation record not found for this question.", "danger")
                return redirect(request.referrer)

            ev = ev_res.data[0]
            current_marks = ev.get("approved_marks") or ev.get("ai_marks_awarded") or 0.0

            recheck_record = {
                "submission_id": submission_id,
                "question_id": question_id,
                "question_evaluation_id": ev["id"],
                "student_id": student_id,
                "student_objection_reason": student_reason,
                "marks_before_recheck": current_marks,
                "status": "pending"
            }

            supabase.table("recheck_requests").upsert(
                recheck_record,
                on_conflict="submission_id,question_id"
            ).execute()

            flash("Your recheck objection has been submitted to the lecturer for review.", "success")
        except Exception as e:
            logger.error(f"Error submitting recheck: {e}")
            flash(f"Error submitting recheck: {str(e)}", "danger")

    return redirect(request.referrer or url_for("student.dashboard"))
