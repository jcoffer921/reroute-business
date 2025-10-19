document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("rightsModal");
  const closeModal = document.getElementById("closeRightsModal");
  const trigger = document.getElementById("triggerModal");

  // Open modal
  trigger.addEventListener("click", (e) => {
    e.preventDefault(); // prevent anchor jump
    modal.style.display = "block";
  });

  // Close modal with X
  closeModal.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // Close modal by clicking outside the content
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });

  // Optional: close modal with Escape key
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.style.display === "block") {
      modal.style.display = "none";
    }
  });
});
