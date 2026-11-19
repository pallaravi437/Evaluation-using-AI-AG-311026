import os
import json
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from config import Config
from database.db_manager import db_manager

logger = logging.getLogger("bea.submission_service")

# Local in-memory store for drafts & submissions when running locally before Supabase sync
_local_submissions: Dict[str, Dict[str, Any]] = {}  # key: (assessment_id, student_id)
_local_pages: Dict[str, List[Dict[str, Any]]] = {}  # key: submission_id
_local_evaluations: Dict[str, Dict[str, Any]] = {}  # key: submission_id -> {question_id: eval_dict}
_local_rechecks: Dict[str, Dict[str, Any]] = {}  # key: f"{submission_id}_{question_id}"

class SubmissionService:
    """
    Manages question-wise answer page uploads, draft saving,
    single-submission locking, unique receipt code generation,
    timestamping in Asia/Kolkata, and lecturer reopening.
    """
    _local_evaluations = _local_evaluations
    _local_submissions = _local_submissions
    _local_pages = _local_pages

    @classmethod
    def _get_student_info(cls, student_id: str) -> Dict[str, Any]:
        """Looks up student metadata across local rosters, registrations, and tenants."""
        if not student_id:
            return {"id": "", "pin": "26054-MEE", "full_name": "Student", "branch": "ECE", "section": "A"}

        # 1. Search in student_service._local_students
        try:
            from services.student_service import _local_students
            for st in _local_students:
                if st.get("id") == student_id or st.get("pin") == student_id:
                    return {
                        "id": st.get("id", student_id),
                        "pin": st.get("pin", student_id),
                        "full_name": st.get("full_name", "Student"),
                        "branch": st.get("branch", "ECE"),
                        "section": st.get("section", "A")
                    }
        except Exception:
            pass

        # 2. Search in student_registrations.json
        try:
            from services.student_service import StudentService
            regs = StudentService._load_registrations()
            for r in regs:
                if r.get("id") == student_id or r.get("pin") == student_id:
                    return {
                        "id": r.get("id", student_id),
                        "pin": r.get("pin", student_id),
                        "full_name": r.get("full_name", "Student"),
                        "branch": r.get("branch", "ECE"),
                        "section": r.get("section", "A")
                    }
        except Exception:
            pass

        # 3. Search in all tenant students.json files
        try:
            from services.lecturer_service import LecturerService, TENANTS_DIR
            if os.path.exists(TENANTS_DIR):
                for tname in os.listdir(TENANTS_DIR):
                    t_students = LecturerService.load_tenant_data(tname, "students.json") or []
                    for st in t_students:
                        if st.get("id") == student_id or st.get("pin") == student_id:
                            return {
                                "id": st.get("id", student_id),
                                "pin": st.get("pin", student_id),
                                "full_name": st.get("full_name", "Student"),
                                "branch": st.get("branch", "ECE"),
                                "section": st.get("section", "A")
                            }
        except Exception:
            pass

        # Fallback to student_id
        return {
            "id": student_id,
            "pin": student_id if "-" in str(student_id) else "26054-MEE",
            "full_name": student_id if "-" not in str(student_id) else "Student",
            "branch": "ECE",
            "section": "A"
        }

    @classmethod
    def _persist_submission_to_tenant(cls, sub: Dict[str, Any]) -> None:
        """Persists submission to tenant submissions.json file."""
        if not sub:
            return
        asm_id = sub.get("assessment_id")
        try:
            from services.assessment_service import AssessmentService
            from services.lecturer_service import LecturerService
            asm = AssessmentService.get_assessment_by_id(asm_id) or {}
            tenant_id = asm.get("created_by") or "11111111-1111-1111-1111-111111111111"
            tenant_subs = LecturerService.load_tenant_data(tenant_id, "submissions.json") or []
            existing_idx = next((i for i, s in enumerate(tenant_subs) if s.get("id") == sub.get("id")), -1)
            # Create a clean serializable copy
            sub_copy = {k: v for k, v in sub.items() if k != "students"}
            if existing_idx >= 0:
                tenant_subs[existing_idx] = sub_copy
            else:
                tenant_subs.insert(0, sub_copy)
            LecturerService.save_tenant_data(tenant_id, "submissions.json", tenant_subs)
        except Exception as e:
            logger.warning(f"Could not persist submission to tenant: {e}")

    @staticmethod
    def generate_receipt_code() -> str:
        """Generates a cryptographically strong, human-readable submission receipt code."""
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_token = secrets.token_hex(3).upper()
        return f"BEA-{today_str}-{rand_token}"

    @classmethod
    def get_recent_submissions(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the latest submitted scripts across assessments
        for public activity feed before login.
        """
        supabase = db_manager.get_supabase(use_service_role=True)
        recent = []
        if supabase:
            try:
                res = supabase.table("answer_submissions").select(
                    "id, submission_receipt_code, status, submitted_at, students(full_name, pin), assessments(title)"
                ).in_("status", ["submitted", "evaluated", "approved"]).order("submitted_at", desc=True).limit(limit).execute()
                
                for s in (res.data or []):
                    st = s.get("students") or {}
                    asm = s.get("assessments") or {}
                    recent.append({
                        "id": s["id"],
                        "pin": st.get("pin", "26054-MEE"),
                        "name": st.get("full_name", "Student"),
                        "test_name": asm.get("title", "BEA Assessment"),
                        "submitted_at": s.get("submitted_at"),
                        "status": s.get("status", "submitted")
                    })
                if recent:
                    return recent
            except Exception as e:
                logger.error(f"Error fetching recent submissions: {e}")

        # Local mode / seeded recent activity
        now_utc = datetime.now(timezone.utc)
        for sub in _local_submissions.values():
            if sub.get("status") in ("submitted", "evaluated", "approved"):
                recent.append({
                    "id": sub["id"],
                    "pin": "26054-ES-041",
                    "name": "KASHABOINA PRANAVI",
                    "test_name": "Slip Test 1: BJT Fundamentals & CE Configuration",
                    "submitted_at": sub.get("submitted_at", now_utc.isoformat()),
                    "status": sub.get("status", "submitted")
                })

        if not recent:
            # Realistic seeded submissions for Diploma batch preview
            recent = [
                {
                    "pin": "26054-ES-041",
                    "name": "KASHABOINA PRANAVI",
                    "test_name": "Slip Test 1: BJT Fundamentals & CE Configuration",
                    "submitted_at": now_utc.isoformat(),
                    "status": "submitted"
                },
                {
                    "pin": "26054-CPS-001",
                    "name": "A SUJATHA",
                    "test_name": "Slip Test 1: BJT Fundamentals & CE Configuration",
                    "submitted_at": now_utc.isoformat(),
                    "status": "submitted"
                },
                {
                    "pin": "26054-CPS-005",
                    "name": "BADAVATH ROHITH RAJ",
                    "test_name": "Slip Test 1: BJT Fundamentals & CE Configuration",
                    "submitted_at": now_utc.isoformat(),
                    "status": "submitted"
                },
                {
                    "pin": "26054-SCT-032",
                    "name": "LOLABHATTU SAI SATWIK",
                    "test_name": "Slip Test 1: BJT Fundamentals & CE Configuration",
                    "submitted_at": now_utc.isoformat(),
                    "status": "submitted"
                }
            ]
        return recent

    @classmethod
    def get_submissions_for_assessment(cls, assessment_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all submissions for an assessment, newest first.
        Includes nested student info for display. Falls back to tenant files
        and local in-memory store when Supabase is unconfigured or unreachable.
        """
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("answer_submissions").select(
                    "*, students(id, pin, full_name, branch, section)"
                ).eq("assessment_id", assessment_id).order("submitted_at", desc=True).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error fetching submissions for assessment {assessment_id}: {e}")

        # Local mode & Tenant store loading
        from services.assessment_service import AssessmentService
        from services.lecturer_service import LecturerService, TENANTS_DIR
        asm = AssessmentService.get_assessment_by_id(assessment_id) or {}
        tenant_id = asm.get("created_by") or "11111111-1111-1111-1111-111111111111"

        subs_map: Dict[str, Dict[str, Any]] = {}
        # 1. Load from assessment creator's tenant submissions.json
        tenant_subs = LecturerService.load_tenant_data(tenant_id, "submissions.json") or []
        for s in tenant_subs:
            if s.get("assessment_id") == assessment_id:
                subs_map[s["id"]] = s

        # 2. Check default tenant if different
        if tenant_id != "11111111-1111-1111-1111-111111111111":
            default_subs = LecturerService.load_tenant_data("11111111-1111-1111-1111-111111111111", "submissions.json") or []
            for s in default_subs:
                if s.get("assessment_id") == assessment_id and s["id"] not in subs_map:
                    subs_map[s["id"]] = s

        # 3. Check all tenants just in case student was enrolled with another lecturer
        if os.path.exists(TENANTS_DIR):
            try:
                for tname in os.listdir(TENANTS_DIR):
                    if tname not in (tenant_id, "11111111-1111-1111-1111-111111111111"):
                        other_subs = LecturerService.load_tenant_data(tname, "submissions.json") or []
                        for s in other_subs:
                            if s.get("assessment_id") == assessment_id and s["id"] not in subs_map:
                                subs_map[s["id"]] = s
            except Exception:
                pass

        # 4. Merge from in-memory _local_submissions
        for s in _local_submissions.values():
            if s.get("assessment_id") == assessment_id:
                subs_map[s["id"]] = s

        # Enrich with student info
        final_subs = []
        for s in subs_map.values():
            rec = dict(s)
            rec["students"] = cls._get_student_info(rec.get("student_id"))
            final_subs.append(rec)

        final_subs.sort(key=lambda x: x.get("submitted_at") or x.get("created_at") or "", reverse=True)
        return final_subs

    @classmethod
    def get_or_create_draft_submission(cls, assessment_id: str, student_id: str) -> Dict[str, Any]:
        """
        Retrieves existing submission or initializes a new draft.
        Enforces one submission record per student per assessment.
        """
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("answer_submissions").select("*").eq(
                    "assessment_id", assessment_id
                ).eq("student_id", student_id).execute()

                if res.data:
                    return res.data[0]

                # Create new draft
                receipt_code = cls.generate_receipt_code()
                new_sub = {
                    "assessment_id": assessment_id,
                    "student_id": student_id,
                    "submission_receipt_code": receipt_code,
                    "status": "draft",
                    "is_locked": False,
                    "total_pages_uploaded": 0
                }
                insert_res = supabase.table("answer_submissions").insert(new_sub).execute()
                if insert_res.data:
                    return insert_res.data[0]
            except Exception as e:
                logger.error(f"Supabase get_or_create_submission error: {e}")

        # Local fallback mode
        key = f"{assessment_id}_{student_id}"
        if key not in _local_submissions:
            # Check tenant storage first before creating new draft
            from services.assessment_service import AssessmentService
            from services.lecturer_service import LecturerService
            asm = AssessmentService.get_assessment_by_id(assessment_id) or {}
            tenant_id = asm.get("created_by") or "11111111-1111-1111-1111-111111111111"
            tenant_subs = LecturerService.load_tenant_data(tenant_id, "submissions.json") or []
            existing = next((s for s in tenant_subs if s.get("assessment_id") == assessment_id and s.get("student_id") == student_id), None)
            if existing:
                _local_submissions[key] = dict(existing)
                _local_pages[existing["id"]] = []
            else:
                sub_id = str(uuid.uuid4())
                new_rec = {
                    "id": sub_id,
                    "assessment_id": assessment_id,
                    "student_id": student_id,
                    "submission_receipt_code": cls.generate_receipt_code(),
                    "status": "draft",
                    "is_locked": False,
                    "total_pages_uploaded": 0,
                    "submitted_at": None,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                _local_submissions[key] = new_rec
                _local_pages[sub_id] = []
                cls._persist_submission_to_tenant(new_rec)
        return _local_submissions[key]

    @classmethod
    def save_answer_page(
        cls,
        submission_id: str,
        question_id: str,
        page_number: int,
        file_bytes: bytes,
        mime_type: str,
        metadata: Dict[str, Any],
        force: bool = False
    ) -> Tuple[bool, Optional[str], str]:
        """
        Saves an uploaded answer page:
        - Uploads to private Supabase Storage bucket ('bea-answer-scripts').
        - Creates / updates answer_pages table metadata.
        """
        sub = cls.get_submission_by_id(submission_id)
        if not sub:
            return False, None, "Submission not found."

        if sub.get("is_locked", False) and not force:
            return False, None, "This submission is locked and cannot be modified."

        storage_path = f"submissions/{submission_id}/{question_id}_page_{page_number}_{metadata.get('sha256', '')[:8]}.jpg"
        supabase = db_manager.get_supabase(use_service_role=True)

        if supabase:
            try:
                # Upload to Supabase Private Storage
                try:
                    supabase.storage.from_(Config.STORAGE_BUCKET).upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": mime_type, "upsert": "true"}
                    )
                except Exception as st_err:
                    logger.warning(f"Supabase storage upload note: {st_err}")

                # Insert / update record in answer_pages
                page_record = {
                    "submission_id": submission_id,
                    "question_id": question_id,
                    "page_number": page_number,
                    "storage_bucket": Config.STORAGE_BUCKET,
                    "storage_path": storage_path,
                    "mime_type": mime_type,
                    "original_size_bytes": metadata.get("original_size_bytes", len(file_bytes)),
                    "optimized_size_bytes": metadata.get("optimized_size_bytes", len(file_bytes)),
                    "image_width": metadata.get("width"),
                    "image_height": metadata.get("height"),
                    "sha256_checksum": metadata.get("sha256")
                }

                res = supabase.table("answer_pages").upsert(
                    page_record,
                    on_conflict="submission_id,question_id,page_number"
                ).execute()

                # Update page count
                count_res = supabase.table("answer_pages").select("id", count="exact").eq("submission_id", submission_id).execute()
                total = count_res.count if hasattr(count_res, "count") else len(count_res.data or [])
                supabase.table("answer_submissions").update({"total_pages_uploaded": total}).eq("id", submission_id).execute()

                return True, storage_path, "Page saved successfully."
            except Exception as e:
                logger.error(f"Error saving answer page to Supabase: {e}")
                return False, None, str(e)

        # Local mode: persist file bytes to static directory for direct HTTP serving
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "submissions", submission_id)
        os.makedirs(upload_dir, exist_ok=True)
        ext = ".pdf" if mime_type == "application/pdf" else (".png" if mime_type == "image/png" else ".jpg")
        filename = f"p{page_number}_{str(question_id)[:8]}{ext}"
        filepath = os.path.join(upload_dir, filename)
        try:
            with open(filepath, "wb") as pf:
                pf.write(file_bytes)
            file_url = f"/static/uploads/submissions/{submission_id}/{filename}"
        except Exception as io_err:
            logger.warning(f"Could not write page file to disk: {io_err}")
            file_url = ""

        pages = _local_pages.setdefault(submission_id, [])
        pages = [p for p in pages if not (p["question_id"] == question_id and p["page_number"] == page_number)]
        page_obj = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "question_id": question_id,
            "page_number": page_number,
            "storage_path": storage_path,
            "file_url": file_url,
            "mime_type": mime_type,
            "original_size_bytes": metadata.get("original_size_bytes", len(file_bytes)),
            "optimized_size_bytes": metadata.get("optimized_size_bytes", len(file_bytes)),
            "image_width": metadata.get("width"),
            "image_height": metadata.get("height"),
            "bytes": file_bytes
        }
        pages.append(page_obj)
        pages.sort(key=lambda x: x.get("page_number", 1))
        _local_pages[submission_id] = pages
        sub["total_pages_uploaded"] = len(pages)
        sub["answer_pages"] = pages
        key = f"{sub.get('assessment_id')}_{sub.get('student_id')}"
        _local_submissions[key] = sub
        cls._persist_submission_to_tenant(sub)
        return True, storage_path, "Page saved (Local mode)."

    @classmethod
    def get_pages_for_submission(cls, submission_id: str) -> List[Dict[str, Any]]:
        """Retrieves all answer pages for a submission, organized question-wise."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("answer_pages").select("*").eq("submission_id", submission_id).order("page_number").execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error fetching answer pages: {e}")

        if submission_id in _local_pages and _local_pages[submission_id]:
            return _local_pages[submission_id]

        sub = cls.get_submission_by_id(submission_id)
        if sub and sub.get("answer_pages"):
            _local_pages[submission_id] = sub["answer_pages"]
            return sub["answer_pages"]

        return _local_pages.get(submission_id, [])

    @classmethod
    def finalize_submission(cls, submission_id: str, client_ip: str = "", user_agent: str = "", mcq_answers: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Enforces final submission:
        - Locks student editing (is_locked = True, status = 'submitted' or 'approved' for MCQs).
        - Auto-grades MCQs against answer keys with instantaneous scoring.
        - Records server timestamp in Asia/Kolkata timezone.
        - Returns submission receipt.
        """
        sub = cls.get_submission_by_id(submission_id)
        if not sub:
            return False, None, "Submission record not found."

        if sub.get("is_locked", False):
            return True, sub, "Submission was already submitted and locked."

        now_utc = datetime.now(timezone.utc)
        now_kolkata = now_utc.astimezone(Config.TIMEZONE).strftime("%d %b %Y, %I:%M:%S %p %Z")

        # Auto-grade MCQs if student submitted choices
        evaluations_dict = {}
        if mcq_answers:
            from services.assessment_service import AssessmentService
            asm = AssessmentService.get_assessment_by_id(sub.get("assessment_id", ""))
            if asm and asm.get("questions"):
                mcq_score = 0.0
                total_mcq_possible = 0.0
                for q in asm["questions"]:
                    qid = str(q.get("id"))
                    q_num = str(q.get("question_number"))
                    correct_opt = (q.get("correct_option") or "A").strip().upper()
                    student_choice = (mcq_answers.get(qid) or mcq_answers.get(q_num) or "").strip().upper()
                    q_max = float(q.get("max_marks", 1.0))
                    total_mcq_possible += q_max
                    is_correct = bool(student_choice and student_choice == correct_opt)
                    awarded = q_max if is_correct else 0.0
                    mcq_score += awarded

                    comment_text = f"Student chose Option {student_choice or 'None'}. {'✓ Correct option selected.' if is_correct else f'✗ Incorrect choice. Correct option is {correct_opt}.'}"
                    model_ans_text = q.get("model_answer", "") or f"Option {correct_opt} is the correct answer."
                    eval_record = {
                        "id": str(uuid.uuid4()),
                        "submission_id": submission_id,
                        "question_id": qid,
                        "ai_marks_awarded": awarded,
                        "approved_marks": awarded,
                        "max_marks": q_max,
                        "student_selected_option": student_choice,
                        "correct_option": correct_opt,
                        "is_correct": is_correct,
                        "model_answer": model_ans_text,
                        "explanation": model_ans_text,
                        "ai_correct_explanation": model_ans_text,
                        "ai_model_answer_reference": model_ans_text,
                        "ai_criterion_breakdown": [
                            {
                                "title": "Selected Option & Technical Accuracy",
                                "marks_awarded": awarded,
                                "max_marks": q_max,
                                "comment": comment_text
                            }
                        ],
                        "ai_correct_concepts": [f"Option {correct_opt}: {model_ans_text}"] if is_correct else [],
                        "ai_missing_concepts": [f"Expected Option {correct_opt}: {model_ans_text}"] if not is_correct else [],
                        "approval_status": "approved_as_is",
                        "ai_student_feedback": f"Selected Option {student_choice or 'None'}. {'✓ Correct! Full marks awarded. ' + model_ans_text if is_correct else f'✗ Incorrect. Correct answer is Option {correct_opt}. Explanation: ' + model_ans_text}"
                    }
                    evaluations_dict[qid] = eval_record

                sub["mcq_answers"] = mcq_answers
                sub["ai_total_marks"] = mcq_score
                sub["official_total_marks"] = mcq_score
                max_total = float(asm.get("max_marks") or total_mcq_possible or 1.0)
                sub["percentage"] = round((mcq_score / max_total) * 100, 1)
                sub["pass_status"] = "pass" if sub["percentage"] >= float(asm.get("pass_percentage", 35.0)) else "fail"
                sub["status"] = "approved"
                sub["question_evaluations"] = evaluations_dict

        _local_evaluations[submission_id] = evaluations_dict

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                update_data = {
                    "status": sub.get("status", "submitted"),
                    "is_locked": True,
                    "submitted_at": now_utc.isoformat(),
                    "client_ip": client_ip,
                    "user_agent": user_agent
                }
                if mcq_answers:
                    update_data["ai_total_marks"] = sub.get("ai_total_marks")
                    update_data["official_total_marks"] = sub.get("official_total_marks")
                    update_data["percentage"] = sub.get("percentage")
                    update_data["pass_status"] = sub.get("pass_status")

                res = supabase.table("answer_submissions").update(update_data).eq("id", submission_id).execute()

                # Upsert individual evaluations into Supabase
                for qid, ev_row in evaluations_dict.items():
                    try:
                        supabase.table("question_evaluations").upsert({
                            "submission_id": submission_id,
                            "question_id": qid,
                            "ai_marks_awarded": ev_row["ai_marks_awarded"],
                            "approved_marks": ev_row["approved_marks"],
                            "max_marks": ev_row["max_marks"],
                            "approval_status": "approved_as_is",
                            "ai_student_feedback": ev_row["ai_student_feedback"],
                            "ai_model_answer_reference": ev_row["explanation"]
                        }, on_conflict="submission_id,question_id").execute()
                    except Exception as q_err:
                        logger.warning(f"Note inserting evaluation row: {q_err}")

                if res.data:
                    updated = res.data[0]
                    updated["submitted_at_formatted"] = now_kolkata
                    cls._persist_submission_to_tenant(updated)
                    return True, updated, "Submission finalized and locked successfully."
            except Exception as e:
                logger.error(f"Error finalizing submission: {e}")
                return False, None, str(e)

        # Local mode
        if not mcq_answers:
            sub["status"] = "submitted"
        sub["is_locked"] = True
        sub["submitted_at"] = now_utc.isoformat()
        sub["submitted_at_formatted"] = now_kolkata
        key = f"{sub.get('assessment_id')}_{sub.get('student_id')}"
        _local_submissions[key] = sub
        cls._persist_submission_to_tenant(sub)
        return True, sub, "Submission finalized (Local mode)."

    @classmethod
    def get_evaluations_for_submission(cls, submission_id: str) -> Dict[str, Dict[str, Any]]:
        """Returns question evaluations mapping question_id -> evaluation details."""
        supabase = db_manager.get_supabase(use_service_role=True)
        evals = {}
        if supabase:
            try:
                res = supabase.table("question_evaluations").select("*").eq("submission_id", submission_id).execute()
                for row in (res.data or []):
                    evals[row["question_id"]] = row
                if evals:
                    return evals
            except Exception as e:
                logger.error(f"Error fetching evaluations from Supabase: {e}")

        # Local mode fallback
        if submission_id in _local_evaluations and _local_evaluations[submission_id]:
            return _local_evaluations[submission_id]

        sub = cls.get_submission_by_id(submission_id)
        if sub and sub.get("question_evaluations"):
            _local_evaluations[submission_id] = sub["question_evaluations"]
            return sub["question_evaluations"]

        return _local_evaluations.get(submission_id, {})

    @classmethod
    def get_submission_by_id(cls, submission_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves submission record by ID."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("answer_submissions").select(
                    "*, students(full_name, pin, branch, section), assessments(title, max_marks)"
                ).eq("id", submission_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error fetching submission {submission_id}: {e}")

        # Check in-memory cache
        for sub in _local_submissions.values():
            if sub.get("id") == submission_id:
                rec = dict(sub)
                rec["students"] = cls._get_student_info(rec.get("student_id"))
                return rec

        # Check tenant storage files
        try:
            from services.lecturer_service import LecturerService, TENANTS_DIR
            if os.path.exists(TENANTS_DIR):
                for tname in os.listdir(TENANTS_DIR):
                    tenant_subs = LecturerService.load_tenant_data(tname, "submissions.json") or []
                    for s in tenant_subs:
                        if s.get("id") == submission_id:
                            rec = dict(s)
                            rec["students"] = cls._get_student_info(rec.get("student_id"))
                            key = f"{rec.get('assessment_id')}_{rec.get('student_id')}"
                            _local_submissions[key] = rec
                            return rec
        except Exception as e:
            logger.warning(f"Error searching submission in tenants: {e}")

        return None

    @classmethod
    def update_submission(cls, submission_id: str, updates: Dict[str, Any]) -> bool:
        """Updates submission fields across local cache, tenant storage, and Supabase."""
        sub = cls.get_submission_by_id(submission_id)
        if not sub:
            return False

        for k, v in updates.items():
            sub[k] = v

        key = f"{sub.get('assessment_id')}_{sub.get('student_id')}"
        _local_submissions[key] = sub
        cls._persist_submission_to_tenant(sub)

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                supabase.table("answer_submissions").update(updates).eq("id", submission_id).execute()
            except Exception as e:
                logger.warning(f"Supabase update error: {e}")

        return True

    @classmethod
    def reopen_submission(cls, submission_id: str, lecturer_id: str, reason: str) -> Tuple[bool, str]:
        """Allows a teacher to reopen a locked submission with an audit reason."""
        if not reason or len(reason.strip()) < 5:
            return False, "A specific audit reason (at least 5 characters) is required to reopen."

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                supabase.table("answer_submissions").update({
                    "is_locked": False,
                    "status": "reopened",
                    "reopened_by": lecturer_id,
                    "reopened_at": now_iso,
                    "reopen_reason": reason.strip()
                }).eq("id", submission_id).execute()

                # Add to marks_audit_log
                supabase.table("marks_audit_log").insert({
                    "submission_id": submission_id,
                    "action_type": "submission_reopened",
                    "reason": reason.strip(),
                    "actor_lecturer_id": lecturer_id
                }).execute()

                return True, "Submission reopened for student resubmission."
            except Exception as e:
                logger.error(f"Error reopening submission: {e}")
                return False, str(e)

        sub = cls.get_submission_by_id(submission_id)
        if sub:
            cls.update_submission(submission_id, {
                "is_locked": False,
                "status": "reopened",
                "reopen_reason": reason
            })
            return True, "Submission reopened (Local mode)."
        return False, "Submission not found."
