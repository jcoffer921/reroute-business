document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('resumeUploadForm');
  const modal = document.getElementById('loading-modal');
  const message = document.getElementById('loading-message');
  const fileInput = document.getElementById('resume_file');
  const fileNameDisplay = document.getElementById('selected-file');
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const uploadOnlyToggle = document.getElementById('upload_only');

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

    const endpoint = (uploadOnlyToggle && uploadOnlyToggle.checked) ? uploadOnlyUrl : uploadUrl;
    fetch(endpoint, {
      method: "POST",
      headers: { 'X-CSRFToken': csrfToken },
      body: formData
    })
      .then(res => res.json().then(data => ({ status: res.status, body: data })))
      .then(({ status, body }) => {
        clearInterval(interval);
        if (status === 200 && (body.resume_id || body.redirect_url)) {
          message.textContent = "✅ Complete! Redirecting...";
          const target = body.redirect_url || `/resume/import/${body.resume_id}/`;
          setTimeout(() => {
            window.location.href = target;
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
