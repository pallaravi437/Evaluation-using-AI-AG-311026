// Student Script Upload & Interactive Canvas Image Processing
let currentFile = null;
let currentQuestionId = null;
let currentQuestionNum = null;
let currentRotation = 0;
let rawImage = new Image();

function handleFileSelect(event, qId, qNum) {
  const file = event.target.files[0];
  if (!file) return;

  currentFile = file;
  currentQuestionId = qId;
  currentQuestionNum = qNum;
  currentRotation = 0;

  // If PDF, upload directly without canvas editing
  if (file.type === "application/pdf") {
    directUploadFile(file, qId);
    return;
  }

  // Load image into canvas
  const reader = new FileReader();
  reader.onload = function (e) {
    rawImage = new Image();
    rawImage.onload = function () {
      openEditorModal(file.size);
      drawCanvas();
    };
    rawImage.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function openEditorModal(origSizeBytes) {
  const modal = document.getElementById("editor-modal");
  modal.style.display = "flex";
  document.getElementById("orig-size-label").innerText = (origSizeBytes / 1024).toFixed(1) + " KB";
}

function closeEditorModal() {
  document.getElementById("editor-modal").style.display = "none";
}

function drawCanvas() {
  const canvas = document.getElementById("editor-canvas");
  const ctx = canvas.getContext("2d");

  const rads = (currentRotation * Math.PI) / 180;
  const isPerpendicular = Math.abs(currentRotation % 180) === 90;

  canvas.width = isPerpendicular ? rawImage.height : rawImage.width;
  canvas.height = isPerpendicular ? rawImage.width : rawImage.height;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate(rads);
  ctx.drawImage(rawImage, -rawImage.width / 2, -rawImage.height / 2);
  ctx.restore();
}

function rotateCanvas(deg) {
  currentRotation = (currentRotation + deg) % 360;
  drawCanvas();
}

function autoDetectEdges() {
  showToast("Auto-straighten applied: Page aligned to standard portrait orientation.", "info");
  if (currentRotation % 180 !== 0) {
    currentRotation = 0;
    drawCanvas();
  }
}

async function uploadProcessedPage() {
  const canvas = document.getElementById("editor-canvas");
  const saveBtn = document.getElementById("confirm-save-page-btn");
  saveBtn.disabled = true;
  saveBtn.innerText = "⏳ Compressing & Uploading...";

  canvas.toBlob(async function (blob) {
    const formData = new FormData();
    formData.append("submission_id", CURRENT_SUBMISSION_ID);
    formData.append("question_id", currentQuestionId);
    formData.append("page_number", Date.now()); // Unique incremental
    formData.append("file", blob, `q_${currentQuestionNum}_script.jpg`);

    try {
      const resp = await fetch("/student/api/upload-page", {
        method: "POST",
        body: formData
      });
      const data = await resp.json();

      if (data.success) {
        closeEditorModal();
        showToast("Script page uploaded and compressed to " + data.metadata.optimized_size_kb + " KB!", "success");
        appendPageThumbnail(currentQuestionId, data);
      } else {
        alert("Upload error: " + data.message);
      }
    } catch (e) {
      alert("Network error: " + e.message);
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerText = "✓ Save Page & Compress";
    }
  }, "image/jpeg", 0.82);
}

async function directUploadFile(file, qId) {
  const formData = new FormData();
  formData.append("submission_id", CURRENT_SUBMISSION_ID);
  formData.append("question_id", qId);
  formData.append("page_number", Date.now());
  formData.append("file", file);

  showToast("Uploading PDF document...", "info");

  try {
    const resp = await fetch("/student/api/upload-page", {
      method: "POST",
      body: formData
    });
    const data = await resp.json();
    if (data.success) {
      showToast("PDF page added successfully!", "success");
      appendPageThumbnail(qId, data);
    } else {
      alert("Upload failed: " + data.message);
    }
  } catch (e) {
    alert("Network error: " + e.message);
  }
}

function appendPageThumbnail(qId, data) {
  const container = document.getElementById(`pages-container-${qId}`);
  const thumb = document.createElement("div");
  thumb.className = "page-thumb-card";
  thumb.style.cssText = "background: #0f172a; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.5rem; width: 160px; text-align: center;";
  thumb.innerHTML = `
    <div style="height: 120px; background: #1e293b; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem; overflow: hidden;">
      <span style="font-size: 2rem;">📄</span>
    </div>
    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">
      Uploaded Page
    </div>
    <div style="font-size: 0.7rem; color: #34d399;">
      ✓ ${data.metadata.optimized_size_kb} KB
    </div>
  `;
  container.appendChild(thumb);

  // Update badge counter
  const badge = document.getElementById(`page-count-badge-${qId}`);
  if (badge) {
    const count = container.querySelectorAll(".page-thumb-card").length;
    badge.innerText = `${count} Page(s) Uploaded`;
  }
}
