import os
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import io
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from services.auth_service import AuthService
from services.assessment_service import AssessmentService
from services.submission_service import SubmissionService
from services.student_service import StudentService
from services.image_service import ImageService
from services.ai_service import AIService
from services.analytics_service import AnalyticsService
from database.db_manager import db_manager
from config import Config

logger = logging.getLogger("bea.teacher_routes")
teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

def teacher_required(f):
    """Enforces active teacher session."""
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("lecturer", "admin") or not session.get("teacher_id"):
            flash("Please sign in with lecturer credentials.", "warning")
            return redirect(url_for("teacher.login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@teacher_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        client_ip = request.remote_addr or ""

        success, teacher_data, message = AuthService.authenticate_teacher(email, password, client_ip)
        if success and teacher_data:
            session.clear()
            session["role"] = teacher_data.get("role", "lecturer")
            session["teacher_id"] = teacher_data["id"]
            session["teacher_name"] = teacher_data["full_name"]
            session["teacher_email"] = teacher_data["email"]
            session.permanent = True
            flash(f"Welcome back, {teacher_data['full_name']}!", "success")
            return redirect(url_for("teacher.dashboard"))
        else:
            flash(message, "danger")

    recent_submissions = SubmissionService.get_recent_submissions()
    return render_template("login.html", active_tab="teacher", recent_submissions=recent_submissions)

@teacher_bp.route("/logout")
def logout():
    session.clear()
    flash("Lecturer session ended.", "info")
    return redirect(url_for("teacher.login"))

@teacher_bp.route("/dashboard")
@teacher_required
def dashboard():
    """
    Core Teacher Dashboard with 3 primary operational pillars:
    1. Set Questions with Marks
    2. Evaluate Submissions
    3. Result Analysis Dashboard
    """
    assessments = AssessmentService.get_all_assessments()
    students = StudentService.get_all_students()
    
    # Calculate overview metrics across assessments
    total_students = len(students) or 60  # Default to ~60 Diploma batch if DB empty
    selected_asm_id = request.args.get("assessment_id") or (assessments[0]["id"] if assessments else None)
    
    # Compute submission tracker statistics for the selected assessment
    tracker = {
        "total_students": total_students,
        "submitted_count": 0,
        "not_submitted_count": total_students,
        "submission_percentage": 0.0,
        "evaluated_count": 0,
        "approved_count": 0
    }

    submissions_list = []
    selected_assessment = None

    if selected_asm_id:
        selected_assessment = AssessmentService.get_assessment_by_id(selected_asm_id)
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("answer_submissions").select(
                    "*, students(id, pin, full_name, branch, section)"
                ).eq("assessment_id", selected_asm_id).order("submitted_at", desc=True).execute()
                submissions_list = res.data or []
            except Exception as e:
                logger.error(f"Error fetching submissions: {e}")

        # Format timestamps to Asia/Kolkata
        sub_count = len([s for s in submissions_list if s.get("status") in ("submitted", "evaluated", "approved")])
        tracker["submitted_count"] = sub_count
        tracker["not_submitted_count"] = max(0, total_students - sub_count)
        tracker["submission_percentage"] = round((sub_count / max(1, total_students)) * 100, 1)
        tracker["evaluated_count"] = len([s for s in submissions_list if s.get("status") in ("evaluated", "approved")])
        tracker["approved_count"] = len([s for s in submissions_list if s.get("status") == "approved"])

        for s in submissions_list:
            if s.get("submitted_at"):
                try:
                    dt = datetime.fromisoformat(s["submitted_at"].replace("Z", "+00:00"))
                    s["submitted_at_formatted"] = dt.astimezone(Config.TIMEZONE).strftime("%d %b %Y, %I:%M %p")
                except Exception:
                    s["submitted_at_formatted"] = s["submitted_at"]

    return render_template(
        "teacher/dashboard.html",
        assessments=assessments,
        selected_assessment=selected_assessment,
        tracker=tracker,
        submissions=submissions_list,
        total_students=total_students
    )

@teacher_bp.route("/assessments", methods=["GET", "POST"])
@teacher_required
def manage_assessments():
    """Create and manage assessments and questions."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        assessment_type = request.form.get("assessment_type", "slip_test")
        max_marks = float(request.form.get("max_marks", 20.0))
        assessment_date = request.form.get("assessment_date", "")
        instructions = request.form.get("instructions", "")
        pass_pct = float(request.form.get("pass_percentage", 35.0))
        teacher_id = session.get("teacher_id")

        success, new_id, msg = AssessmentService.create_assessment(
            title=title,
            assessment_type=assessment_type,
            max_marks=max_marks,
            assessment_date=assessment_date,
            instructions=instructions,
            pass_percentage=pass_pct,
            created_by_id=teacher_id
        )
        if success:
            flash("Assessment created successfully!", "success")
            return redirect(url_for("teacher.dashboard", assessment_id=new_id))
        else:
            flash(f"Failed to create assessment: {msg}", "danger")

    assessments = AssessmentService.get_all_assessments()
    return render_template("teacher/assessments.html", assessments=assessments)

@teacher_bp.route("/assessment/<assessment_id>/questions")
@teacher_required
def manage_questions(assessment_id):
    """View and manage questions and marking rubrics for an assessment."""
    assessment = AssessmentService.get_assessment_by_id(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("teacher.manage_assessments"))
    return render_template("teacher/manage_questions.html", assessment=assessment)

@teacher_bp.route("/assessment/<assessment_id>/add-question", methods=["POST"])
@teacher_required
def add_question(assessment_id):
    """Adds a new question with marking criteria to an assessment."""
    q_num = request.form.get("question_number", "").strip()
    q_text = request.form.get("question_text", "").strip()
    max_m = float(request.form.get("max_marks", 5.0))
    model_ans = request.form.get("model_answer", "").strip()
    alternatives = request.form.get("acceptable_alternatives", "").strip()
    difficulty = request.form.get("difficulty", "medium")
    req_diagram = bool(request.form.get("requires_diagram"))
    req_numerical = bool(request.form.get("requires_numerical"))

    # Extract dynamic rubric criteria
    criteria = []
    titles = request.form.getlist("criterion_title[]")
    marks = request.form.getlist("criterion_marks[]")
    descs = request.form.getlist("criterion_desc[]")

    for i in range(len(titles)):
        t = titles[i].strip()
        if t:
            try:
                m = float(marks[i])
            except (IndexError, ValueError):
                m = 1.0
            d = descs[i].strip() if i < len(descs) else ""
            criteria.append({"criterion_title": t, "max_marks": m, "description": d})

    # Handle optional question reference image/circuit upload
    img_file = request.files.get("question_image")
    image_url = ""
    if img_file and img_file.filename:
        valid, opt_bytes, metadata, _ = ImageService.validate_and_process_upload(img_file)
        if valid and opt_bytes:
            safe_num = "".join(c for c in q_num if c.isalnum()) or "1"
            mime = (metadata or {}).get("mime_type", "image/jpeg")
            ext = ".svg" if mime == "image/svg+xml" else (".png" if mime == "image/png" else ".jpg")
            filename = f"q_{assessment_id[:8]}_{safe_num}_{int(datetime.now().timestamp())}{ext}"
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "questions")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(opt_bytes)
            image_url = f"/static/uploads/questions/{filename}"

    q_data = {
        "question_number": q_num,
        "question_text": q_text,
        "max_marks": max_m,
        "model_answer": model_ans,
        "acceptable_alternatives": alternatives,
        "difficulty": difficulty,
        "requires_diagram": req_diagram,
        "requires_numerical": req_numerical,
        "question_image_url": image_url,
        "criteria": criteria
    }

    success, q_id, msg = AssessmentService.add_question(assessment_id, q_data)
    if success:
        flash(f"Question {q_num} and its marking rubric added successfully!", "success")
    else:
        flash(f"Failed to add question: {msg}", "danger")

    return redirect(url_for("teacher.manage_questions", assessment_id=assessment_id))

@teacher_bp.route("/assessment/<assessment_id>/edit-question/<question_id>", methods=["POST"])
@teacher_required
def edit_question(assessment_id, question_id):
    """Updates an existing question, attached diagram/figure, and rubric criteria."""
    q_num = request.form.get("question_number", "1").strip()
    q_text = request.form.get("question_text", "").strip()
    try:
        max_m = float(request.form.get("max_marks", 5.0))
    except (ValueError, TypeError):
        max_m = 5.0
    model_ans = request.form.get("model_answer", "").strip()
    alternatives = request.form.get("acceptable_alternatives", "").strip()
    difficulty = request.form.get("difficulty", "medium")
    req_diagram = bool(request.form.get("requires_diagram"))
    req_numerical = bool(request.form.get("requires_numerical"))

    # Parse rubric criteria lists
    crit_titles = request.form.getlist("criterion_title") or request.form.getlist("criterion_title[]")
    crit_marks = request.form.getlist("criterion_marks") or request.form.getlist("criterion_marks[]")
    descs = request.form.getlist("criterion_desc") or request.form.getlist("criterion_desc[]")

    criteria = []
    for i, t in enumerate(crit_titles):
        t = t.strip()
        if t:
            try:
                m = float(crit_marks[i]) if i < len(crit_marks) else 1.0
            except ValueError:
                m = 1.0
            d = descs[i].strip() if i < len(descs) else ""
            criteria.append({"criterion_title": t, "max_marks": m, "description": d})

    # Handle optional replacement of question reference image
    img_file = request.files.get("question_image")
    image_url = ""
    if img_file and img_file.filename:
        valid, opt_bytes, metadata, _ = ImageService.validate_and_process_upload(img_file)
        if valid and opt_bytes:
            safe_num = "".join(c for c in q_num if c.isalnum()) or "1"
            mime = (metadata or {}).get("mime_type", "image/jpeg")
            ext = ".svg" if mime == "image/svg+xml" else (".png" if mime == "image/png" else ".jpg")
            filename = f"q_{assessment_id[:8]}_{safe_num}_{int(datetime.now().timestamp())}{ext}"
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "questions")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(opt_bytes)
            image_url = f"/static/uploads/questions/{filename}"

    q_data = {
        "question_number": q_num,
        "question_text": q_text,
        "max_marks": max_m,
        "model_answer": model_ans,
        "acceptable_alternatives": alternatives,
        "difficulty": difficulty,
        "requires_diagram": req_diagram,
        "requires_numerical": req_numerical,
        "criteria": criteria
    }
    if image_url:
        q_data["question_image_url"] = image_url

    success, msg = AssessmentService.update_question(assessment_id, question_id, q_data)
    if success:
        flash(f"Question {q_num} and its marking rubric updated successfully!", "success")
    else:
        flash(f"Failed to update question: {msg}", "danger")

    return redirect(url_for("teacher.manage_questions", assessment_id=assessment_id))

@teacher_bp.route("/assessment/<assessment_id>/delete-question/<question_id>", methods=["POST"])
@teacher_required
def delete_question(assessment_id, question_id):
    """Deletes a question from an assessment."""
    success, msg = AssessmentService.delete_question(assessment_id, question_id)
    if success:
        flash("Question deleted.", "info")
    else:
        flash(f"Could not delete question: {msg}", "danger")
    return redirect(url_for("teacher.manage_questions", assessment_id=assessment_id))

@teacher_bp.route("/students", methods=["GET", "POST"])
@teacher_required
def manage_students():
    """Student roster management with Excel/CSV preview & validation."""
    students = StudentService.get_all_students()
    preview_data = None
    invalid_rows = None

    if request.method == "POST":
        file = request.files.get("roster_file")
        if file and file.filename:
            try:
                content = file.read()
                valid, invalid = StudentService.parse_file(content, file.filename)
                session["pending_roster_import"] = valid
                preview_data = valid
                invalid_rows = invalid
                flash(f"Parsed {len(valid)} valid student records. Please review and confirm import.", "info")
            except Exception as e:
                flash(f"Error parsing student file: {str(e)}", "danger")

    return render_template(
        "teacher/students.html",
        students=students,
        preview_data=preview_data,
        invalid_rows=invalid_rows
    )

@teacher_bp.route("/students/confirm-import", methods=["POST"])
@teacher_required
def confirm_student_import():
    """Commits parsed preview students to Supabase database."""
    pending = session.pop("pending_roster_import", None)
    if not pending:
        flash("No pending student import found. Please upload the file again.", "warning")
        return redirect(url_for("teacher.manage_students"))

    summary = StudentService.import_students(pending)
    flash(f"Import complete! {summary['inserted']} students successfully saved.", "success")
    return redirect(url_for("teacher.manage_students"))

@teacher_bp.route("/students/edit/<student_id>", methods=["POST"])
@teacher_required
def edit_student(student_id):
    """Updates an existing student profile from the Registered Students Roster."""
    data = {
        "pin": request.form.get("pin", "").strip().upper(),
        "full_name": request.form.get("full_name", "").strip(),
        "academic_year": request.form.get("academic_year", "2026-2027").strip(),
        "semester": request.form.get("semester", "Semester 1").strip(),
        "branch": request.form.get("branch", "ECE").strip(),
        "section": request.form.get("section", "A").strip(),
        "contact_phone": request.form.get("contact_phone", "").strip(),
        "contact_email": request.form.get("contact_email", "").strip(),
        "is_active": request.form.get("is_active") == "1"
    }
    success, msg = StudentService.update_student(student_id, data)
    if success:
        flash(f"Student profile for {data['pin'] or student_id} updated successfully.", "success")
    else:
        flash(f"Failed to update student: {msg}", "danger")
    return redirect(url_for("teacher.manage_students"))

@teacher_bp.route("/students/edit-preview/<int:row_idx>", methods=["POST"])
@teacher_required
def edit_preview_student(row_idx):
    """Updates a row in the pending import preview list before committing."""
    pending = session.get("pending_roster_import", [])
    if 0 <= row_idx < len(pending):
        pending[row_idx]["pin"] = request.form.get("pin", pending[row_idx].get("pin", "")).strip().upper()
        pending[row_idx]["full_name"] = request.form.get("full_name", pending[row_idx].get("full_name", "")).strip()
        pending[row_idx]["academic_year"] = request.form.get("academic_year", pending[row_idx].get("academic_year", "2026-2027")).strip()
        pending[row_idx]["semester"] = request.form.get("semester", pending[row_idx].get("semester", "Semester 1")).strip()
        pending[row_idx]["branch"] = request.form.get("branch", pending[row_idx].get("branch", "ECE")).strip()
        pending[row_idx]["section"] = request.form.get("section", pending[row_idx].get("section", "A")).strip()
        pending[row_idx]["contact_phone"] = request.form.get("contact_phone", pending[row_idx].get("contact_phone", "")).strip()
        pending[row_idx]["contact_email"] = request.form.get("contact_email", pending[row_idx].get("contact_email", "")).strip()
        session["pending_roster_import"] = pending
        session.modified = True
        flash(f"Preview record #{row_idx + 1} ({pending[row_idx]['pin']}) updated.", "info")
    else:
        flash("Invalid preview row index.", "warning")
    return redirect(url_for("teacher.manage_students"))

@teacher_bp.route("/students/template")
@teacher_required
def download_student_template():
    """Generates and downloads the official student roster Excel template."""
    content = StudentService.generate_excel_template()
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="BEA_Student_Roster_Template.xlsx"
    )

@teacher_bp.route("/students/template/word")
@teacher_required
def download_student_word_template():
    """Generates and downloads the official student roster Word (.docx) template."""
    content = StudentService.generate_word_template()
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name="BEA_Student_Roster_Template.docx"
    )

@teacher_bp.route("/evaluate/<submission_id>")
@teacher_required
def evaluate_submission(submission_id):
    """
    Displays the submission script pages side-by-side with
    the AI evaluation and mark approval interface.
    """
    sub = SubmissionService.get_submission_by_id(submission_id)
    if not sub:
        flash("Submission not found.", "danger")
        return redirect(url_for("teacher.dashboard"))

    assessment = AssessmentService.get_assessment_by_id(sub["assessment_id"])
    pages = SubmissionService.get_pages_for_submission(submission_id)

    # Fetch existing evaluations
    supabase = db_manager.get_supabase(use_service_role=True)
    evaluations = {}
    if supabase:
        try:
            ev_res = supabase.table("question_evaluations").select("*").eq("submission_id", submission_id).execute()
            for ev in (ev_res.data or []):
                evaluations[ev["question_id"]] = ev
        except Exception as e:
            logger.error(f"Error loading question evaluations: {e}")

    # Group pages by question
    question_pages = {}
    for p in pages:
        question_pages.setdefault(p["question_id"], []).append(p)

    return render_template(
        "teacher/evaluation_view.html",
        submission=sub,
        assessment=assessment,
        pages=pages,
        question_pages=question_pages,
        evaluations=evaluations
    )

@teacher_bp.route("/api/run-ai-evaluation", methods=["POST"])
@teacher_required
def api_run_ai_evaluation():
    """
    Triggers Gemini Multimodal AI evaluation for a submission or specific question.
    Only executes when teacher explicitly clicks EVALUATE.
    """
    data = request.get_json() or {}
    submission_id = data.get("submission_id")
    target_question_id = data.get("question_id")  # Optional: evaluate single question
    teacher_id = session.get("teacher_id")

    sub = SubmissionService.get_submission_by_id(submission_id)
    if not sub:
        return jsonify({"success": False, "message": "Submission record not found."}), 404

    assessment = AssessmentService.get_assessment_by_id(sub["assessment_id"])
    all_pages = SubmissionService.get_pages_for_submission(submission_id)

    questions_to_eval = assessment.get("questions", [])
    if target_question_id:
        questions_to_eval = [q for q in questions_to_eval if q["id"] == target_question_id]

    supabase = db_manager.get_supabase(use_service_role=True)
    results = {}
    total_ai_marks = 0.0

    for q in questions_to_eval:
        qid = q["id"]
        q_pages = [p for p in all_pages if p.get("question_id") == qid]
        criteria = q.get("marking_criteria") or q.get("criteria", [])

        # Call Gemini AI
        eval_result = AIService.evaluate_question(
            question_data=q,
            marking_criteria=criteria,
            page_images=q_pages
        )

        awarded_m = float(eval_result.get("marks_awarded", 0.0))
        total_ai_marks += awarded_m

        # Save to question_evaluations table in Supabase
        if supabase:
            try:
                ev_row = {
                    "submission_id": submission_id,
                    "question_id": qid,
                    "ai_marks_awarded": awarded_m,
                    "max_marks": float(q.get("max_marks", 5.0)),
                    "ai_criterion_breakdown": eval_result.get("criterion_breakdown", []),
                    "ai_correct_concepts": eval_result.get("correct_concepts", []),
                    "ai_missing_concepts": eval_result.get("missing_concepts", []),
                    "ai_technical_mistakes": eval_result.get("technical_mistakes", []),
                    "ai_marks_deducted_reasons": eval_result.get("marks_deducted_reasons", []),
                    "ai_correct_explanation": eval_result.get("correct_explanation", ""),
                    "ai_model_answer_reference": eval_result.get("model_answer_reference", ""),
                    "ai_student_feedback": eval_result.get("student_feedback", ""),
                    "ai_confidence_level": eval_result.get("confidence_level", "high"),
                    "ai_lecturer_review_warning": eval_result.get("lecturer_review_warning", False),
                    "ai_warning_reason": eval_result.get("warning_reason"),
                    "approval_status": "pending_review",
                    "approved_marks": awarded_m  # Suggested marks pre-filled for teacher approval
                }
                supabase.table("question_evaluations").upsert(
                    ev_row,
                    on_conflict="submission_id,question_id"
                ).execute()
            except Exception as e:
                logger.error(f"Error saving question evaluation to Supabase: {e}")

        results[qid] = eval_result

    # Update submission status to 'evaluated' and update ai_total_marks
    if supabase:
        try:
            supabase.table("answer_submissions").update({
                "status": "evaluated",
                "ai_total_marks": total_ai_marks
            }).eq("id", submission_id).execute()
        except Exception:
            pass

    return jsonify({
        "success": True,
        "message": "AI Evaluation completed successfully.",
        "results": results,
        "total_ai_marks": total_ai_marks
    })

@teacher_bp.route("/api/approve-marks", methods=["POST"])
@teacher_required
def api_approve_marks():
    """
    Lecturer approves or modifies marks for a submission.
    Creates immutable audit log and populates official marks.
    """
    data = request.get_json() or {}
    submission_id = data.get("submission_id")
    question_marks = data.get("marks", {})  # {question_id: approved_mark}
    lecturer_comments = data.get("comments", {})
    overall_comment = data.get("overall_comment", "")
    teacher_id = session.get("teacher_id")

    supabase = db_manager.get_supabase(use_service_role=True)
    total_official_marks = 0.0

    if supabase:
        try:
            for qid, marks_val in question_marks.items():
                m_float = float(marks_val)
                total_official_marks += m_float
                comm = lecturer_comments.get(qid, "")

                # Fetch original AI evaluation
                prev_res = supabase.table("question_evaluations").select(
                    "id, ai_marks_awarded, approved_marks"
                ).eq("submission_id", submission_id).eq("question_id", qid).execute()

                prev_ev = prev_res.data[0] if prev_res.data else {}
                orig_ai = prev_ev.get("ai_marks_awarded", m_float)
                prev_off = prev_ev.get("approved_marks")

                is_modified = (m_float != orig_ai)

                # Update question_evaluations
                supabase.table("question_evaluations").update({
                    "approval_status": "modified_and_approved" if is_modified else "approved_as_is",
                    "approved_marks": m_float,
                    "lecturer_comments": comm,
                    "reviewed_by": teacher_id,
                    "reviewed_at": datetime.now(timezone.utc).isoformat()
                }).eq("submission_id", submission_id).eq("question_id", qid).execute()

                # Add entry into marks_audit_log
                supabase.table("marks_audit_log").insert({
                    "submission_id": submission_id,
                    "question_id": qid,
                    "question_evaluation_id": prev_ev.get("id"),
                    "action_type": "lecturer_modified" if is_modified else "lecturer_approved",
                    "original_ai_marks": orig_ai,
                    "previous_official_marks": prev_off,
                    "new_official_marks": m_float,
                    "reason": f"Teacher marked as {'modified' if is_modified else 'approved'}. {comm}".strip(),
                    "actor_lecturer_id": teacher_id
                }).execute()

            # Update submission record to 'approved' and calculate pass status
            sub_res = supabase.table("answer_submissions").select("assessment_id").eq("id", submission_id).execute()
            asm_id = sub_res.data[0]["assessment_id"] if sub_res.data else None
            asm = AssessmentService.get_assessment_by_id(asm_id) if asm_id else None
            max_m = float(asm.get("max_marks", 20.0)) if asm else 20.0
            pass_pct = float(asm.get("pass_percentage", 35.0)) if asm else 35.0
            pct = round((total_official_marks / max_m) * 100, 2)
            pass_status = "pass" if pct >= pass_pct else "fail"

            supabase.table("answer_submissions").update({
                "status": "approved",
                "official_total_marks": total_official_marks,
                "percentage": pct,
                "pass_status": pass_status,
                "approved_by": teacher_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "lecturer_overall_comment": overall_comment
            }).eq("id", submission_id).execute()

            return jsonify({
                "success": True,
                "message": "Marks approved and recorded in official audit ledger.",
                "total_official_marks": total_official_marks,
                "percentage": pct,
                "pass_status": pass_status
            })

        except Exception as e:
            logger.error(f"Error approving marks: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "Marks approved (Local mode).", "total_official_marks": total_official_marks})

@teacher_bp.route("/reopen-submission", methods=["POST"])
@teacher_required
def reopen_submission():
    """Allows lecturer to reopen a locked submission with an audit reason."""
    submission_id = request.form.get("submission_id")
    reason = request.form.get("reason", "").strip()
    teacher_id = session.get("teacher_id")

    success, msg = SubmissionService.reopen_submission(submission_id, teacher_id, reason)
    if success:
        flash("Submission has been reopened. The student may now update and resubmit.", "success")
    else:
        flash(f"Reopen failed: {msg}", "danger")

    return redirect(request.referrer or url_for("teacher.dashboard"))

@teacher_bp.route("/analytics/<assessment_id>")
@teacher_required
def result_analytics(assessment_id):
    """Result Analyser and Topic Analytics Dashboard."""
    assessment = AssessmentService.get_assessment_by_id(assessment_id)
    if not assessment:
        flash("Assessment not found.", "danger")
        return redirect(url_for("teacher.dashboard"))

    analytics = AnalyticsService.get_assessment_analytics(assessment_id)
    return render_template(
        "teacher/analytics.html",
        assessment=assessment,
        analytics=analytics
    )
