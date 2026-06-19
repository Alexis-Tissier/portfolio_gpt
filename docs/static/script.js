const state = {
  photos: [],
  filtered: [],
  currentIndex: 0,
  theme: localStorage.getItem("portfolio-public-theme") || "dark",
};

const $ = (selector) => document.querySelector(selector);
const gallery = $("#gallery");
const emptyState = $("#emptyState");
const photoCount = $("#photoCount");
const themeToggle = $("#themeToggle");
const lightbox = $("#lightbox");
const lightboxImage = $("#lightboxImage");
const lightboxTitle = $("#lightboxTitle");
const lightboxMeta = $("#lightboxMeta");

function applyTheme() {
  document.body.classList.toggle("light", state.theme === "light");
  themeToggle.textContent = state.theme === "light" ? "Mode sombre" : "Mode clair";
}

async function loadPhotos() {
  try {
    const response = await fetch("data/photos.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Impossible de charger photos.json");
    state.photos = await response.json();
  } catch (error) {
    console.error(error);
    state.photos = [];
  }

  state.filtered = [...state.photos].sort((a, b) => b.sort_ts - a.sort_ts);
  renderGallery();
}

function groupBy(items, keyGetter) {
  const groups = new Map();
  for (const item of items) {
    const key = keyGetter(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return groups;
}

function renderGallery() {
  gallery.innerHTML = "";
  photoCount.textContent = state.filtered.length;
  emptyState.classList.toggle("hidden", state.filtered.length > 0);

  const months = groupBy(state.filtered, (photo) => photo.month_key);

  for (const [, monthPhotos] of months) {
    const monthSection = document.createElement("section");
    monthSection.className = "gallery-month";

    const monthTitle = document.createElement("div");
    monthTitle.className = "month-title";
    monthTitle.innerHTML = `
      <h2>${escapeHtml(monthPhotos[0].month_label)}</h2>
      <span>${monthPhotos.length} photo${monthPhotos.length > 1 ? "s" : ""}</span>
    `;
    monthSection.appendChild(monthTitle);

    const days = groupBy(monthPhotos, (photo) => photo.day_key);

    for (const [, dayPhotos] of days) {
      const daySection = document.createElement("section");
      daySection.className = "gallery-day";

      const dayTitle = document.createElement("div");
      dayTitle.className = "day-title";
      dayTitle.innerHTML = `
        <h3>${escapeHtml(dayPhotos[0].day_label)}</h3>
        <span>${dayPhotos.length} photo${dayPhotos.length > 1 ? "s" : ""}</span>
      `;

      const grid = document.createElement("div");
      grid.className = "masonry";

      for (const photo of dayPhotos) {
        const index = state.filtered.indexOf(photo);
        const card = document.createElement("button");
        card.type = "button";
        card.className = "photo-card";

        if (photo.width && photo.height) {
          card.style.aspectRatio = `${photo.width} / ${photo.height}`;
        }

        card.addEventListener("click", () => openLightbox(index));

        card.innerHTML = `
          <img src="${photo.url}" alt="${escapeHtml(photo.original_name || photo.filename)}" loading="lazy" decoding="async" />
          <span class="photo-caption">
            <strong>${escapeHtml(photo.original_name || photo.filename)}</strong>
            <span>${escapeHtml(photo.date_label)}</span>
          </span>
        `;

        grid.appendChild(card);
      }

      daySection.appendChild(dayTitle);
      daySection.appendChild(grid);
      monthSection.appendChild(daySection);
    }

    gallery.appendChild(monthSection);
  }
}

function openLightbox(index) {
  if (!state.filtered[index]) return;
  state.currentIndex = index;
  const photo = state.filtered[index];
  lightboxImage.src = photo.url;
  lightboxTitle.textContent = photo.original_name || photo.filename;
  lightboxMeta.textContent = photo.date_label;
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

themeToggle.addEventListener("click", () => {
  state.theme = state.theme === "light" ? "dark" : "light";
  localStorage.setItem("portfolio-public-theme", state.theme);
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

applyTheme();
loadPhotos();
