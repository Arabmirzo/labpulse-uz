/* LabPulse UZ — Asosiy JavaScript moduli */

// 1. Tema boshqaruvi
(function initTheme() {
  const savedTheme = localStorage.getItem("labpulse_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("labpulse_theme", next);
  updateThemeIcon(next);

  // Sozlamalarga ham xabar yuborish (ixtiyoriy)
  fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme: next })
  }).catch(() => {});
}

function updateThemeIcon(theme) {
  const label = document.getElementById("themeLabel");
  if (label) {
    label.textContent = theme === "dark" ? "Tun" : "Kun";
  }
}

// 2. Mobil menyu toggle
function toggleMobileMenu() {
  const sidebar = document.querySelector(".sidebar");
  if (sidebar) {
    sidebar.classList.toggle("open");
  }
}

// 3. Toast bildirishnomalar
function showToast(message, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "warning") icon = "⚠️";
  if (type === "critical") icon = "🚨";

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// 4. Baytlarni tushunarli formatga o'tkazish
function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

// Dom yuklanganda ishga tushirish
document.addEventListener("DOMContentLoaded", () => {
  const curTheme = document.documentElement.getAttribute("data-theme") || "dark";
  updateThemeIcon(curTheme);

  // Tashqi bosilganda mobil menyuni yopish
  document.addEventListener("click", (e) => {
    const sidebar = document.querySelector(".sidebar");
    const menuBtn = document.querySelector(".mobile-menu-btn");
    if (sidebar && sidebar.classList.contains("open") && !sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
      sidebar.classList.remove("open");
    }
  });
});
