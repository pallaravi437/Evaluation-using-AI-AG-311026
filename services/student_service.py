import os
import io
import csv
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from config import Config
from database.db_manager import db_manager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_STORE_DIR = os.path.join(BASE_DIR, "database", "local_store")
STUDENT_REGISTRATIONS_FILE = os.path.join(LOCAL_STORE_DIR, "student_registrations.json")

os.makedirs(LOCAL_STORE_DIR, exist_ok=True)

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

import re

logger = logging.getLogger("bea.student_service")

# In-memory store for local mode
_local_students: List[Dict[str, Any]] = [
    {
        "id": "st-demo-001",
        "pin": "26054-ES-041",
        "full_name": "KASHABOINA PRANAVI",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "A",
        "contact_phone": "9502210435",
        "contact_email": "pranavi@example.com",
        "is_active": True
    },
    {
        "id": "st-demo-002",
        "pin": "26054-CPS-001",
        "full_name": "A SUJATHA",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "A",
        "contact_phone": "6305307638",
        "contact_email": "sujatha@example.com",
        "is_active": True
    },
    {
        "id": "st-demo-003",
        "pin": "26054-CPS-005",
        "full_name": "BADAVATH ROHITH RAJ",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "A",
        "contact_phone": "8522878783",
        "contact_email": "rohith@example.com",
        "is_active": True
    },
    {
        "id": "st-demo-004",
        "pin": "26054-SCT-032",
        "full_name": "LOLABHATTU SAI SATWIK",
        "academic_year": "2026-2027",
        "semester": "Semester 1",
        "branch": "ECE",
        "section": "A",
        "contact_phone": "9866100836",
        "contact_email": "satwik@example.com",
        "is_active": True
    }
]

