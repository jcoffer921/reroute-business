document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        const invalidFields = form.querySelectorAll(':invalid');

        invalidFields.forEach(field => {
            field.style.borderColor = '#e53935';
        });

        if (invalidFields.length > 0) {
            // Optional: focus first invalid field
            invalidFields[0].focus();
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const progressFill = document.querySelector('.progress-bar-fill');
    if (progressFill) {
        const currentWidth = progressFill.style.width;
        progressFill.style.width = '0%'; // reset first
        setTimeout(() => {
            progressFill.style.width = currentWidth;
        }, 100); // allow DOM to load first
    }
});

document.addEventListener('DOMContentLoaded', () => {
    function toggleField(selectId, otherValue, targetId) {
        const select = document.getElementById(selectId);
        const target = document.getElementById(targetId);

        if (!select || !target) return;

        const handleChange = () => {
            target.style.display = select.value === otherValue ? 'block' : 'none';
        };

        select.addEventListener('change', handleChange);
        handleChange(); // Initialize on page load
    }

    toggleField('id_pronouns', 'other', 'pronouns-other-group');
    toggleField('id_native_Language', 'other', 'language-other-group');
    // Repeat for Step 4 or other "other" fields
});

document.addEventListener('DOMContentLoaded', () => {
  function toggleExplanation(radioName, matchValue, targetId) {
    const radios = document.querySelectorAll(`input[name="${radioName}"]`);
    const target = document.getElementById(targetId);

    if (!radios.length || !target) return;

    function checkSelected() {
      const selected = document.querySelector(`input[name="${radioName}"]:checked`);
      target.style.display = selected && selected.value === matchValue ? "block" : "none";
    }

    radios.forEach(r => r.addEventListener('change', checkSelected));
    checkSelected();
  }

  // Call for each conditional field
  toggleExplanation('disability', 'yes', 'disability-explanation-group');
  toggleExplanation('veteran_status', 'yes', 'veteran-explanation-group');
});

document.addEventListener('DOMContentLoaded', () => {
  const firstErrorField = document.querySelector('.error');
  if (firstErrorField) {
    firstErrorField.focus();
  }
});

