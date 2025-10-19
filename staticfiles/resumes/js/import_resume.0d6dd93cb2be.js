document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('resumeUploadForm');
  const modal = document.getElementById('loading-modal');
  const message = document.getElementById('loading-message');
  const fileInput = document.getElementById('resume_file');
  const fileNameDisplay = document.getElementById('selected-file');
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  const messages = [
    "🔍 Reviewing your resume…",
    "🧠 Parsing with AI…",
    "✨ Almost finished…"
  ];

  // Show selected file name
  fileInput.addEventListener('change', function () {
    fileNameDisplay.textContent = fileInput.files.length > 0
      ? `📄 Selected File: ${fileInput.files[0].name}`
      : '';
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return;

    modal.classList.add('active');
    message.textContent = messages[0];
    let currentStep = 1;

    const interval = setInterval(() => {
      if (currentStep < messages.length) {
        message.textContent = messages[currentStep++];
      } else {
        clearInterval(interval);
      }
    }, 2000);

    const formData = new FormData();
    formData.append('file', file);

    fetch(uploadUrl, {
      method: "POST",
      headers: { 'X-CSRFToken': csrfToken },
      body: formData
    })
      .then(res => res.json().then(data => ({ status: res.status, body: data })))
      .then(({ status, body }) => {
        clearInterval(interval);
        if (status === 200 && body.resume_id) {
          message.textContent = "✅ Complete! Redirecting...";
          setTimeout(() => {
            window.location.href = `/resume/import/${body.resume_id}/`;
          }, 1200);
        } else {
          // ❌ Upload failed – hide modal and show alert
          modal.classList.remove('active');
          alert("❌ Upload failed: " + (body.error || "Unexpected server error."));
        }
      })
      .catch(err => {
        clearInterval(interval);
        modal.classList.remove('active');
        alert("❌ An unexpected error occurred. Please try again.");
        console.error(err);
      });
  });
});
