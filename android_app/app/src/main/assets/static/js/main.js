// Global Main JS for BEA AI Assessment System
document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 500);
    }, 6000);
  });

  const navToggle = document.getElementById("nav-toggle");
  const primaryNav = document.getElementById("primary-nav");
  if (navToggle && primaryNav) {
    navToggle.addEventListener("click", function () {
      const open = primaryNav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  document.querySelectorAll("[data-dropdown]").forEach(function (wrap) {
    const btn = wrap.querySelector("[data-dropdown-toggle]");
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      wrap.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", wrap.classList.contains("is-open") ? "true" : "false");
    });
  });

  document.addEventListener("click", function () {
    document.querySelectorAll("[data-dropdown].is-open").forEach(function (wrap) {
      wrap.classList.remove("is-open");
      const btn = wrap.querySelector("[data-dropdown-toggle]");
      if (btn) btn.setAttribute("aria-expanded", "false");
    });
  });
});

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(message, type) {
  type = type || "info";
  const container = document.querySelector(".flash-container") || createToastContainer();
  const alert = document.createElement("div");
  alert.className = "alert alert-" + type;

  const text = document.createElement("span");
  text.textContent = message;

  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Dismiss");
  close.textContent = "×";
  close.style.cssText = "background:none;border:none;color:inherit;cursor:pointer;font-size:1.1rem;";
  close.addEventListener("click", function () { alert.remove(); });

  alert.appendChild(text);
  alert.appendChild(close);
  container.appendChild(alert);
  setTimeout(function () { alert.remove(); }, 5000);
}

function createToastContainer() {
  const main = document.querySelector(".container");
  const div = document.createElement("div");
  div.className = "flash-container";
  main.insertBefore(div, main.firstChild);
  return div;
}

function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  if (btn) btn.textContent = show ? "Hide" : "Show";
}

function openGlobalSearch() {
  const modal = document.getElementById("global-search-modal");
  if (!modal) return;
  modal.classList.add("is-open");
  modal.style.display = "flex";
  modal.setAttribute("aria-hidden", "false");
  const input = document.getElementById("global-search-input");
  setTimeout(function () { if (input) input.focus(); }, 50);
}

function closeGlobalSearch() {
  const modal = document.getElementById("global-search-modal");
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
}

let searchDebounceTimer = null;

function onGlobalSearchInput(val) {
  clearTimeout(searchDebounceTimer);
  const query = (val || "").trim();
  const container = document.getElementById("global-search-results");
  if (!container) return;
  if (!query) {
    container.innerHTML = '<div class="empty-state">Type any keyword to search across distributed academic repositories.</div>';
    return;
  }

  container.innerHTML = '<div class="empty-state">Querying distributed servers...</div>';

  searchDebounceTimer = setTimeout(async function () {
    try {
      const resp = await fetch("/admin/search?q=" + encodeURIComponent(query), {
        headers: { Accept: "application/json" }
      });
      const data = await resp.json();
      if (!data.success) {
        container.innerHTML = '<div class="empty-state" style="color:var(--danger);">' + escapeHtml(data.message || "Search error") + "</div>";
        return;
      }

      const mats = (data.results && data.results.materials) || [];
      const syllabi = (data.results && data.results.syllabi) || [];
      const students = (data.results && data.results.students) || [];

      if (!mats.length && !syllabi.length && !students.length) {
        container.innerHTML = '<div class="empty-state">No results found for "' + escapeHtml(query) + '". Try broader search terms.</div>';
        return;
      }

      let html = "";
      if (mats.length) {
        html += '<div style="font-size:0.75rem;text-transform:uppercase;color:#38bdf8;font-weight:700;margin:0.25rem 0;">Academic Materials (' + mats.length + ")</div>";
        mats.slice(0, 5).forEach(function (m) {
          html +=
            '<a href="/teacher/materials" class="search-result">' +
            "<div style=\"display:flex;justify-content:space-between;align-items:center;\">" +
            '<strong style="font-size:0.88rem;color:#f8fafc;">' + escapeHtml(m.title || "Material") + "</strong>" +
            '<span class="badge badge-info" style="font-size:0.65rem;">' + escapeHtml(m.storage_server_id || "default") + "</span>" +
            "</div>" +
            '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.2rem;">' +
            escapeHtml(m.subject_code || "") + " • " + escapeHtml(m.material_type || "notes") +
            "</div></a>";
        });
      }
      if (syllabi.length) {
        html += '<div style="font-size:0.75rem;text-transform:uppercase;color:#34d399;font-weight:700;margin:0.75rem 0 0.25rem;">Syllabi & Curriculum (' + syllabi.length + ")</div>";
        syllabi.slice(0, 5).forEach(function (s) {
          html +=
            '<a href="/teacher/materials" class="search-result">' +
            "<div style=\"display:flex;justify-content:space-between;align-items:center;\">" +
            '<strong style="font-size:0.88rem;color:#f8fafc;">' + escapeHtml(s.course_code || "") + " - " + escapeHtml(s.course_title || "Syllabus") + "</strong>" +
            '<span class="badge badge-success" style="font-size:0.65rem;">v' + escapeHtml(s.version || "1.0") + "</span>" +
            "</div>" +
            '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.2rem;">Dept: ' +
            escapeHtml(s.department || "") + " • Sem " + escapeHtml(s.semester || "") +
            "</div></a>";
        });
      }
      if (students.length) {
        html += '<div style="font-size:0.75rem;text-transform:uppercase;color:#c084fc;font-weight:700;margin:0.75rem 0 0.25rem;">Students (' + students.length + ")</div>";
        students.slice(0, 5).forEach(function (st) {
          html +=
            '<a href="/teacher/students" class="search-result">' +
            "<div style=\"display:flex;justify-content:space-between;align-items:center;\">" +
            '<strong style="font-size:0.88rem;color:#f8fafc;">' + escapeHtml(st.student_name || st.full_name || "Student") + "</strong>" +
            '<code style="color:#c084fc;font-size:0.75rem;">' + escapeHtml(st.student_pin || "") + "</code>" +
            "</div>" +
            '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.2rem;">Dept: ' +
            escapeHtml(st.department || "General") + " • Sem: " + escapeHtml(st.semester || "") +
            "</div></a>";
        });
      }
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = '<div class="empty-state" style="color:var(--danger);">Error: ' + escapeHtml(err.message) + "</div>";
    }
  }, 250);
}

document.addEventListener("keydown", function (e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    const modal = document.getElementById("global-search-modal");
    if (modal && modal.classList.contains("is-open")) {
      closeGlobalSearch();
    } else {
      openGlobalSearch();
    }
  } else if (e.key === "Escape") {
    closeGlobalSearch();
  }
});
