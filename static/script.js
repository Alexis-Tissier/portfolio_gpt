const state = {
  config: null,
  photos: [],
  filtered: [],
  currentIndex: 0,
  sort: localStorage.getItem("portfolio-sort") || "desc",
  theme: localStorage.getItem("portfolio-theme") || "dark",
};

const $ = (selector) => document.querySelector(selector);
const gallery = $("#gallery");
const emptyState = $("#emptyState");
const configPanel = $("#configPanel");
const rootInput = $("#rootInput");
const targetInput = $("#targetInput");
const searchInput = $("#searchInput");
const yearFilter = $("#yearFilter");
const sortSelect = $("#sortSelect");
const photoCount = $("#photoCount");
const monthCount = $("#monthCount");
const yearCount = $("#yearCount");
const rootLabel = $("#rootLabel");
const configMessage = $("#configMessage");
const themeToggle = $("#themeToggle");
const refreshButton = $("#refreshButton");
const lightbox = $("#lightbox");
const lightboxImage = $("#lightboxImage");
const lightboxTitle = $("#lightboxTitle");
const lightboxMeta = $("#lightboxMeta");

function applyTheme() {
  document.body.classList.toggle("light", state.theme === "light");
  themeToggle.textContent = state.theme === "light" ? "Mode sombre" : "Mode clair";
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Erreur HTTP ${response.status}`);
  }
  return response.json();
}

async function loadConfig() {
  const data = await api("/api/config");
  state.config = data.config;
  rootInput.value = state.config.photos_root || "";
  targetInput.value = state.config.target_folder_name || "Retouché";
  sortSelect.value = state.sort || state.config.default_sort || "desc";
  configPanel.classList.toggle("hidden", Boolean(state.config.photos_root && data.root_exists));
}

async function loadPhotos(force = false) {
  refreshButton.disabled = true;
  refreshButton.textContent = "Scan…";
  try {
    const data = await api(`/api/photos${force ? "?force=1" : ""}`);
    state.photos = data.photos || [];
    rootLabel.textContent = data.root
      ? `Dossier lu : ${data.root}`
      : "Aucun dossier racine configuré.";

    if (data.last_error) {
      configPanel.classList.remove("hidden");
      configMessage.textContent = data.last_error;
    } else {
      configMessage.textContent = data.pillow_available
        ? "Miniatures accélérées activées."
        : "L'application fonctionne. Pour un chargement plus rapide, installe Pillow avec : pip install Pillow";
    }

    populateYears(data.years || []);
    applyFilters();
  } catch (error) {
    configMessage.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Actualiser";
  }
}

function populateYears(years) {
  const current = yearFilter.value || "all";
  yearFilter.innerHTML = `<option value="all">Toutes</option>`;
  for (const year of years) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = String(year);
    yearFilter.appendChild(option);
  }
  yearFilter.value = [...yearFilter.options].some((option) => option.value === current) ? current : "all";
}

function applyFilters() {
  const query = searchInput.value.trim().toLowerCase();
  const selectedYear = yearFilter.value;
  const sort = sortSelect.value;
  state.sort = sort;
  localStorage.setItem("portfolio-sort", sort);

  state.filtered = state.photos.filter((photo) => {
    const text = `${photo.filename} ${photo.relative_path} ${photo.folder}`.toLowerCase();
    const matchQuery = !query || text.includes(query);
    const matchYear = selectedYear === "all" || String(photo.year) === selectedYear;
    return matchQuery && matchYear;
  });

  state.filtered.sort((a, b) => {
    if (a.month_key === "sans-date" && b.month_key !== "sans-date") return 1;
    if (b.month_key === "sans-date" && a.month_key !== "sans-date") return -1;
    return sort === "desc" ? b.sort_ts - a.sort_ts : a.sort_ts - b.sort_ts;
  });

  renderStats();
  renderGallery();
}

function groupByMonth(photos) {
  const groups = new Map();
  for (const photo of photos) {
    if (!groups.has(photo.month_key)) {
      groups.set(photo.month_key, { key: photo.month_key, label: photo.month_label, photos: [] });
    }
    groups.get(photo.month_key).photos.push(photo);
  }
  return [...groups.values()];
}

function renderStats() {
  const groups = groupByMonth(state.filtered).filter((group) => group.key !== "sans-date");
  const years = new Set(state.filtered.map((photo) => photo.year).filter(Boolean));
  photoCount.textContent = state.filtered.length;
  monthCount.textContent = groups.length;
  yearCount.textContent = years.size;
}

function renderGallery() {
  gallery.innerHTML = "";
  emptyState.classList.toggle("hidden", state.filtered.length > 0);

  for (const group of groupByMonth(state.filtered)) {
    const section = document.createElement("section");
    section.className = "gallery-month";

    const title = document.createElement("div");
    title.className = "month-title";
    title.innerHTML = `<h2>${escapeHtml(group.label)}</h2><span>${group.photos.length} photo${group.photos.length > 1 ? "s" : ""}</span>`;

    const grid = document.createElement("div");
    grid.className = "masonry";

    for (const photo of group.photos) {
      const index = state.filtered.indexOf(photo);
      const card = document.createElement("button");
      card.type = "button";
      card.className = "photo-card";

      if (photo.width && photo.height) {
        card.style.aspectRatio = `${photo.width} / ${photo.height}`;
      }

      card.addEventListener("click", () => openLightbox(index));

      card.innerHTML = `
        <img src="${photo.thumb_url}" alt="${escapeHtml(photo.filename)}" loading="lazy" decoding="async" />
        <span class="photo-caption">
          <strong>${escapeHtml(photo.filename)}</strong>
          <span>${escapeHtml(photo.date_label)} · ${escapeHtml(photo.folder)}</span>
        </span>
      `;

      grid.appendChild(card);
    }

    section.appendChild(title);
    section.appendChild(grid);
    gallery.appendChild(section);
  }
}

function openLightbox(index) {
  if (!state.filtered[index]) return;
  state.currentIndex = index;
  const photo = state.filtered[index];
  lightboxImage.src = photo.media_url;
  lightboxTitle.textContent = photo.filename;
  lightboxMeta.textContent = `${photo.date_label} · ${photo.relative_path}`;
  lightbox.classList.remove("hidden");
  lightbox.setAttribute("aria-hidden", "false");
}

function closeLightbox() {
  lightbox.classList.add("hidden");
  lightbox.setAttribute("aria-hidden", "true");
  lightboxImage.src = "";
}

function moveLightbox(direction) {
  if (lightbox.classList.contains("hidden") || state.filtered.length === 0) return;
  const total = state.filtered.length;
  const nextIndex = (state.currentIndex + direction + total) % total;
  openLightbox(nextIndex);
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

$("#configForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  configMessage.textContent = "Configuration en cours…";
  try {
    const payload = {
      photos_root: rootInput.value.trim(),
      target_folder_name: targetInput.value.trim() || "Retouché",
      default_sort: sortSelect.value,
    };
    await api("/api/config", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadConfig();
    await loadPhotos(true);
    configMessage.textContent = "Configuration enregistrée.";
  } catch (error) {
    configMessage.textContent = error.message;
  }
});

searchInput.addEventListener("input", applyFilters);
yearFilter.addEventListener("change", applyFilters);
sortSelect.addEventListener("change", applyFilters);
refreshButton.addEventListener("click", () => loadPhotos(true));

themeToggle.addEventListener("click", () => {
  state.theme = state.theme === "light" ? "dark" : "light";
  localStorage.setItem("portfolio-theme", state.theme);
  applyTheme();
});

$("#closeLightbox").addEventListener("click", closeLightbox);
$("#prevPhoto").addEventListener("click", () => moveLightbox(-1));
$("#nextPhoto").addEventListener("click", () => moveLightbox(1));
lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) closeLightbox();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeLightbox();
  if (event.key === "ArrowLeft") moveLightbox(-1);
  if (event.key === "ArrowRight") moveLightbox(1);
});

(async function init() {
  applyTheme();
  await loadConfig();
  await loadPhotos(false);
})();
