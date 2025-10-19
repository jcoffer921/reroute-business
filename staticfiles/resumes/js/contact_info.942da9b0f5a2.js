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
document.getElementById("id_full_name")?.addEventListener("input", function () {
  updateText("preview_full_name", this.value, "Your Name");
});
// Email
document.getElementById("id_email")?.addEventListener("input", function () {
  updateText("preview_email", this.value, "email@example.com");
});
// Phone
document.getElementById("id_phone")?.addEventListener("input", function () {
  updateText("preview_phone", this.value, "(123) 456-7890");
});
// City
document.getElementById("id_city")?.addEventListener("input", function () {
  updateText("preview_city", this.value, "City");
});
// State
document.getElementById("id_state")?.addEventListener("change", function () {
  updateText("preview_state", this.value, "State");
});
