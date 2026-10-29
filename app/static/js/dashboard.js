/* LabPulse UZ — Dashboard Telemetriya va Grafik boshqaruvi */

let refreshIntervalId = null;
let currentIntervalSec = 5;
let isRefreshing = false;

// 1. Telemetriyani yuklash
async function fetchMetrics() {
  if (isRefreshing) return;
  isRefreshing = true;
  
  const refreshBtn = document.getElementById("manualRefreshBtn");
  if (refreshBtn) refreshBtn.classList.add("loading");

  try {
    const res = await fetch("/api/metrics");
    if (!res.ok) throw new Error(`HTTP xatosi: ${res.status}`);
    const data = await res.json();

    updateMetricCards(data);
    hideErrorBanner();
    updateLastTimestamp();
  } catch (err) {
    console.error("Metrikalarni olishda xatolik:", err);
    showErrorBanner("Serverdan jonli ma'lumotlarni olib bo'lmadi. Aloqa uzilgan bo'lishi mumkin.");
  } finally {
    isRefreshing = false;
    if (refreshBtn) refreshBtn.classList.remove("loading");
  }
}

// 2. Kartalarni yangilash
function updateMetricCards(data) {
  // CPU
  const cpuVal = data.cpu_percent !== null && data.cpu_percent !== undefined ? data.cpu_percent : 0;
  const cpuElem = document.getElementById("valCpu");
  const cpuBar = document.getElementById("barCpu");
  if (cpuElem) cpuElem.textContent = cpuVal.toFixed(1);
  if (cpuBar) {
    cpuBar.style.width = `${Math.min(cpuVal, 100)}%`;
    cpuBar.className = "progress-bar-fill " + getSeverityClass(cpuVal, 70, 90);
  }
  const cpuSub = document.getElementById("subCpu");
  if (cpuSub) cpuSub.textContent = `${data.cpu_count || 1} ta mantiqiy yadro`;

  // RAM
  const mem = data.memory || {};
  const ramVal = mem.used_percent || 0;
  const ramElem = document.getElementById("valRam");
  const ramBar = document.getElementById("barRam");
  if (ramElem) ramElem.textContent = ramVal.toFixed(1);
  if (ramBar) {
    ramBar.style.width = `${Math.min(ramVal, 100)}%`;
    ramBar.className = "progress-bar-fill " + getSeverityClass(ramVal, 80, 90);
  }
  const ramSub = document.getElementById("subRam");
  if (ramSub && mem.used_bytes && mem.total_bytes) {
    ramSub.textContent = `${formatBytes(mem.used_bytes)} / ${formatBytes(mem.total_bytes)}`;
  }

  // Disk
  const disk = data.disk || {};
  const diskVal = disk.used_percent || 0;
  const diskElem = document.getElementById("valDisk");
  const diskBar = document.getElementById("barDisk");
  if (diskElem) diskElem.textContent = diskVal.toFixed(1);
  if (diskBar) {
    diskBar.style.width = `${Math.min(diskVal, 100)}%`;
    // Disk uchun ishlatilish foizi 80% dan oshsa ogohlantirish, 90% da kritik
    diskBar.className = "progress-bar-fill " + getSeverityClass(diskVal, 80, 90);
  }
  const diskSub = document.getElementById("subDisk");
  if (diskSub && disk.free_bytes) {
    diskSub.textContent = `${formatBytes(disk.free_bytes)} bo'sh joy`;
  }

  // Hostname & Platform & Uptime
  const hostElem = document.getElementById("valHostname");
  if (hostElem) hostElem.textContent = data.hostname || "Lokal kompyuter";

  const platElem = document.getElementById("valPlatform");
  if (platElem) platElem.textContent = `${data.platform || ""} ${data.platform_version || ""}`.trim();

  const uptimeElem = document.getElementById("valUptime");
  if (uptimeElem && data.uptime_seconds) {
    uptimeElem.textContent = formatUptimeSec(data.uptime_seconds);
  }

  // Tizim umumiy holatini hisoblash
  updateSystemBadge(cpuVal, ramVal, diskVal);
}

function getSeverityClass(val, warnThresh, critThresh) {
  if (val >= critThresh) return "critical";
  if (val >= warnThresh) return "warning";
  return "success";
}

function updateSystemBadge(cpu, ram, disk) {
  const badge = document.getElementById("systemStatusBadge");
  const desc = document.getElementById("systemStatusDesc");
  if (!badge) return;

  if (cpu >= 90 || ram >= 90 || disk >= 90) {
    badge.className = "badge badge-critical";
    badge.textContent = "Muhim e'tibor talab";
    if (desc) desc.textContent = "Protsessor, xotira yoki disk chegaraviy yuklanishda.";
  } else if (cpu >= 70 || ram >= 80 || disk >= 80) {
    badge.className = "badge badge-warning";
    badge.textContent = "Diqqat talab qilinadi";
    if (desc) desc.textContent = "Ayrim resurslar me'yordan ortiq foydalanilmoqda.";
  } else {
    badge.className = "badge badge-success";
    badge.textContent = "Tizim barqaror";
    if (desc) desc.textContent = "Barcha resurslar xavfsiz chegarada ishlayapti.";
  }
}

