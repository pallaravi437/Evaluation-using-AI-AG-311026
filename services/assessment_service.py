import os
import json
import logging
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from config import Config
from database.db_manager import db_manager

logger = logging.getLogger("bea.assessment_service")

# In-memory mock storage for local development / testing before Supabase connection
_local_assessments: List[Dict[str, Any]] = []
_local_questions: Dict[str, List[Dict[str, Any]]] = {}

class AssessmentService:
    """
    Manages creation and configuration of Assessments (Slip tests, Assignments, Unit tests),
    questions with rubrics/marking criteria, and syllabus topic mappings.
    """

    @classmethod
    def get_all_assessments(cls) -> List[Dict[str, Any]]:
        """Retrieves list of all assessments with question count and submission summary."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("assessments").select(
                    "id, title, assessment_type, subject_code, assessment_date, max_marks, pass_percentage, status, allow_submissions, results_published, created_at"
                ).order("assessment_date", desc=True).execute()
                assessments = res.data or []
                return assessments
            except Exception as e:
                logger.error(f"Error fetching assessments: {e}")

        # Return sample default assessment if empty or in local mode
        if not _local_assessments:
            cls._seed_default_assessment()
        return _local_assessments

    @classmethod
    def get_assessment_by_id(cls, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Fetches assessment details and questions."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("assessments").select("*").eq("id", assessment_id).execute()
                if res.data:
                    assessment = res.data[0]
                    # Fetch questions
                    q_res = supabase.table("questions").select(
                        "*, marking_criteria(*)"
                    ).eq("assessment_id", assessment_id).order("display_order").execute()
                    assessment["questions"] = q_res.data or []
                    return assessment
            except Exception as e:
                logger.error(f"Error fetching assessment {assessment_id}: {e}")

        for asm in _local_assessments:
            if asm["id"] == assessment_id:
                asm_copy = dict(asm)
                asm_copy["questions"] = _local_questions.get(assessment_id, [])
                return asm_copy
        return None

    @classmethod
    def create_assessment(
        cls,
        title: str,
        assessment_type: str,
        max_marks: float,
        assessment_date: str,
        instructions: str = "",
        pass_percentage: float = 35.0,
        questions: Optional[List[Dict[str, Any]]] = None,
        created_by_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """Creates a new assessment with questions and marking criteria."""
        supabase = db_manager.get_supabase(use_service_role=True)
        
        record = {
            "title": title.strip(),
            "assessment_type": assessment_type,
            "subject_code": "BEA (MEE-105)",
            "assessment_date": assessment_date or str(date.today()),
            "max_marks": float(max_marks),
            "pass_percentage": float(pass_percentage),
            "instructions": instructions.strip(),
            "status": "published",
            "allow_submissions": True,
            "results_published": False,
            "created_by": created_by_id
        }

        if supabase:
            try:
                res = supabase.table("assessments").insert(record).execute()
                if res.data:
                    new_id = res.data[0]["id"]
                    if questions:
                        cls._save_questions(supabase, new_id, questions)
                    return True, new_id, "Assessment created successfully."
            except Exception as e:
                logger.error(f"Error creating assessment in Supabase: {e}")
                return False, None, str(e)

        # Local mode
        import uuid
        new_id = str(uuid.uuid4())
        record["id"] = new_id
        _local_assessments.insert(0, record)
        if questions:
            _local_questions[new_id] = questions
        else:
            _local_questions[new_id] = []
        return True, new_id, "Assessment created (Local session)."

    @classmethod
    def add_question(cls, assessment_id: str, question_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Adds a single question with rubric criteria to an assessment."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                # Count current questions for display order
                cur_res = supabase.table("questions").select("id", count="exact").eq("assessment_id", assessment_id).execute()
                current_count = cur_res.count if hasattr(cur_res, "count") else len(cur_res.data or [])
                display_order = current_count + 1

                q_row = {
                    "assessment_id": assessment_id,
                    "question_number": question_data.get("question_number", str(display_order)),
                    "display_order": display_order,
                    "question_text": question_data.get("question_text", "").strip(),
                    "max_marks": float(question_data.get("max_marks", 5.0)),
                    "model_answer": question_data.get("model_answer", "").strip(),
                    "acceptable_alternatives": question_data.get("acceptable_alternatives", "").strip(),
                    "difficulty": question_data.get("difficulty", "medium"),
                    "requires_diagram": bool(question_data.get("requires_diagram", False)),
                    "requires_numerical": bool(question_data.get("requires_numerical", False)),
                    "question_image_url": question_data.get("question_image_url", ""),
                    "question_image_path": question_data.get("question_image_path", "")
                }
                res = supabase.table("questions").insert(q_row).execute()
                if res.data:
                    q_id = res.data[0]["id"]
                    criteria = question_data.get("criteria", [])
                    for idx, c in enumerate(criteria, start=1):
                        supabase.table("marking_criteria").insert({
                            "question_id": q_id,
                            "criterion_order": idx,
                            "criterion_title": c.get("criterion_title", f"Criterion {idx}").strip(),
                            "max_marks": float(c.get("max_marks", 1.0)),
                            "description": c.get("description", "").strip()
                        }).execute()
                    return True, q_id, "Question added successfully."
            except Exception as e:
                logger.error(f"Error adding question to Supabase: {e}")
                return False, None, str(e)

        # Local mode
        import uuid
        q_id = str(uuid.uuid4())
        q_copy = dict(question_data)
        q_copy["id"] = q_id
        q_list = _local_questions.setdefault(assessment_id, [])
        q_copy["display_order"] = len(q_list) + 1
        q_list.append(q_copy)
        return True, q_id, "Question added (Local mode)."

    @classmethod
    def update_question(cls, assessment_id: str, question_id: str, question_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Updates an existing question and its marking rubric criteria."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                q_row = {
                    "question_number": question_data.get("question_number", "1"),
                    "question_text": question_data.get("question_text", "").strip(),
                    "max_marks": float(question_data.get("max_marks", 5.0)),
                    "model_answer": question_data.get("model_answer", "").strip(),
                    "acceptable_alternatives": question_data.get("acceptable_alternatives", "").strip(),
                    "difficulty": question_data.get("difficulty", "medium"),
                    "requires_diagram": bool(question_data.get("requires_diagram", False)),
                    "requires_numerical": bool(question_data.get("requires_numerical", False)),
                }
                if question_data.get("question_image_url"):
                    q_row["question_image_url"] = question_data["question_image_url"]

                supabase.table("questions").update(q_row).eq("id", question_id).execute()

                # Update criteria
                criteria = question_data.get("criteria", [])
                if criteria:
                    supabase.table("marking_criteria").delete().eq("question_id", question_id).execute()
                    for idx, c in enumerate(criteria, start=1):
                        supabase.table("marking_criteria").insert({
                            "question_id": question_id,
                            "criterion_order": idx,
                            "criterion_title": c.get("criterion_title", f"Criterion {idx}").strip(),
                            "max_marks": float(c.get("max_marks", 1.0)),
                            "description": c.get("description", "").strip()
                        }).execute()
                return True, "Question updated successfully."
            except Exception as e:
                logger.error(f"Error updating question: {e}")
                return False, str(e)

        # Local mode
        if assessment_id in _local_questions:
            for q in _local_questions[assessment_id]:
                if q.get("id") == question_id:
                    q["question_number"] = question_data.get("question_number", q.get("question_number"))
                    q["question_text"] = question_data.get("question_text", q.get("question_text"))
                    q["max_marks"] = float(question_data.get("max_marks", q.get("max_marks", 5.0)))
                    q["model_answer"] = question_data.get("model_answer", q.get("model_answer"))
                    q["acceptable_alternatives"] = question_data.get("acceptable_alternatives", q.get("acceptable_alternatives"))
                    q["difficulty"] = question_data.get("difficulty", q.get("difficulty"))
                    q["requires_diagram"] = bool(question_data.get("requires_diagram", False))
                    q["requires_numerical"] = bool(question_data.get("requires_numerical", False))
                    if question_data.get("question_image_url"):
                        q["question_image_url"] = question_data["question_image_url"]
                    if question_data.get("criteria"):
                        q["marking_criteria"] = question_data["criteria"]
                        q["criteria"] = question_data["criteria"]
                    return True, "Question updated (Local mode)."
            return False, "Question not found."
        return False, "Assessment not found."

    @classmethod
    def delete_question(cls, assessment_id: str, question_id: str) -> Tuple[bool, str]:
        """Deletes a question from an assessment."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                supabase.table("questions").delete().eq("id", question_id).execute()
                return True, "Question deleted successfully."
            except Exception as e:
                logger.error(f"Error deleting question: {e}")
                return False, str(e)

        if assessment_id in _local_questions:
            _local_questions[assessment_id] = [q for q in _local_questions[assessment_id] if q.get("id") != question_id]
            return True, "Question deleted (Local mode)."
        return False, "Assessment not found."

    @classmethod
    def _save_questions(cls, supabase, assessment_id: str, questions: List[Dict[str, Any]]):
        """Helper to insert questions and their rubric criteria."""
        for idx, q in enumerate(questions, start=1):
            q_row = {
                "assessment_id": assessment_id,
                "question_number": q.get("question_number", str(idx)),
                "display_order": idx,
                "question_text": q.get("question_text", ""),
                "max_marks": float(q.get("max_marks", 5.0)),
                "model_answer": q.get("model_answer", ""),
                "acceptable_alternatives": q.get("acceptable_alternatives", ""),
                "difficulty": q.get("difficulty", "medium"),
                "requires_diagram": q.get("requires_diagram", False),
                "requires_numerical": q.get("requires_numerical", False),
                "question_image_url": q.get("question_image_url", ""),
                "question_image_path": q.get("question_image_path", "")
            }
            res = supabase.table("questions").insert(q_row).execute()
            if res.data:
                q_id = res.data[0]["id"]
                criteria = q.get("criteria", [])
                for c_idx, c in enumerate(criteria, start=1):
                    c_row = {
                        "question_id": q_id,
                        "criterion_order": c_idx,
                        "criterion_title": c.get("criterion_title", f"Criterion {c_idx}"),
                        "max_marks": float(c.get("max_marks", 1.0)),
                        "description": c.get("description", "")
                    }
                    supabase.table("marking_criteria").insert(c_row).execute()

    @classmethod
    def _seed_default_assessment(cls):
        """Seeds default BEA Assessment 1 for Diploma Students."""
        asm_id = "bea-test-unit-001"
        _local_assessments.append({
            "id": asm_id,
            "title": "Slip Test 1: BJT Fundamentals & CE Configuration",
            "assessment_type": "slip_test",
            "subject_code": "BEA (MEE-105)",
            "assessment_date": str(date.today()),
            "max_marks": 20.0,
            "pass_percentage": 35.0,
            "instructions": "Answer all questions. Draw neat labeled circuit diagrams showing terminal currents and polarities.",
            "status": "published",
            "allow_submissions": True,
            "results_published": True
        })

        _local_questions[asm_id] = [
            {
                "id": f"{asm_id}-q1",
                "question_number": "1",
                "display_order": 1,
                "question_text": "Draw the circuit diagram of an NPN Transistor in Common Emitter (CE) configuration with input and output biasing circuits. Label all currents (IB, IC, IE) and voltages (VBE, VCE). Refer to the circuit diagram below if needed.",
                "max_marks": 5.0,
                "model_answer": "Circuit showing NPN transistor with emitter grounded/common. Base-emitter forward biased with VBB and resistor RB. Collector-emitter reverse biased with VCC and load resistor RC. Currents indicated: IE = IB + IC.",
                "acceptable_alternatives": "PNP transistor in CE with reversed polarities is also accepted.",
                "difficulty": "medium",
                "requires_diagram": True,
                "requires_numerical": False,
                "question_image_url": "/static/images/bjt_ce_circuit.svg",
                "criteria": [
                    {"criterion_title": "Correct NPN Transistor symbol & terminal identification", "max_marks": 1.5, "description": "Arrow outwards on emitter terminal."},
                    {"criterion_title": "Biasing polarities (Forward Base, Reverse Collector)", "max_marks": 1.5, "description": "VBB forward bias and VCC reverse bias."},
                    {"criterion_title": "Current directions and voltage labels (IB, IC, IE, VBE, VCE)", "max_marks": 2.0, "description": "Correct application of Kirchhoff's Current Law: IE = IB + IC."}
                ]
            },
            {
                "id": f"{asm_id}-q2",
                "question_number": "2",
                "display_order": 2,
                "question_text": "Define Transistor alpha (α) and beta (β). Derive the mathematical relationship connecting α and β.",
                "max_marks": 5.0,
                "model_answer": "α = IC / IE (Common Base DC current gain). β = IC / IB (Common Emitter DC current gain). Since IE = IB + IC, divide by IC: IE/IC = IB/IC + 1 => 1/α = 1/β + 1 => 1/α = (1 + β)/β => α = β / (1 + β), or β = α / (1 - α).",
                "acceptable_alternatives": "Starting from β definition and substituting IC = α*IE is acceptable.",
                "difficulty": "easy",
                "requires_diagram": False,
                "requires_numerical": False,
                "criteria": [
                    {"criterion_title": "Definitions of α and β with typical ranges", "max_marks": 1.5, "description": "α (0.95 to 0.998) and β (20 to 500)."},
                    {"criterion_title": "Current relation IE = IB + IC", "max_marks": 1.0, "description": "Fundamental transistor current equation."},
                    {"criterion_title": "Step-by-step derivation to β = α / (1 - α)", "max_marks": 2.5, "description": "Algebraic steps clearly written."}
                ]
            },
            {
                "id": f"{asm_id}-q3",
                "question_number": "3",
                "display_order": 3,
                "question_text": "In a CE transistor amplifier circuit, the base current IB = 25 µA and the collector current IC = 4.75 mA. Calculate: (i) Emitter current IE, and (ii) Current gain beta (β).",
                "max_marks": 5.0,
                "model_answer": "(i) IE = IB + IC = 0.025 mA + 4.75 mA = 4.775 mA. (ii) β = IC / IB = 4.75 mA / 0.025 mA = 190.",
                "acceptable_alternatives": "Calculating β first and then IE = (1+β)*IB is completely acceptable.",
                "difficulty": "medium",
                "requires_diagram": False,
                "requires_numerical": True,
                "criteria": [
                    {"criterion_title": "Formula for Emitter current IE", "max_marks": 1.0, "description": "IE = IB + IC."},
                    {"criterion_title": "Calculation of IE with correct units (4.775 mA)", "max_marks": 1.5, "description": "Accurate unit conversion (µA to mA)."},
                    {"criterion_title": "Formula for β and calculation (190, dimensionless)", "max_marks": 2.5, "description": "β = IC / IB = 190."}
                ]
            },
            {
                "id": f"{asm_id}-q4",
                "question_number": "4",
                "display_order": 4,
                "question_text": "Sketch the input and output characteristic curves of a BJT in CE configuration. Identify the Cut-off, Active, and Saturation operating regions on the output characteristics.",
                "max_marks": 5.0,
                "model_answer": "Input characteristics: IB vs VBE (diode-like curve with knee voltage ~0.7V for Silicon). Output characteristics: IC vs VCE for different IB curves. Active region: VCE > VCE(sat), horizontal flat lines. Saturation region: steep vertical rise near origin. Cut-off region: region below IB = 0.",
                "acceptable_alternatives": "Germanium knee voltage ~0.3V accepted if noted.",
                "difficulty": "hard",
                "requires_diagram": True,
                "requires_numerical": False,
                "criteria": [
                    {"criterion_title": "Input characteristics curve (IB vs VBE)", "max_marks": 1.5, "description": "Proper axes and knee voltage shown."},
                    {"criterion_title": "Output characteristics family of curves (IC vs VCE)", "max_marks": 1.5, "description": "Multiple IB curves with units."},
                    {"criterion_title": "Identification of Cut-off, Active, and Saturation regions", "max_marks": 2.0, "description": "Clear demarcation of all 3 regions."}
                ]
            }
        ]
