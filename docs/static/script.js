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

function getThumbUrl(photo) {
  return photo.thumb_url || photo.url || photo.full_url;
}

function getFullUrl(photo) {
  return photo.full_url || photo.url || photo.thumb_url;
}

function preloadImage(url) {
  if (!url) return;
  const img = new Image();
  img.src = url;
}

function preloadAround(index) {
  const total = state.filtered.length;
  if (!total) return;

  const current = state.filtered[index];
  const previous = state.filtered[(index - 1 + total) % total];
  const next = state.filtered[(index + 1) % total];

  preloadImage(getFullUrl(current));
  preloadImage(getFullUrl(previous));
  preloadImage(getFullUrl(next));
}

function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}

function orderPhotos(photos) {
  const featured = photos
    .filter((photo) => photo.featured === true)
    .sort((a, b) => {
      const orderA = Number.isFinite(a.order) ? a.order : 0;
      const orderB = Number.isFinite(b.order) ? b.order : 0;
      return orderA - orderB;
    });

  const random = shuffleArray(photos.filter((photo) => photo.featured !== true));

  return [...featured, ...random];
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

  state.filtered = orderPhotos(state.photos);

  renderGallery();
}

function renderGallery() {
  gallery.innerHTML = "";
  photoCount.textContent = state.filtered.length;
  emptyState.classList.toggle("hidden", state.filtered.length > 0);

  const grid = document.createElement("div");
  grid.className = "masonry public-selection";

  state.filtered.forEach((photo, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "photo-card";

    if (photo.featured === true) {
      card.classList.add("is-featured");
    }

    if (photo.width && photo.height) {
      card.style.aspectRatio = `${photo.width} / ${photo.height}`;
    }

    card.addEventListener("click", () => openLightbox(index));

    const img = document.createElement("img");
    img.src = getThumbUrl(photo);
    img.alt = "Photographie";
    img.decoding = "async";
    img.loading = index < 18 ? "eager" : "lazy";
    img.fetchPriority = index < 8 ? "high" : "auto";

    img.addEventListener("load", () => {
      card.classList.add("is-loaded");
    });

    img.addEventListener("error", () => {
      const fallback = getFullUrl(photo);
      if (fallback && img.src !== new URL(fallback, window.location.href).href) {
        img.src = fallback;
        return;
      }
      card.classList.add("is-error");
    });

    const caption = document.createElement("span");
    caption.className = "photo-caption";
    caption.setAttribute("aria-hidden", "true");
    caption.innerHTML = "<strong>Voir la photo</strong>";

    card.appendChild(img);
    card.appendChild(caption);
    grid.appendChild(card);
  });

  gallery.appendChild(grid);
}

function openLightbox(index) {
  if (!state.filtered[index]) return;
  state.currentIndex = index;

  const photo = state.filtered[index];
  const fullUrl = getFullUrl(photo);

  lightboxImage.classList.remove("is-visible");
  lightboxImage.src = "";
  lightboxImage.alt = `Photographie ${index + 1} sur ${state.filtered.length}`;
  lightboxTitle.textContent = "";
  lightboxMeta.textContent = "";

  document.body.classList.add("lightbox-open");
  lightbox.classList.remove("hidden");
  lightbox.setAttribute("aria-hidden", "false");

  lightboxImage.onload = () => {
    lightboxImage.classList.add("is-visible");
  };

  lightboxImage.onerror = () => {
    const fallback = getThumbUrl(photo);
    if (fallback && lightboxImage.src !== new URL(fallback, window.location.href).href) {
      lightboxImage.src = fallback;
    }
  };

  lightboxImage.src = fullUrl;
  preloadAround(index);
}

function closeLightbox() {
  lightbox.classList.add("hidden");
  lightbox.setAttribute("aria-hidden", "true");
  document.body.classList.remove("lightbox-open");
  lightboxImage.onload = null;
  lightboxImage.onerror = null;
  lightboxImage.src = "";
  lightboxImage.classList.remove("is-visible");
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

$("#closeLightbox").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  closeLightbox();
});

$("#prevPhoto").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  moveLightbox(-1);
});

$("#nextPhoto").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  moveLightbox(1);
});

lightboxImage.addEventListener("click", (event) => {
  event.stopPropagation();
});

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
