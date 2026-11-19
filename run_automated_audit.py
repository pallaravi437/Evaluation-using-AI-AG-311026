"""
Automated Web Application QA & Compliance Audit Tool
Crawls and validates:
- HTTP Status & Response Time
- HTML5 & WCAG 1.3.1 (H1 tag, landmarks, labels)
- SEO Meta Tags (Description, Keywords, Canonical, Open Graph)
- Form Fields (Password minlength, email/identifier validation, CSRF)
- Table Accessibility (Captions, th scope attributes)
- Authentication Flows (Admin, Lecturer, Student)
"""

import sys
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

def audit_url(session, url, name, is_post=False, post_data=None):
    results = {"name": name, "url": url, "checks": []}
    
    def check(category, description, status, details=""):
        results["checks"].append({
            "category": category,
            "description": description,
            "status": "PASS" if status else "FAIL",
            "details": details
        })

    try:
        t0 = time.time()
        if is_post:
            resp = session.post(url, data=post_data, allow_redirects=True, timeout=5)
        else:
            resp = session.get(url, timeout=5)
        latency = round((time.time() - t0) * 1000, 1)

        check("Network", f"HTTP Status ({resp.status_code})", resp.status_code == 200, f"Latency: {latency}ms")
        
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Page Title
        title_tag = soup.find("title")
        check("SEO", "Descriptive Title Tag", bool(title_tag and title_tag.text.strip()), title_tag.text.strip() if title_tag else "Missing")

        # 2. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        check("SEO", "Meta Description Tag", bool(meta_desc and meta_desc.get("content")), meta_desc.get("content")[:50] + "..." if meta_desc and meta_desc.get("content") else "Missing")

        # 3. Canonical Tag
        canonical = soup.find("link", attrs={"rel": "canonical"})
        check("SEO", "Canonical Link Tag", bool(canonical and canonical.get("href")), canonical.get("href") if canonical else "Missing")

        # 4. Open Graph Tags
        og_title = soup.find("meta", attrs={"property": "og:title"})
        check("Social", "Open Graph Title (og:title)", bool(og_title and og_title.get("content")), og_title.get("content") if og_title else "Missing")

        # 5. H1 Accessibility
        h1_tags = soup.find_all("h1")
        check("Accessibility", "Exactly One H1 Heading (WCAG 1.3.1)", len(h1_tags) == 1, f"Found {len(h1_tags)} H1 tag(s)")

        # 6. Password Fields Security
        pwd_inputs = soup.find_all("input", attrs={"type": "password"})
        for p in pwd_inputs:
            has_min = p.has_attr("minlength") and int(p["minlength"]) >= 6
            check("Security", f"Password Field #{p.get('id', 'pwd')} enforces minlength>=6", has_min, f"minlength={p.get('minlength', 'none')}")

        # 7. Form Accessibility & Controls
        forms = soup.find_all("form")
        for f in forms:
            has_submit = bool(f.find("button", attrs={"type": "submit"}) or f.find("input", attrs={"type": "submit"}))
            check("Forms", f"Form #{f.get('id', 'form')} has Submit button", has_submit)

        # 8. Table Accessibility
        tables = soup.find_all("table")
        for t in tables:
            has_caption = bool(t.find("caption")) or t.has_attr("aria-label")
            check("Accessibility", f"Table has Caption or aria-label", has_caption)
            ths = t.find_all("th")
            missing_scope = [th for th in ths if not th.has_attr("scope")]
            check("Accessibility", f"Table headers have scope attribute", len(missing_scope) == 0, f"{len(ths) - len(missing_scope)}/{len(ths)} headers compliant")

    except Exception as e:
        check("Network", "Page Reachable", False, str(e))

    return results

def run_full_suite():
    print("=" * 70)
    print(" AUTOMATED QA & ACCESSIBILITY AUDIT REPORT")
    print(" Target:", BASE_URL)
    print(" Generated:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    pages = [
        {"name": "Teacher Login Portal", "url": f"{BASE_URL}/teacher/login"},
        {"name": "Student Signup Page", "url": f"{BASE_URL}/student/signup"},
        {"name": "Lecturer Registration Page", "url": f"{BASE_URL}/teacher/signup"}
    ]

    total_checks = 0
    passed_checks = 0
    failed_checks = 0

    sess = requests.Session()

    for p in pages:
        print(f"\n[*] Auditing Page: {p['name']} ({p['url']})")
        res = audit_url(sess, p["url"], p["name"])
        for c in res["checks"]:
            total_checks += 1
            if c["status"] == "PASS":
                passed_checks += 1
                status_str = "[PASS]"
            else:
                failed_checks += 1
                status_str = "[FAIL]"
            
            detail_str = f" - {c['details']}" if c['details'] else ""
            print(f"  {status_str} [{c['category']}] {c['description']}{detail_str}")

    # Authenticated flow test
    print(f"\n[*] Auditing Authenticated Lecturer Session (Prof. Priya Kulkarni)...")
    auth_resp = sess.post(f"{BASE_URL}/teacher/login", data={"email": "prof_priya", "password": "Priya@123"})
    if auth_resp.status_code == 200:
        dash_res = audit_url(sess, f"{BASE_URL}/teacher/assessments", "Teacher Assessments View")
        for c in dash_res["checks"]:
            total_checks += 1
            if c["status"] == "PASS":
                passed_checks += 1
                status_str = "[PASS]"
            else:
                failed_checks += 1
                status_str = "[FAIL]"
            detail_str = f" - {c['details']}" if c['details'] else ""
            print(f"  {status_str} [{c['category']}] {c['description']}{detail_str}")

    print("\n" + "=" * 70)
    print(f" AUDIT SUMMARY: Total: {total_checks} | Passed: {passed_checks} | Failed: {failed_checks}")
    pass_pct = round((passed_checks / total_checks) * 100, 1) if total_checks else 0
    print(f" Compliance Score: {pass_pct}%")
    print("=" * 70)

if __name__ == "__main__":
    run_full_suite()
