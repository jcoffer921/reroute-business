// contact_info.js
// Live preview helpers with sensible fallbacks for non-coders reading the code.

/**
 * Update text content of an element by id with a fallback.
 * @param {string} id - target element id
 * @param {string} value - new text value
 * @param {string} fallback - default if value is empty
 */
function updateText(id, value, fallback = "") {
  const el = document.getElementById(id);
  if (el) el.textContent = (value || "").trim() || fallback;
}

// Full Name
const fullNameInput = document.getElementById("id_full_name");
const emailInput = document.getElementById("id_email");
const cityInput = document.getElementById("id_city");
const stateInput = document.getElementById("id_state");

fullNameInput?.addEventListener("input", function () {
  updateText("preview_full_name", this.value, "Your Name");
  this.classList.toggle('is-invalid', !this.value.trim());
});
// Email
emailInput?.addEventListener("input", function () {
  updateText("preview_email", this.value, "email@example.com");
  const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value.trim());
  this.classList.toggle('is-invalid', !ok);
});
// Phone
document.getElementById("id_phone")?.addEventListener("input", function () {
  updateText("preview_phone", this.value, "(123) 456-7890");
});
// City
cityInput?.addEventListener("input", function () {
  updateText("preview_city", this.value, "City");
  this.classList.toggle('is-invalid', !this.value.trim());
});
// State
stateInput?.addEventListener("change", function () {
  updateText("preview_state", this.value, "State");
  this.classList.toggle('is-invalid', !this.value.trim());
});

// Submit validation (minimal: full name + valid email)
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    let invalid = false;
    if (fullNameInput && !fullNameInput.value.trim()) {
      fullNameInput.classList.add('is-invalid');
      invalid = true;
    }
    if (emailInput) {
      const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim());
      if (!ok) {
        emailInput.classList.add('is-invalid');
        invalid = true;
      }
    }
    if (cityInput && !cityInput.value.trim()) {
      cityInput.classList.add('is-invalid');
      invalid = true;
    }
    if (stateInput && !stateInput.value.trim()) {
      stateInput.classList.add('is-invalid');
      invalid = true;
    }
    if (invalid) {
      e.preventDefault();
      const first = document.querySelector('.is-invalid');
      if (first) first.focus();
    }
  });
});
