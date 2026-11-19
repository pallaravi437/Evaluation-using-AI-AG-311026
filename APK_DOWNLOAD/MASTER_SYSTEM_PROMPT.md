# Master Prompt: Fully Online AI-Enabled Assessment & Evaluation Platform

Use the following complete specification prompt to build, replicate, or extend the entire **AI-Enabled Online Evaluator & Examination Platform** from scratch.

---

```markdown
You are an expert full-stack AI system architect. Build a production-grade, multi-tenant AI-Powered Assessment and Handwritten Answer Evaluation Platform (Online AI Evaluator) using Python Flask, TailwindCSS, Google Gemini AI, and a resilient Universal Storage Engine.

---

## 1. System Architecture & Tech Stack

- **Framework:** Python 3.11+ / Flask with modular Blueprints (`admin`, `teacher`, `student`, `api`).
- **Production Server:** Gunicorn WSGI (`gunicorn app:app`).
- **Frontend:** Jinja2 templates, TailwindCSS / Bootstrap styling, Chart.js for analytics, FontAwesome icons, drag-and-drop file uploaders, and camera capture.
- **AI Engine:** Google Gemini API (`gemini-1.5-flash`, `gemini-2.0-flash`, or `gemini-pro`) with an automated Fallback Heuristic Rule Engine (ensures zero-downtime evaluation even if quotas are exhausted or offline).
- **Vision / OCR:** Pillow (PIL) image preprocessing (EXIF auto-orientation, grayscale binarization, contrast normalization, noise removal) + layout-aware document question parsing.
- **Storage Layer:** Universal Data Manager with fallback hierarchy:
  1. Multi-Tenant Local JSON Flat-File Store (guaranteed zero-dependency runtime)
  2. SQLite (`database/evaluator.db`)
  3. PostgreSQL / Cloud SQL ready
  4. Firebase / Google Cloud Storage ready.

---

## 2. Multi-Role Hierarchy & Security

Enforce strict role separation across three distinct roles:

### Role 1: Administrator (Superuser)
- **Primary Function:** Acts strictly as the **Lecturer Approval Authority**.
- **Credentials:** Default Superuser (`admin` / `87654321` or `admin@bea.edu`).
- **Capabilities:**
  - Review all registered lecturers filtered by status (`Pending`, `Approved`, `Suspended`).
  - Approve pending lecturers with one click, activating their private tenant workspace.
  - Suspend or reject lecturer accounts with logged audit trails.
  - Admin cannot tamper with lecturer questions or student exam answers.

### Role 2: Lecturer / Teacher (Multi-Tenant Faculty)
- **Registration Flow:** Self-signup at `/teacher/signup`. Account remains pending until approved by the Administrator.
- **Tenant Isolation:** Every approved lecturer receives a unique tenant ID (`lec-<uuid>`). All assessments, questions, syllabus materials, student rosters, and submissions are saved in their private directory (`database/local_store/tenants/<tenant_id>/`).
- **Capabilities:**
  - **Student Approval Queue (`/teacher/students`):** Review incoming student signups who selected this lecturer; approve or reject them.
  - **Student Roster Management:** Batch upload Excel (.xlsx) / CSV student lists with validation previews, select-all checkboxes, and batch deletion.
  - **Curriculum & Materials:** Upload syllabi, lecture notes (PDF/Word), and reference materials.
  - **AI Question Paper Generator:** Generate questions (MCQs, Numericals, Derivations, Diagrammatic) based on curriculum topics.
  - **Document & Form Ingestion:** Parse PDF/Word question papers (stripping out college exam headers and student signature boxes) or import directly from Google Forms URLs.
  - **Assessment Management:** Set marks, passing marks, time limits, question weights, step-marking rubrics, and model solutions.
  - **Analytics & Gradebook:** Score distribution charts, class averages, high/low performers, topic weakness heatmaps, and downloadable CSV grade sheets.

### Role 3: Student (Examinee)
- **Registration Flow:** Self-signup at `/student/signup` requiring Full Name, unique PIN, Branch, Semester, Section, and selection from an **"Available Approved Lecturers"** dropdown. Account is placed in "Pending Approval" until the chosen lecturer approves them.
- **Capabilities:**
  - Login at `/student/login` with Name and PIN.
  - **Dashboard (`/student/dashboard`):** View assessments assigned exclusively by their approved lecturer.
  - **Exam Interface:** Real-time countdown timer, question navigation, formula prompts, and diagram requirements.
  - **Answer Submission:** Type answers directly or upload photos of handwritten sheets via file upload or camera capture (with auto-rotation).
  - **Instant AI Feedback:** Receive immediate rubric breakdown, step-by-step mark distribution, missing keywords, calculation checks, and actionable tips.

---

## 3. AI Evaluation & Grading Pipeline

Implement `services/ai_service.py` and `services/evaluation_service.py`:
1. **Preprocessing:** Clean and auto-orient student photos; perform handwriting extraction and LaTeX/mathematical notation normalization.
2. **Rubric Grading:**
   - Conceptual Understanding (40%)
   - Step-by-Step Derivation & Calculation (30%)
   - Keyword & Terminology Accuracy (15%)
   - Diagrammatic & Circuit Accuracy (15%)
3. **Resilient Fallback:** When Gemini API is unavailable or rate-limited (HTTP 429), fall back seamlessly to the internal Heuristic Rule Evaluator (keyword density, numerical tolerance window ±2%, length-normalized step checks) so student submissions are never rejected.

---

## 4. Multi-Tenant Storage Layout

```text
database/
├── local_store/
│   ├── lecturers.json              # Lecturer accounts and approval statuses
│   ├── student_registrations.json  # Student signup applications
│   ├── students_master.json        # Global student registry
│   └── tenants/
│       ├── 11111111-1111-1111-1111-111111111111/   # Default faculty workspace
│       │   ├── assessments.json
│       │   ├── materials.json
│       │   ├── students.json
│       │   └── submissions.json
│       └── lec-<uuid>/                             # Individual lecturer workspaces
│           ├── assessments.json
│           ├── materials.json
│           ├── students.json
│           └── submissions.json
```

---

## 5. Deployment Specifications

- **Production Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
- **Render / Cloud Deployment:** `render.yaml` with root directory set to `GITHUB MOVE` or project root.
- **Automated Verification:** Full Pytest test suite ensuring 100% pass rate across multi-tenancy, admin approvals, student workflows, and universal storage.
```

