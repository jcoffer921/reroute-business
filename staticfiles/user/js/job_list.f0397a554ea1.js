function toggleFilters() {
  const sidebar = document.getElementById('filtersSidebar');
  sidebar.style.display = sidebar.style.display === 'block' ? 'none' : 'block';
}

document.addEventListener('DOMContentLoaded', () => {
  // Auto-submit when checkboxes change
  document.querySelectorAll('#jobFilterForm input[type="checkbox"]').forEach(box => {
    box.addEventListener('change', () => {
      document.getElementById('jobFilterForm').submit();
    });
  });
});

document.addEventListener('DOMContentLoaded', () => {
  if (!toggleSaveUrl || !csrfToken) {
    console.error("Missing toggleSaveUrl or csrfToken.");
    return;
  }

  // Use event delegation on the container
  document.body.addEventListener('click', async (event) => {
    const button = event.target.closest('.save-job-btn');

    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    const jobId = button.dataset.jobId;
    const icon = button.querySelector('.bookmark-icon');
    const label = button.querySelector('.save-label');

    // Prevent double click spamming
    if (button.disabled) return;
    button.disabled = true;

    try {
      const response = await fetch(toggleSaveUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_id=${jobId}`
      });

      const data = await response.json();
      console.log("Save toggle response:", data);  // 👀 Debug

      if (data.status === 'saved') {
        button.classList.add('saved');
        icon.classList.add('filled');
        label.textContent = 'Saved';
      } else if (data.status === 'unsaved') {
        button.classList.remove('saved');
        icon.classList.remove('filled');
        label.textContent = 'Save Job';
      }
    } catch (error) {
      console.error('Toggle save error:', error);
    } finally {
      button.disabled = false;
    }
  });
});
