/* LabPulse UZ — Diagnostika Sahifasi Logikasi */

async function startFullDiagnostics() {
  const btn = document.getElementById("runDiagnosticsBtn");
  const targetInput = document.getElementById("diagnosticTargetInput");
  const progressBox = document.getElementById("diagnosticProgress");
  const resultsContainer = document.getElementById("diagnosticResults");
  const statusBadge = document.getElementById("overallStatusBadge");
  const statusDesc = document.getElementById("overallStatusDesc");

  const target = targetInput ? targetInput.value.trim() : "8.8.8.8";

  // UI ni faollashtirish
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Tekshirilmoqda...`;
  }
  if (progressBox) progressBox.style.display = "block";
  if (resultsContainer) resultsContainer.innerHTML = "";

  try {
    const res = await fetch("/api/diagnostics/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: target })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server xatosi: ${res.status}`);
    }

    const data = await res.json();
    renderDiagnosticResults(data);
    showToast("Diagnostika muvaffaqiyatli yakunlandi!", "success");
  } catch (err) {
    console.error("Diagnostika jarayonida xatolik:", err);
    showToast(`Diagnostika xatoligi: ${err.message}`, "critical");
    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="card" style="border-color: var(--status-critical);">
          <h4 style="color: var(--status-critical); margin-bottom: 8px;">Diagnostika to'xtab qoldi</h4>
          <p style="color: var(--text-secondary);">${err.message}</p>
        </div>
      `;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        To'liq tekshiruvni boshlash
      `;
    }
    if (progressBox) progressBox.style.display = "none";
  }
}

function renderDiagnosticResults(data) {
  const container = document.getElementById("diagnosticResults");
  const statusBadge = document.getElementById("overallStatusBadge");
  const statusDesc = document.getElementById("overallStatusDesc");
  const statusCard = document.getElementById("summaryStatusCard");

  if (statusCard) statusCard.style.display = "block";

  const summary = data.summary || {};
  if (statusBadge) {
    statusBadge.className = `badge ${summary.color_class || 'badge-info'}`;
    statusBadge.textContent = summary.label || "Natija olindi";
  }
  if (statusDesc) {
    statusDesc.textContent = summary.description || "";
  }

  const findings = data.findings || [];
  if (!container) return;

  if (findings.length === 0) {
    container.innerHTML = `
      <div class="card">
        <p style="color: var(--text-secondary); text-align: center;">Hech qanday muammo topilmadi.</p>
      </div>
    `;
    return;
  }

  let html = `<div class="card" style="margin-top: 20px;">
    <div class="card-header">
      <h3 class="card-title">Aniqlangan holatlar va tavsiyalar (${findings.length})</h3>
    </div>
    <div class="findings-list">`;

  findings.forEach(f => {
    let badgeClass = "badge-info";
    let iconSvg = "ℹ️";
    if (f.level === "Muhim") {
      badgeClass = "badge-critical";
      iconSvg = "🚨";
    } else if (f.level === "Diqqat") {
      badgeClass = "badge-warning";
      iconSvg = "⚠️";
    } else {
      badgeClass = "badge-success";
      iconSvg = "✅";
    }

    html += `
      <div class="finding-item">
        <div class="finding-icon-wrap" style="background: var(--bg-card);">
          ${iconSvg}
        </div>
        <div class="finding-content">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-weight: 600; font-size: 0.95rem;">${escapeHtml(f.title)}</span>
            <span class="badge ${badgeClass}">${escapeHtml(f.level)}</span>
          </div>
          <div class="finding-detail">${escapeHtml(f.detail)}</div>
          <div class="finding-recommendation">
            <strong>Xavfsiz tavsiya:</strong> ${escapeHtml(f.recommendation)}
          </div>
        </div>
      </div>
    `;
  });

  html += `</div></div>`;
  container.innerHTML = html;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