class StudentService:
    """
    Handles student registration, Excel, CSV, and MS Word (.docx) imports with preview,
    intelligent header banner detection, duplicate PIN detection, validation reports,
    and template generation.
    """

    @staticmethod
    def generate_excel_template() -> bytes:
        """Generates a downloadable Excel template for student enrollment."""
        if not OPENPYXL_AVAILABLE:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Student Name", "PIN", "Academic Year", "Semester", "Branch", "Section", "Contact Phone", "Contact Email"])
            writer.writerow(["KASHABOINA PRANAVI", "26054-ES-041", "2026-2027", "Semester 1", "ECE", "A", "9502210435", "pranavi@example.com"])
            writer.writerow(["A SUJATHA", "26054-CPS-001", "2026-2027", "Semester 1", "ECE", "A", "6305307638", "sujatha@example.com"])
            return output.getvalue().encode("utf-8")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Roster Template"

        headers = [
            "PIN", "Student Name", "Academic Year", "Semester", "Branch", "Section", "Contact Phone", "Contact Email"
        ]
        ws.append(headers)

        header_fill = openpyxl.styles.PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = openpyxl.styles.Font(color="FFFFFF", bold=True)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 24

        sample_rows = [
            ["26054-ES-041", "KASHABOINA PRANAVI", "2026-2027", "Semester 1", "ECE", "A", "9502210435", "pranavi@example.com"],
            ["26054-CPS-001", "A SUJATHA", "2026-2027", "Semester 1", "ECE", "A", "6305307638", "sujatha@example.com"],
            ["26054-CPS-005", "BADAVATH ROHITH RAJ", "2026-2027", "Semester 1", "ECE", "A", "8522878783", "rohith@example.com"],
            ["26054-SCT-032", "LOLABHATTU SAI SATWIK", "2026-2027", "Semester 1", "ECE", "A", "9866100836", "satwik@example.com"]
        ]
        for row in sample_rows:
            ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def generate_word_template() -> bytes:
        """Generates a downloadable Microsoft Word (.docx) template for student enrollment."""
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx is required to generate Word template.")

        doc = docx.Document()

        # Set title & instructions
        title = doc.add_heading("BEA AI Assessment - Student Roster Template", level=1)
        doc.add_paragraph("Subject: Basic Electronics & Amplifiers (C26_MEE-105) | Diploma 60–70 Student Batch")
        doc.add_paragraph("Instructions: Fill in the student details in the table below. The AI evaluator will automatically parse PIN, Name, and optional contact details.")

        headers = ["PIN", "Student Name", "Academic Year", "Semester", "Branch", "Section", "Contact Phone", "Contact Email"]
        sample_rows = [
            ["26054-ES-041", "KASHABOINA PRANAVI", "2026-2027", "Semester 1", "ECE", "A", "9502210435", "pranavi@example.com"],
            ["26054-CPS-001", "A SUJATHA", "2026-2027", "Semester 1", "ECE", "A", "6305307638", "sujatha@example.com"],
            ["26054-CPS-005", "BADAVATH ROHITH RAJ", "2026-2027", "Semester 1", "ECE", "A", "8522878783", "rohith@example.com"],
            ["26054-SCT-032", "LOLABHATTU SAI SATWIK", "2026-2027", "Semester 1", "ECE", "A", "9866100836", "satwik@example.com"]
        ]

        table = doc.add_table(rows=1 + len(sample_rows), cols=len(headers))
        table.style = 'Table Grid'

        # Style header row
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            hdr_cells[i].text = header_text
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        # Populate sample rows
        for row_idx, data_row in enumerate(sample_rows, start=1):
            row_cells = table.rows[row_idx].cells
            for col_idx, val in enumerate(data_row):
                row_cells[col_idx].text = str(val)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    @classmethod
    def _extract_grid_from_file(cls, file_bytes: bytes, filename: str) -> List[List[str]]:
        """
        Extracts a raw 2D grid of string cells from .xlsx, .csv, or MS Word (.docx / .doc).
        """
        lower_name = filename.lower()

        # 1. CSV
        if lower_name.endswith(".csv"):
            try:
                content = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1", errors="ignore")
            reader = csv.reader(io.StringIO(content))
            return [[str(c).strip() for c in row] for row in reader if any(str(c).strip() for c in row)]

        # 2. MS Word (.docx)
        if lower_name.endswith(".docx"):
            if not DOCX_AVAILABLE:
                raise RuntimeError("python-docx library is required to parse .docx documents.")
            doc = docx.Document(io.BytesIO(file_bytes))
            grid: List[List[str]] = []

            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    row_vals = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    if any(row_vals):
                        grid.append(row_vals)

            # If no tables found, extract from lines/paragraphs
            if not grid:
                for p in doc.paragraphs:
                    line = p.text.strip()
                    if line:
                        # Split by tabs or commas
                        if "\t" in line:
                            parts = [c.strip() for c in line.split("\t")]
                        elif "," in line:
                            parts = [c.strip() for c in line.split(",")]
                        elif "|" in line:
                            parts = [c.strip() for c in line.split("|")]
                        else:
                            parts = [line]
                        if any(parts):
                            grid.append(parts)
            return grid

        # 3. Legacy Word (.doc) fallback
        if lower_name.endswith(".doc"):
            # Try docx first in case it's a docx renamed to .doc
            try:
                if DOCX_AVAILABLE:
                    doc = docx.Document(io.BytesIO(file_bytes))
                    grid = []
                    for table in doc.tables:
                        for row in table.rows:
                            row_vals = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                            if any(row_vals):
                                grid.append(row_vals)
                    if grid:
                        return grid
            except Exception:
                pass

            # Extract text lines using regex from binary streams
            text_chunks = re.findall(rb'[A-Za-z0-9\s,\t\-\.]{4,}', file_bytes)
            grid = []
            for chunk in text_chunks:
                try:
                    line = chunk.decode("ascii", errors="ignore").strip()
                    if "\t" in line:
                        parts = [c.strip() for c in line.split("\t")]
                    elif "," in line:
                        parts = [c.strip() for c in line.split(",")]
                    else:
                        parts = [line]
                    if len(parts) >= 2:
                        grid.append(parts)
                except Exception:
                    continue
            if grid:
                return grid
            raise ValueError("Legacy .doc format could not be converted. Please save the document as .docx or .xlsx and re-upload.")

        # 4. Excel (.xlsx)
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("openpyxl is required to parse Excel files.")
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        grid = []
        for line in ws.iter_rows(values_only=True):
            if any(c is not None and str(c).strip() for c in line):
                grid.append([str(c).strip() if c is not None else "" for c in line])
        return grid

    @classmethod
    def parse_file(cls, file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses Excel (.xlsx), CSV (.csv), or MS Word (.docx / .doc) student rosters.
        Intelligently skips top college headers/banners, fuzzy-maps Board APAAR column names,
        and provides value-based fallback matching if headers are non-standard.
        """
        raw_grid = cls._extract_grid_from_file(file_bytes, filename)
        if not raw_grid:
            return [], [{"row_number": 1, "pin": "N/A", "name": "N/A", "errors": ["File is empty or contains no readable data rows."]}]

        # PIN & Name Match Keywords
        PIN_KEYWORDS = ["PIN", "REGN", "REG_NO", "REGNO", "REGISTRATION", "ROLL", "HTNO", "HALL_TICKET", "HALLTICKET", "ADMISSION", "APAAR", "STUDENT_ID", "ID_NO", "SL_NO", "SNO"]
        NAME_KEYWORDS = ["STUDENT_NAME", "NAME", "CANDIDATE_NAME", "FULL_NAME", "AADHAAR_NAME", "CANDIDATE", "STUDENT"]
        DISQUALIFY_NAME = ["FATHER", "MOTHER", "COLLEGE", "INSTITUTE", "SCHOOL", "BRANCH", "SIGNATURE", "SUBJECT"]

        # Step 1: Detect True Header Row (scan first 15 rows)
        best_header_idx = 0
        best_score = -1

        for r_idx in range(min(15, len(raw_grid))):
            row = raw_grid[r_idx]
            row_text = " ".join(row).upper()
            score = 0

            has_pin_kw = any(kw in row_text for kw in ["PIN", "REGN", "REG", "ROLL", "HTNO", "HALL"])
            has_name_kw = any(kw in row_text for kw in ["NAME", "STUDENT", "CANDIDATE", "AADHAAR"])

            if has_pin_kw and has_name_kw:
                score += 10
            elif has_pin_kw or has_name_kw:
                score += 4

            if any(kw in row_text for kw in ["MOBILE", "PHONE", "BRANCH", "SECTION", "SEMESTER", "SNO", "SL.NO"]):
                score += 2

            if score > best_score:
                best_score = score
                best_header_idx = r_idx

        # If header score is decent, data begins after header row
        header_row = [str(c).strip() for c in raw_grid[best_header_idx]]
        data_rows = raw_grid[best_header_idx + 1:] if best_score >= 4 else raw_grid

        # Step 2: Map column indices from detected header row
        pin_col = None
        name_col = None
        phone_col = None
        email_col = None
        branch_col = None
        year_col = None
        sem_col = None
        sec_col = None

        for col_idx, h in enumerate(header_row):
            h_clean = re.sub(r'[^A-Z0-9]', '_', h.upper().strip())

            # Check PIN
            if pin_col is None:
                if any(kw in h_clean for kw in ["PIN", "REGN", "REG_NO", "REGNO", "REGISTRATION", "ROLL", "HTNO", "HALL_TICKET", "HALLTICKET", "ADMISSION", "APAAR", "STUDENT_ID"]):
                    if "CODE" not in h_clean:
                        pin_col = col_idx

            # Check Name
            if name_col is None:
                if any(kw in h_clean for kw in ["STUDENT_NAME", "NAME", "CANDIDATE", "FULL_NAME", "AADHAAR"]):
                    if not any(dq in h_clean for dq in DISQUALIFY_NAME):
                        name_col = col_idx

            # Check Phone
            if phone_col is None and any(kw in h_clean for kw in ["MOBILE", "PHONE", "CONTACT", "CELL"]):
                phone_col = col_idx

            # Check Email
            if email_col is None and ("EMAIL" in h_clean or "MAIL" in h_clean):
                email_col = col_idx

            # Check Branch
            if branch_col is None and any(kw in h_clean for kw in ["BRANCH", "DEPT", "COURSE"]):
                branch_col = col_idx

            # Check Year
            if year_col is None and any(kw in h_clean for kw in ["ACADEMIC", "YEAR", "BATCH", "AY"]):
                year_col = col_idx

            # Check Semester
            if sem_col is None and ("SEM" in h_clean or "SEMESTER" in h_clean):
                sem_col = col_idx

            # Check Section
            if sec_col is None and ("SEC" in h_clean or "SECTION" in h_clean):
                sec_col = col_idx

        # Step 3: Heuristic Value Fallback if PIN or Name column not found by header
        if pin_col is None or name_col is None:
            max_cols = max(len(r) for r in data_rows) if data_rows else 0
            pin_scores = [0] * max_cols
            name_scores = [0] * max_cols

            for row in data_rows[:15]:
                for c_idx, val in enumerate(row):
                    v_str = str(val).strip()
                    # Check PIN pattern (e.g. 26054-ES-041 or contains digits+hyphens or long digits)
                    if re.search(r'^\d{2,}[A-Za-z0-9-]{3,}$', v_str) or re.search(r'^\d{5,12}$', v_str):
                        pin_scores[c_idx] += 1
                    # Check Name pattern (alphabetic words with spaces, length >= 4)
                    elif re.search(r'^[A-Za-z\s\.]{4,40}$', v_str) and not any(k in v_str.upper() for k in ["ECE", "SEMESTER", "MALE", "FEMALE", "GOVERNMENT"]):
                        name_scores[c_idx] += 1

            if pin_col is None and any(s > 0 for s in pin_scores):
                pin_col = pin_scores.index(max(pin_scores))
            if name_col is None and any(s > 0 for s in name_scores):
                # Ensure name_col != pin_col
                sorted_name_cols = sorted(range(len(name_scores)), key=lambda i: name_scores[i], reverse=True)
                for cand in sorted_name_cols:
                    if cand != pin_col and name_scores[cand] > 0:
                        name_col = cand
                        break

        # Defaults if still unassigned
        if pin_col is None and len(header_row) > 1:
            pin_col = 1 if len(header_row) > 2 else 0
        if name_col is None and len(header_row) > 2:
            name_col = 2 if pin_col == 1 else 1

        # Step 4: Parse & Validate Data Rows
        valid_rows: List[Dict[str, Any]] = []
        invalid_rows: List[Dict[str, Any]] = []
        seen_pins = set()

        for idx, row in enumerate(data_rows, start=best_header_idx + 2):
            if not any(str(c).strip() for c in row):
                continue

            # Extract fields by column index
            pin = (row[pin_col] if pin_col is not None and pin_col < len(row) else "").strip().upper()
            name = (row[name_col] if name_col is not None and name_col < len(row) else "").strip()
            phone = (row[phone_col] if phone_col is not None and phone_col < len(row) else "").strip()
            email = (row[email_col] if email_col is not None and email_col < len(row) else "").strip()
            branch = (row[branch_col] if branch_col is not None and branch_col < len(row) else "ECE").strip() or "ECE"
            acad_year = (row[year_col] if year_col is not None and year_col < len(row) else "2026-2027").strip() or "2026-2027"
            sem = (row[sem_col] if sem_col is not None and sem_col < len(row) else "Semester 1").strip() or "Semester 1"
            sec = (row[sec_col] if sec_col is not None and sec_col < len(row) else "A").strip() or "A"

            # Skip header repeats or footer summary rows
            combined_upper = (pin + " " + name).upper()
            if any(term in combined_upper for term in ["TOTAL STUDENTS", "PRINCIPAL", "HOD SIGNATURE", "PAGE NO", "DATE:"]):
                continue
            if pin in ("PIN", "REGN_NO", "ROLL_NO", "SL_NO", "SNO", "NO") and name in ("STUDENT NAME", "NAME", "NAME OF STUDENT"):
                continue

            errors = []
            if not pin or pin == "N/A":
                errors.append("PIN is missing or empty.")
            elif pin in seen_pins:
                errors.append(f"Duplicate PIN '{pin}' found within this file.")

            if not name or name == "N/A":
                errors.append("Student Name is missing or empty.")

            if errors:
                invalid_rows.append({
                    "row_number": idx,
                    "pin": pin or "N/A",
                    "name": name or "N/A",
                    "errors": errors,
                    "raw_data": row
                })
            else:
                seen_pins.add(pin)
                valid_rows.append({
                    "row_number": idx,
                    "pin": pin,
                    "full_name": name,
                    "academic_year": acad_year,
                    "semester": sem,
                    "branch": branch,
                    "section": sec,
                    "contact_phone": phone,
                    "contact_email": email,
                    "is_active": True
                })

        return valid_rows, invalid_rows

    @classmethod
    def import_students(cls, student_records: List[Dict[str, Any]], teacher_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Safely upserts student records into Supabase without deleting existing students.
        """
        supabase = db_manager.get_supabase(use_service_role=True)
        summary = {
            "total_submitted": len(student_records),
            "inserted": 0,
            "updated": 0,
            "errors": []
        }

        if not supabase:
            # Multi-tenant local storage if teacher_id is a registered tenant
            if teacher_id and teacher_id.startswith("lec-"):
                import uuid
                from services.lecturer_service import LecturerService
                tenant_students = LecturerService.load_tenant_data(teacher_id, "students.json") or []
                existing_pins = {st.get("pin", "").upper(): idx for idx, st in enumerate(tenant_students)}
                for st in student_records:
                    clean_pin = (st.get("pin") or "").strip().upper()
                    if not clean_pin:
                        continue
                    rec = {
                        "id": st.get("id") or f"st-{uuid.uuid4()}",
                        "pin": clean_pin,
                        "full_name": st.get("full_name", "").strip(),
                        "academic_year": st.get("academic_year", "2026-2027"),
                        "semester": st.get("semester", "Semester 1"),
                        "branch": st.get("branch", "ECE"),
                        "section": st.get("section", "A"),
                        "contact_phone": st.get("contact_phone", ""),
                        "contact_email": st.get("contact_email", ""),
                        "is_active": st.get("is_active", True),
                        "created_by": teacher_id
                    }
                    if clean_pin in existing_pins:
                        tenant_students[existing_pins[clean_pin]] = rec
                    else:
                        tenant_students.append(rec)
                        existing_pins[clean_pin] = len(tenant_students) - 1
                    summary["inserted"] += 1
                LecturerService.save_tenant_data(teacher_id, "students.json", tenant_students)
                return summary

            # Global Local / simulation mode
            for st in student_records:
                existing = next((s for s in _local_students if s.get("pin") == st.get("pin")), None)
                if existing:
                    existing.update(st)
                else:
                    st_copy = dict(st)
                    st_copy["id"] = f"st-loc-{len(_local_students)+1}"
                    _local_students.append(st_copy)
            summary["inserted"] = len(student_records)
            return summary

        for st in student_records:
            try:
                record = {
                    "pin": st["pin"],
                    "full_name": st["full_name"],
                    "academic_year": st.get("academic_year", "2026-2027"),
                    "semester": st.get("semester", "Semester 1"),
                    "branch": st.get("branch", "ECE"),
                    "section": st.get("section", "A"),
                    "contact_phone": st.get("contact_phone", ""),
                    "contact_email": st.get("contact_email", ""),
                    "is_active": st.get("is_active", True)
                }

                # Upsert on conflict on pin
                res = supabase.table("students").upsert(
                    record, 
                    on_conflict="pin"
                ).execute()
                
                summary["inserted"] += 1
            except Exception as e:
                summary["errors"].append({"pin": st.get("pin"), "error": str(e)})

        return summary

    @classmethod
    def get_all_students(cls, teacher_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves list of students for teacher view with multi-tenant isolation."""
        if teacher_id and teacher_id.startswith("lec-"):
            from services.lecturer_service import LecturerService
            tenant_students = LecturerService.load_tenant_data(teacher_id, "students.json")
            if isinstance(tenant_students, list):
                return tenant_students
            return []

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("students").select("*").order("pin").execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error fetching students: {e}")
        return _local_students

    @classmethod
    def update_student(cls, student_id: str, student_data: Dict[str, Any], teacher_id: Optional[str] = None) -> Tuple[bool, str]:
        """Updates a student's profile information in Supabase or local store."""
        if teacher_id and teacher_id.startswith("lec-"):
            from services.lecturer_service import LecturerService
            tenant_students = LecturerService.load_tenant_data(teacher_id, "students.json") or []
            updated = False
            for st in tenant_students:
                if st.get("id") == student_id or st.get("pin") == student_id:
                    for k, v in student_data.items():
                        if v is not None:
                            st[k] = v
                    updated = True
                    break
            if updated:
                LecturerService.save_tenant_data(teacher_id, "students.json", tenant_students)
                return True, "Student details updated successfully."
            return False, "Student not found in your roster."

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                record = {
                    "full_name": student_data.get("full_name", "").strip(),
                    "academic_year": student_data.get("academic_year", "2026-2027").strip(),
                    "semester": student_data.get("semester", "Semester 1").strip(),
                    "branch": student_data.get("branch", "ECE").strip(),
                    "section": student_data.get("section", "A").strip(),
                    "contact_phone": student_data.get("contact_phone", "").strip(),
                    "contact_email": student_data.get("contact_email", "").strip(),
                    "is_active": bool(student_data.get("is_active", True))
                }
                if student_data.get("pin"):
                    record["pin"] = student_data["pin"].strip().upper()

                res = supabase.table("students").update(record).eq("id", student_id).execute()
                if not (res.data if hasattr(res, "data") else None):
                    supabase.table("students").update(record).eq("pin", student_id).execute()
                return True, "Student details updated successfully."
            except Exception as e:
                logger.error(f"Error updating student {student_id}: {e}")
                return False, str(e)

        # Local mode
        for st in _local_students:
            if st.get("id") == student_id or st.get("pin") == student_id:
                if student_data.get("pin"):
                    st["pin"] = student_data["pin"].strip().upper()
                if student_data.get("full_name"):
                    st["full_name"] = student_data["full_name"].strip()
                if student_data.get("branch"):
                    st["branch"] = student_data["branch"].strip()
                if student_data.get("section"):
                    st["section"] = student_data["section"].strip()
                if student_data.get("semester"):
                    st["semester"] = student_data["semester"].strip()
                if student_data.get("academic_year"):
                    st["academic_year"] = student_data["academic_year"].strip()
                st["contact_phone"] = student_data.get("contact_phone", "").strip()
                st["contact_email"] = student_data.get("contact_email", "").strip()
                if "is_active" in student_data:
                    st["is_active"] = bool(student_data["is_active"])
                return True, "Student details updated (Local mode)."
        return False, "Student not found."

    @classmethod
    def delete_students(cls, identifiers: List[str], teacher_id: Optional[str] = None) -> Tuple[bool, int, str]:
        """Deletes one or multiple students by ID or PIN with tenant support."""
        if not identifiers:
            return False, 0, "No students selected for deletion."

        clean_ids = [str(i).strip() for i in identifiers if str(i).strip()]
        if not clean_ids:
            return False, 0, "No valid student identifiers provided."

        if teacher_id and teacher_id.startswith("lec-"):
            from services.lecturer_service import LecturerService
            tenant_students = LecturerService.load_tenant_data(teacher_id, "students.json") or []
            id_set = set(clean_ids)
            filtered = [st for st in tenant_students if st.get("id") not in id_set and st.get("pin") not in id_set]
            deleted_count = len(tenant_students) - len(filtered)
            LecturerService.save_tenant_data(teacher_id, "students.json", filtered)
            return True, deleted_count, f"Successfully deleted {deleted_count} student(s) from your tenant roster."

        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                # Delete by ID and PIN
                supabase.table("students").delete().in_("id", clean_ids).execute()
                supabase.table("students").delete().in_("pin", clean_ids).execute()
                return True, len(clean_ids), f"Successfully deleted {len(clean_ids)} student(s)."
            except Exception as e:
                logger.error(f"Error deleting students in Supabase: {e}")
                return False, 0, str(e)

        # Local mode
        global _local_students
        initial_count = len(_local_students)
        _local_students = [
            st for st in _local_students 
            if st.get("id") not in clean_ids and st.get("pin") not in clean_ids
        ]
        deleted_count = initial_count - len(_local_students)
        return True, deleted_count, f"Successfully deleted {deleted_count} student(s) (Local mode)."

    # -------------------------------------------------------------------------
    # STUDENT SELF-REGISTRATION & LECTURER APPROVAL WORKFLOW
    # -------------------------------------------------------------------------

    @classmethod
    def _load_registrations(cls) -> List[Dict[str, Any]]:
        """Loads student registration requests from JSON file."""
        if not os.path.exists(STUDENT_REGISTRATIONS_FILE):
            return []
        try:
            with open(STUDENT_REGISTRATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading student registrations: {e}")
            return []

    @classmethod
    def _save_registrations(cls, registrations: List[Dict[str, Any]]) -> bool:
        """Saves student registration requests to JSON file."""
        try:
            with open(STUDENT_REGISTRATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(registrations, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving student registrations: {e}")
            return False

    @classmethod
    def register_student(
        cls,
        full_name: str,
        pin: str,
        lecturer_id: str,
        branch: str = "ECE",
        semester: str = "Semester 1",
        section: str = "A",
        contact_phone: str = "",
        contact_email: str = ""
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Registers a student for enrollment under a chosen lecturer.
        Status is initially 'pending' until the chosen lecturer grants approval.
        """
        clean_name = (full_name or "").strip()
        clean_pin = (pin or "").strip().upper()
        clean_lec_id = (lecturer_id or "").strip()

        if not clean_name or not clean_pin:
            return False, None, "Student Full Name and unique PIN are required."

        if not clean_lec_id:
            return False, None, "Please select an available lecturer from the options."

        # Fetch lecturer details
        from services.lecturer_service import LecturerService
        lec_info = LecturerService.get_lecturer_by_id(clean_lec_id)
        if not lec_info and clean_lec_id in ("teacher", "default-teacher", "11111111-1111-1111-1111-111111111111"):
            lec_info = {
                "id": "11111111-1111-1111-1111-111111111111",
                "full_name": "Prof. BEA Department Faculty",
                "subject": "Basic Electronic Engineering (BEA)",
                "specialization": "Electronics & Communication Engineering"
            }

        if not lec_info:
            return False, None, "Selected lecturer not found. Please choose a valid lecturer."

        registrations = cls._load_registrations()

        # Check for existing registrations for this PIN
        for r in registrations:
            if r.get("pin", "").upper() == clean_pin:
                if r.get("status") == "approved":
                    return False, None, f"Student PIN '{clean_pin}' is already enrolled with Lecturer {r.get('lecturer_name')}."
                elif r.get("status") == "pending" and r.get("lecturer_id") == clean_lec_id:
                    return False, None, f"A registration for PIN '{clean_pin}' is already pending approval with Lecturer {lec_info.get('full_name')}."

        reg_id = f"st-reg-{uuid.uuid4()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "id": reg_id,
            "pin": clean_pin,
            "pin_normalized": clean_pin,
            "full_name": clean_name,
            "branch": branch.strip() or "ECE",
            "semester": semester.strip() or "Semester 1",
            "section": section.strip() or "A",
            "contact_phone": contact_phone.strip(),
            "contact_email": contact_email.strip(),
            "lecturer_id": clean_lec_id,
            "lecturer_name": lec_info.get("full_name", "Faculty"),
            "lecturer_subject": lec_info.get("subject", "General"),
            "status": "pending",
            "is_approved": False,
            "is_active": False,
            "registered_at": now_iso,
            "approved_at": None,
            "rejection_reason": None
        }

        # Remove any old rejected registration for this PIN
        registrations = [r for r in registrations if not (r.get("pin", "").upper() == clean_pin and r.get("status") == "rejected")]
        registrations.append(record)
        cls._save_registrations(registrations)

        logger.info(f"New student registration: {clean_name} ({clean_pin}) assigned to lecturer {lec_info.get('full_name')}")
        return True, record, f"Registration submitted! Waiting for approval from Lecturer '{lec_info.get('full_name')}'. Once approved, you will be added to their student list and can access assessments."

    DEFAULT_TEACHER_IDS = {"teacher", "default-teacher", "11111111-1111-1111-1111-111111111111"}

    @classmethod
    def get_pending_students_for_lecturer(cls, teacher_id: str) -> List[Dict[str, Any]]:
        """Returns all students waiting for this lecturer's approval."""
        if not teacher_id:
            return []
        registrations = cls._load_registrations()
        return [
            r for r in registrations
            if r.get("status") == "pending" and (
                r.get("lecturer_id") == teacher_id or 
                (teacher_id in cls.DEFAULT_TEACHER_IDS and r.get("lecturer_id") in cls.DEFAULT_TEACHER_IDS)
            )
        ]

    @classmethod
    def get_registration_by_pin(cls, pin: str) -> Optional[Dict[str, Any]]:
        """Finds registration record by PIN."""
        clean_pin = (pin or "").strip().upper()
        if not clean_pin:
            return None
        registrations = cls._load_registrations()
        for r in reversed(registrations):
            if r.get("pin", "").upper() == clean_pin:
                return r
        return None

    @classmethod
    def approve_student_registration(cls, registration_id: str, teacher_id: str) -> Tuple[bool, str]:
        """
        Lecturer approves student. Student is immediately added to the lecturer's student roster.
        """
        registrations = cls._load_registrations()
        match = None
        for r in registrations:
            if r.get("id") == registration_id:
                match = r
                break

        if not match:
            return False, "Registration request not found."

        # Verify authority
        if teacher_id and teacher_id != match.get("lecturer_id") and not (teacher_id in cls.DEFAULT_TEACHER_IDS and match.get("lecturer_id") in cls.DEFAULT_TEACHER_IDS) and teacher_id not in ("admin", "admin-00000000-0000-0000-0000-000000000000"):
            return False, "You do not have authority to approve students for another lecturer."

        now_iso = datetime.now(timezone.utc).isoformat()
        match["status"] = "approved"
        match["is_approved"] = True
        match["is_active"] = True
        match["approved_at"] = now_iso
        cls._save_registrations(registrations)

        # Build student roster entry
        student_entry = {
            "id": match["id"],
            "pin": match["pin"],
            "full_name": match["full_name"],
            "academic_year": "2026-2027",
            "semester": match.get("semester", "Semester 1"),
            "branch": match.get("branch", "ECE"),
            "section": match.get("section", "A"),
            "contact_phone": match.get("contact_phone", ""),
            "contact_email": match.get("contact_email", ""),
            "is_active": True,
            "enrolled_at": now_iso
        }

        # Add to lecturer tenant students roster
        target_tid = match.get("lecturer_id")
        if target_tid and target_tid.startswith("lec-"):
            from services.lecturer_service import LecturerService
            tenant_students = LecturerService.load_tenant_data(target_tid, "students.json") or []
            tenant_students = [s for s in tenant_students if s.get("pin", "").upper() != match["pin"]]
            tenant_students.append(student_entry)
            LecturerService.save_tenant_data(target_tid, "students.json", tenant_students)
        else:
            # Add to local students if default lecturer
            global _local_students
            _local_students = [s for s in _local_students if s.get("pin", "").upper() != match["pin"]]
            _local_students.append(student_entry)

        # Also sync to Supabase if connected
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                supabase.table("students").upsert({
                    "pin": match["pin"],
                    "full_name": match["full_name"],
                    "branch": match.get("branch", "ECE"),
                    "semester": match.get("semester", "Semester 1"),
                    "section": match.get("section", "A"),
                    "contact_phone": match.get("contact_phone", ""),
                    "contact_email": match.get("contact_email", ""),
                    "is_active": True
                }, on_conflict="pin").execute()
            except Exception as e:
                logger.debug(f"Supabase student sync on approval: {e}")

        logger.info(f"Student {match['full_name']} ({match['pin']}) approved by lecturer {teacher_id}.")
        return True, f"Approved {match['full_name']} ({match['pin']})! Student has been added to your roster and can now access your assessments."

    @classmethod
    def reject_student_registration(cls, registration_id: str, teacher_id: str, reason: str = "") -> Tuple[bool, str]:
        """Lecturer rejects student registration."""
        registrations = cls._load_registrations()
        match = None
        for r in registrations:
            if r.get("id") == registration_id:
                match = r
                break

        if not match:
            return False, "Registration request not found."

        match["status"] = "rejected"
        match["is_approved"] = False
        match["is_active"] = False
        match["rejection_reason"] = reason.strip() or "Registration rejected by lecturer."
        cls._save_registrations(registrations)

        logger.info(f"Student registration {registration_id} rejected by lecturer {teacher_id}.")
        return True, f"Registration for {match['full_name']} ({match['pin']}) has been rejected."