function formatUptimeSec(seconds) {
  seconds = parseInt(seconds, 10) || 0;
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (days > 0) parts.push(`${days} kun`);
  if (hours > 0) parts.push(`${hours} soat`);
  if (minutes > 0 || parts.length === 0) parts.push(`${minutes} daqiqa`);
  return parts.join(" ");
}

function updateLastTimestamp() {
  const el = document.getElementById("lastUpdatedTime");
  if (el) {
    const d = new Date();
    el.textContent = d.toLocaleTimeString("uz-UZ");
  }
}

function showErrorBanner(msg) {
  const b = document.getElementById("dashboardErrorBanner");
  const t = document.getElementById("dashboardErrorText");
  if (b && t) {
    t.textContent = msg;
    b.style.display = "flex";
  }
}

function hideErrorBanner() {
  const b = document.getElementById("dashboardErrorBanner");
  if (b) b.style.display = "none";
}

// 3. Haqiqiy tarixiy ko'rsatkichlar grafikasi (Canvas API orqali)
async function fetchAndDrawChart() {
  try {
    const res = await fetch("/api/history");
    if (!res.ok) return;
    const json = await res.json();
    const history = json.history || [];
    renderHistoryChart(history);
  } catch (e) {
    console.error("Grafik tarixini yuklab bo'lmadi:", e);
  }
}

function renderHistoryChart(dataPoints) {
  const canvas = document.getElementById("telemetryChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  
  // Retina display moslashuvi
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = rect.width;
  const h = rect.height;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const chartW = w - padding.left - padding.right;
  const chartH = h - padding.top - padding.bottom;

  ctx.clearRect(0, 0, w, h);

  // Qora / Oq tema ranglarini aniqlash
  const isDark = document.documentElement.getAttribute("data-theme") !== "light";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.07)" : "rgba(0, 0, 0, 0.07)";
  const textColor = isDark ? "#94A3B8" : "#64748B";

  // Y o'qi to'rlari (0%, 25%, 50%, 75%, 100%)
  ctx.strokeStyle = gridColor;
  ctx.fillStyle = textColor;
  ctx.font = "11px -apple-system, sans-serif";
  ctx.lineWidth = 1;

  for (let i = 0; i <= 4; i++) {
    const yVal = i * 25;
    const y = padding.top + chartH - (yVal / 100) * chartH;
    
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartW, y);
    ctx.stroke();

    ctx.textAlign = "right";
    ctx.fillText(`${yVal}%`, padding.left - 8, y + 4);
  }

  if (dataPoints.length < 2) {
    ctx.fillStyle = textColor;
    ctx.textAlign = "center";
    ctx.fillText("Tarixiy ko'rsatkichlar to'planmoqda...", w / 2, h / 2);
    return;
  }

  // Chiziqlarni chizish funksiyasi
  function drawLine(points, key, strokeColor, fillColor) {
    const step = chartW / Math.max(points.length - 1, 1);

    ctx.beginPath();
    points.forEach((pt, idx) => {
      const val = pt[key] !== null && pt[key] !== undefined ? pt[key] : 0;
      const x = padding.left + idx * step;
      const y = padding.top + chartH - (Math.min(val, 100) / 100) * chartH;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    // So'nggi nuqtagacha chizish
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Maydonni bo'yash (Gradient)
    ctx.lineTo(padding.left + (points.length - 1) * step, padding.top + chartH);
    ctx.lineTo(padding.left, padding.top + chartH);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
  }

  // CPU (Binafsha-ko'k)
  drawLine(
    dataPoints,
    "cpu_percent",
    "#6D7CFF",
    isDark ? "rgba(109, 124, 255, 0.15)" : "rgba(79, 70, 229, 0.1)"
  );

  // RAM (Moviy-yashil)
  drawLine(
    dataPoints,
    "memory_percent",
    "#22D3EE",
    isDark ? "rgba(34, 211, 238, 0.1)" : "rgba(8, 145, 178, 0.1)"
  );
}

// 4. Initialisation
document.addEventListener("DOMContentLoaded", () => {
  // Dastlabki yuklash
  fetchMetrics();
  fetchAndDrawChart();

  // Sozlamalardan intervalni olish
  fetch("/api/settings")
    .then(r => r.json())
    .then(st => {
      if (st && st.refresh_interval) {
        currentIntervalSec = st.refresh_interval;
      }
      startAutoRefresh();
    })
    .catch(() => {
      startAutoRefresh();
    });

  // Qo'lda yangilash tugmasi
  const refreshBtn = document.getElementById("manualRefreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      fetchMetrics();
      fetchAndDrawChart();
    });
  }

  // Oyna o'lchami o'zgarganda grafikni qayta chizish
  window.addEventListener("resize", () => {
    fetchAndDrawChart();
  });
});

function startAutoRefresh() {
  if (refreshIntervalId) clearInterval(refreshIntervalId);
  refreshIntervalId = setInterval(() => {
    fetchMetrics();
    fetchAndDrawChart();
  }, currentIntervalSec * 1000);
}
