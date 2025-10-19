// === Live Preview Bindings for Resume Builder Steps ===

/**
 * Dynamically updates the preview field when the form input changes.
 * @param {string} inputId - ID of the form input element.
 * @param {string} previewId - ID of the preview element to update.
 * @param {string} fallback - Default text to show if input is empty.
 */
function bindLivePreview(inputId, previewId, fallback = '') {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  if (input && preview) {
    input.addEventListener('input', () => {
      preview.textContent = input.value || fallback;
    });
  }
}

/**
 * Binds preview updates for date ranges.
 */
function bindDateRangePreview(startId, endId, previewId, fallback = 'Start - End') {
  const startInput = document.getElementById(startId);
  const endInput = document.getElementById(endId);
  const preview = document.getElementById(previewId);

  function update() {
    if (!preview) return;
    const start = startInput?.value || '';
    const end = endInput?.value || '';
    preview.textContent = start || end ? `${start} – ${end}` : fallback;
  }

  startInput?.addEventListener('input', update);
  endInput?.addEventListener('input', update);

  update(); // initialize
}


/**
 * Binds a textarea input to a live preview bullet list.
 * Each line of the textarea becomes a bullet point.
 * @param {string} inputId - The ID of the textarea input.
 * @param {string} listId - The ID of the UL element to update.
 * @param {string} fallback - Default bullet if empty.
 */
function bindBulletPreview(inputId, listId, fallback = 'Bullet') {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);

  function updateList() {
    if (!input || !list) return;
    const lines = input.value.split('\n').filter(line => line.trim() !== '');
    list.innerHTML = '';
    if (lines.length === 0) {
      const li = document.createElement('li');
      li.textContent = fallback;
      list.appendChild(li);
    } else {
      lines.forEach(line => {
        const li = document.createElement('li');
        li.textContent = line;
        list.appendChild(li);
      });
    }
  }

  input?.addEventListener('input', updateList);
  updateList(); // Run once on load
}


document.addEventListener('DOMContentLoaded', () => {
  // Contact Info Bindings
  bindLivePreview('id_full_name', 'preview_full_name', 'Your Name');
  bindLivePreview('id_email', 'preview_email', 'email@example.com');
  bindLivePreview('id_phone', 'preview_phone', '(123) 456-7890');
  bindLivePreview('id_location', 'preview_location', 'City, State');

  // Summary
  bindLivePreview('id_summary', 'preview_summary', 'A brief summary of your qualifications and career goals.');

  // Bullet Key Insertion
  document.querySelectorAll("textarea").forEach(area => {
    area.addEventListener("keydown", function(e) {
      if (e.key === "Enter") {
        const cursor = this.selectionStart;
        const text = this.value;
        const before = text.substring(0, cursor);
        const after = text.substring(cursor);
        this.value = `${before}\n• ${after}`;
        e.preventDefault();
      }
    });
  });
});



function bindDynamicEducationPreviews() {
  const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
  const totalForms = parseInt(totalFormsInput?.value || 1);
  const container = document.getElementById('education-preview-container');
  if (!container) return;

  container.innerHTML = ''; // Clear previous preview blocks

  for (let i = 0; i < totalForms; i++) {
    const schoolId = `id_form-${i}-school`;
    const degreeId = `id_form-${i}-degree`;
    const startId = `id_form-${i}-start_date`;
    const endId = `id_form-${i}-end_date`;
    const descId = `id_form-${i}-description`;

    const previewBlock = document.createElement('div');
    previewBlock.className = 'education-preview-block';
    previewBlock.innerHTML = `
      <strong id="preview_school_${i}">School Name</strong><br>
      <em id="preview_degree_${i}">Degree</em><br>
      <span id="preview_edudates_${i}">Start – End</span>
      <p id="preview_edudesc_${i}">Description</p>
      <hr>
    `;
    container.appendChild(previewBlock);

    bindLivePreview(schoolId, `preview_school_${i}`, 'School Name');
    bindLivePreview(degreeId, `preview_degree_${i}`, 'Degree');
    bindLivePreview(descId, `preview_edudesc_${i}`, 'Course description');
    bindDateRangePreview(startId, endId, `preview_edudates_${i}`);
  }
}


document.addEventListener('DOMContentLoaded', () => {
  bindDynamicEducationPreviews();
});
