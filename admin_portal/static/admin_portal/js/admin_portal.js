document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("confirmModal");
  const msgEl = document.getElementById("confirmModalMessage");
  const btnOk = document.getElementById("confirmOk");
  const btnCancel = document.getElementById("confirmCancel");
  const backdrop = document.querySelector(".rr-modal__backdrop");
  let pendingForm = null;

  function openModal(message, form) {
    pendingForm = form;
    if (msgEl) msgEl.textContent = message || "Are you sure?";
    if (modal) {
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
    }
  }

  function closeModal() {
    if (modal) {
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
    }
    pendingForm = null;
  }

  if (btnOk) {
    btnOk.addEventListener("click", () => {
      if (pendingForm) pendingForm.submit();
      closeModal();
    });
  }

  if (btnCancel) btnCancel.addEventListener("click", closeModal);
  if (backdrop) backdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });

  document.querySelectorAll("form.js-confirm").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      openModal(form.dataset.message || "Are you sure?", form);
    });
  });
});
