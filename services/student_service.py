import os
import io
import csv
import logging
from typing import List, Dict, Any, Tuple, Optional
from config import Config
from database.db_manager import db_manager

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger("bea.student_service")

# Standard expected headers
STANDARD_HEADERS = [
    "student_name", "pin", "academic_year", "semester", "branch", "section", "contact_phone", "contact_email"
]

class StudentService:
    """
    Handles student registration, Excel & CSV imports with preview,
    duplicate PIN detection, validation reports, and template generation.
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
            "Student Name", "PIN", "Academic Year", "Semester", "Branch", "Section", "Contact Phone", "Contact Email"
        ]
        ws.append(headers)

        # Style header row
        header_fill = openpyxl.styles.PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = openpyxl.styles.Font(color="FFFFFF", bold=True)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 22

        # Sample rows matching Diploma ECE roster
        sample_rows = [
            ["KASHABOINA PRANAVI", "26054-ES-041", "2026-2027", "Semester 1", "ECE", "A", "9502210435", "pranavi@example.com"],
            ["A SUJATHA", "26054-CPS-001", "2026-2027", "Semester 1", "ECE", "A", "6305307638", "sujatha@example.com"],
            ["BADAVATH ROHITH RAJ", "26054-CPS-005", "2026-2027", "Semester 1", "ECE", "A", "8522878783", "rohith@example.com"],
            ["LOLABHATTU SAI SATWIK", "26054-SCT-032", "2026-2027", "Semester 1", "ECE", "A", "9866100836", "satwik@example.com"]
        ]
        for row in sample_rows:
            ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @classmethod
    def parse_file(cls, file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses Excel (.xlsx) or CSV files, automatically mapping headers
        (including APAAR / State Board formats like REGN_NO, AADHAAR NAME).
        Returns: (valid_rows, invalid_rows)
        """
        raw_rows = []
        is_csv = filename.lower().endswith(".csv")

        if is_csv:
            try:
                content = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if rows:
                raw_headers = [h.strip() for h in rows[0]]
                for line in rows[1:]:
                    if any(cell.strip() for cell in line):
                        raw_rows.append(dict(zip(raw_headers, [c.strip() for c in line])))
        else:
            if not OPENPYXL_AVAILABLE:
                raise RuntimeError("openpyxl is required to parse Excel files.")
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if rows:
                raw_headers = [str(h).strip() if h is not None else "" for h in rows[0]]
                for line in rows[1:]:
                    if any(c is not None and str(c).strip() for c in line):
                        row_dict = {}
                        for i, h in enumerate(raw_headers):
                            if i < len(line):
                                val = line[i]
                                row_dict[h] = str(val).strip() if val is not None else ""
                        raw_rows.append(row_dict)

        valid_rows: List[Dict[str, Any]] = []
        invalid_rows: List[Dict[str, Any]] = []
        seen_pins = set()

        for idx, row in enumerate(raw_rows, start=2):
            # Normalize field names
            normalized = {}
            for k, v in row.items():
                clean_k = k.strip().upper().replace(" ", "_").replace("-", "_")
                normalized[clean_k] = v

            # Resolve PIN
            pin = (
                normalized.get("PIN") or 
                normalized.get("REGN_NO") or 
                normalized.get("RROLL") or 
                normalized.get("ROLL_NO") or 
                normalized.get("STUDENT_PIN") or ""
            ).strip().upper()

            # Resolve Name
            name = (
                normalized.get("STUDENT_NAME") or 
                normalized.get("NAME") or 
                normalized.get("AADHAAR_NAME") or 
                normalized.get("FULL_NAME") or ""
            ).strip()

            academic_year = normalized.get("ACADEMIC_YEAR") or "2026-2027"
            semester = normalized.get("SEMESTER") or "Semester 1"
            branch = normalized.get("BRANCH") or "ECE"
            section = normalized.get("SECTION") or "A"
            phone = normalized.get("CONTACT_PHONE") or normalized.get("MOBILE") or ""
            email = normalized.get("CONTACT_EMAIL") or ""

            # Validation checks
            errors = []
            if not pin:
                errors.append("PIN is missing.")
            elif pin in seen_pins:
                errors.append(f"Duplicate PIN '{pin}' found within this file.")
            if not name:
                errors.append("Student Name is missing.")

            if errors:
                invalid_rows.append({
                    "row_number": idx,
                    "pin": pin,
                    "name": name,
                    "errors": errors,
                    "raw_data": row
                })
            else:
                seen_pins.add(pin)
                valid_rows.append({
                    "row_number": idx,
                    "pin": pin,
                    "full_name": name,
                    "academic_year": academic_year,
                    "semester": semester,
                    "branch": branch,
                    "section": section,
                    "contact_phone": phone,
                    "contact_email": email,
                    "is_active": True
                })

        return valid_rows, invalid_rows

    @classmethod
    def import_students(cls, student_records: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            # Local / simulation mode
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
    def get_all_students(cls) -> List[Dict[str, Any]]:
        """Retrieves list of students for teacher view."""
        supabase = db_manager.get_supabase(use_service_role=True)
        if supabase:
            try:
                res = supabase.table("students").select("*").order("pin").execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Error fetching students: {e}")
        return []
