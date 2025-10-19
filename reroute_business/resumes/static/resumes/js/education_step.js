// education_step.js
// Manages Django formset rows for Education: add new rows from the empty_form
// template, and gracefully handle deletions using the built-in DELETE checkbox.
// We DO NOT manually decrease TOTAL_FORMS when deleting existing rows — that’s
// Django’s job via the -DELETE flag. We DO physically remove brand-new rows
// that haven’t been submitted yet.

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("education-form");
  const addBtn = document.getElementById("add-education-btn");
  const totalForms = document.getElementById("id_form-TOTAL_FORMS");
  const emptyTemplate = document.getElementById("empty-form-template"); // contains empty_form HTML

  if (!form || !addBtn || !totalForms || !emptyTemplate) return;

  // Insert new row from template and rewire controls
  function addRow() {
    const idx = parseInt(totalForms.value, 10);
    const html = emptyTemplate.innerHTML.replace(/__prefix__/g, String(idx));

    const wrapper = document.createElement("div");
    wrapper.className = "formset-row border rounded p-4 mb-4";
    wrapper.innerHTML = html;

    // Add a lightweight “remove row” button for *new* rows only (UX sugar)
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-sm btn-outline-danger";
    removeBtn.textContent = "Remove this entry";
    removeBtn.addEventListener("click", () => {
      // Physically remove DOM for NEW rows only (safe since they aren't saved)
      wrapper.remove();
      // We must NOT decrement TOTAL_FORMS or indexes; Django can handle sparse indices.
      // Keeping indices stable avoids name collisions for inputs added after removal.
    });

    // Put the remove button at the bottom of the new row
    const nav = document.createElement("div");
    nav.className = "mt-2";
    nav.appendChild(removeBtn);
    wrapper.appendChild(nav);

    // Insert before navigation controls at bottom
    const navBlock = form.querySelector(".form-navigation");
    form.insertBefore(wrapper, navBlock);

    // Increment TOTAL_FORMS to register the new row
    totalForms.value = String(idx + 1);

    // Wire any row-specific behaviors (e.g., delete checkbox strike-through)
    wireRow(wrapper);
  }

  function wireRow(scope) {
    // Dim when DELETE checkbox is toggled on (existing rows only)
    const del = scope.querySelector('input[name$="-DELETE"]');
    if (del) {
      del.addEventListener("change", () => {
        scope.style.opacity = del.checked ? 0.6 : 1;
      });
    }
  }

  // Wire existing rows on first load
  document.querySelectorAll("#education-form .formset-row").forEach(wireRow);

  addBtn.addEventListener("click", addRow);

  // --- Client-side validation ---
  function markInvalid(input, msg) {
    if (!input) return;
    input.classList.add('is-invalid');
    let hint = input.nextElementSibling;
    if (!hint || !hint.classList || !hint.classList.contains('client-error')) {
      hint = document.createElement('div');
      hint.className = 'client-error';
      input.parentNode.insertBefore(hint, input.nextSibling);
    }
    hint.textContent = msg;
  }

  function clearInvalid(input) {
    if (!input) return;
    input.classList.remove('is-invalid');
    const hint = input.nextElementSibling;
    if (hint && hint.classList && hint.classList.contains('client-error')) {
      hint.remove();
    }
  }

  function rowHasAnyInput(scope) {
    const fields = scope.querySelectorAll('input, textarea, select');
    for (const el of fields) {
      if (el.type === 'checkbox') continue;
      if ((el.value || '').trim()) return true;
    }
    return false;
  }

  form.addEventListener('submit', (e) => {
    let invalid = false;
    let validRows = 0;
    document.querySelectorAll('#education-form .formset-row').forEach(scope => {
      const del = scope.querySelector('input[name$="-DELETE"]');
      if (del && del.checked) return;
      if (!rowHasAnyInput(scope)) return; // blank rows ignored

      const school = scope.querySelector('input[name$="-school"]');
      const start = scope.querySelector('input[name$="-start_date"]');

      clearInvalid(school); clearInvalid(start);
      if (!school || !school.value.trim()) { markInvalid(school, 'School is required.'); invalid = true; }
      if (!start || !start.value.trim()) { markInvalid(start, 'Start date is required.'); invalid = true; }
      if (!invalid) validRows += 1;
    });
    // Require at least one valid row
    let global = document.getElementById('edu-global-error');
    if (!global) {
      global = document.createElement('div');
      global.id = 'edu-global-error';
      global.className = 'client-error';
      const heading = document.querySelector('.form-step-wrapper h2');
      if (heading && heading.parentNode) heading.parentNode.insertBefore(global, heading.nextSibling);
    }
    global.textContent = '';
    if (validRows === 0) {
      invalid = true;
      global.textContent = 'Please add at least one education entry.';
    }
    if (invalid) {
      e.preventDefault();
      const first = document.querySelector('#education-form .is-invalid');
      if (first) first.focus();
    }
  });
});
