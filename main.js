// ==========================================================
// Small shared utilities
// ==========================================================
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function placeholderIcon() {
  return `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M12 2 5 6v6c0 5 3 8.5 7 9 4-.5 7-4 7-9V6l-7-4Z"/>
  </svg>`;
}

function itemCardHTML(item) {
  const typeClass = item.item_type === "lost" ? "tag-type--lost" : "tag-type--found";
  const statusClass = "status-pill--" + item.status;
  const media = item.image_path
    ? `<div class="tag-card-media" style="background-image:url('/static/uploads/${encodeURIComponent(item.image_path)}')"></div>`
    : `<div class="tag-card-media">${placeholderIcon()}</div>`;

  return `
    <a class="tag-card" href="/item/${item.id}">
      ${media}
      <div class="tag-card-body">
        <span class="tag-type ${typeClass}">${item.item_type}</span>
        <h4>${escapeHtml(item.title)}</h4>
        <div class="meta">📍 ${escapeHtml(item.location)}</div>
        <div class="meta">🗓️ ${escapeHtml(item.event_date)}</div>
        <p class="desc">${escapeHtml(item.description || "No description provided.")}</p>
        <div class="tag-id">
          <span>TICKET #${String(item.id).padStart(5, "0")}</span>
          <span class="status-pill ${statusClass}">${item.status}</span>
        </div>
      </div>
    </a>`;
}

// ==========================================================
// Browse page: dynamic filter + fetch
// ==========================================================
function initBrowsePage() {
  const grid = document.getElementById("results-grid");
  if (!grid) return;

  const form = document.getElementById("filter-form");
  const emptyState = document.getElementById("empty-state");
  const countLabel = document.getElementById("result-count");

  async function loadItems() {
    grid.setAttribute("aria-busy", "true");
    const params = new URLSearchParams(new FormData(form));
    // strip empty params
    for (const [key, val] of [...params.entries()]) {
      if (!val) params.delete(key);
    }
    try {
      const res = await fetch("/api/items?" + params.toString());
      if (!res.ok) throw new Error("Network response was not ok");
      const items = await res.json();

      grid.innerHTML = items.map(itemCardHTML).join("");
      countLabel.textContent = items.length + (items.length === 1 ? " result" : " results");
      emptyState.style.display = items.length === 0 ? "block" : "none";
    } catch (err) {
      grid.innerHTML = "";
      emptyState.style.display = "block";
      emptyState.querySelector("p").textContent = "Something went wrong loading items. Please try again.";
      console.error(err);
    } finally {
      grid.removeAttribute("aria-busy");
    }
  }

  form.addEventListener("input", debounce(loadItems, 300));
  form.addEventListener("submit", (e) => { e.preventDefault(); loadItems(); });

  document.querySelectorAll(".type-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".type-filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      form.querySelector("input[name='type']").value = btn.dataset.type;
      loadItems();
    });
  });

  loadItems();
}

function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// ==========================================================
// Home page: recent items are server-rendered, but the
// live stat counters get a small "count up" animation.
// ==========================================================
function animateCounters() {
  document.querySelectorAll(".hero-stat .num").forEach((el) => {
    const target = parseInt(el.dataset.count || el.textContent, 10);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      el.textContent = current;
    }, 25);
  });
}

// ==========================================================
// Image preview on report form
// ==========================================================
function initImagePreview() {
  const input = document.getElementById("image-input");
  const preview = document.getElementById("image-preview");
  if (!input || !preview) return;
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) { preview.style.display = "none"; return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.style.display = "block";
    };
    reader.readAsDataURL(file);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initBrowsePage();
  animateCounters();
  initImagePreview();
});
