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

  state.filtered = [...state.photos].sort((a, b) => {
    const orderA = Number.isFinite(a.order) ? a.order : 0;
    const orderB = Number.isFinite(b.order) ? b.order : 0;
    return orderA - orderB;
  });

  renderGallery();
}

function renderGallery() {
  gallery.innerHTML = "";
  photoCount.textContent = state.filtered.length;
  emptyState.classList.toggle("hidden", state.filtered.length > 0);

  const grid = document.createElement("div");
  grid.className = "masonry public-selection";

  for (const photo of state.filtered) {
    const index = state.filtered.indexOf(photo);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "photo-card";

    if (photo.width && photo.height) {
      card.style.aspectRatio = `${photo.width} / ${photo.height}`;
    }

    card.addEventListener("click", () => openLightbox(index));

    card.innerHTML = `
      <img src="${photo.url}" alt="Photographie" loading="lazy" decoding="async" />
      <span class="photo-caption" aria-hidden="true">
        <strong>Voir la photo</strong>
      </span>
    `;

    grid.appendChild(card);
  }

  gallery.appendChild(grid);
}

function openLightbox(index) {
  if (!state.filtered[index]) return;
  state.currentIndex = index;
  const photo = state.filtered[index];
  lightboxImage.src = photo.url;
  lightboxTitle.textContent = `Photo ${index + 1} / ${state.filtered.length}`;
  lightboxMeta.textContent = "Sélection publique";
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
