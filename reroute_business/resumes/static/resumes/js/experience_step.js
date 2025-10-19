// experience_step.js
// Same pattern as education. Also adds UX: if "currently_work_here" is checked,
// we disable and clear the end_date to prevent conflicting inputs.

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("experience-form");
  const addBtn = document.getElementById("add-experience-btn");
  const totalForms = document.getElementById("id_form-TOTAL_FORMS");
  const emptyTemplate = document.getElementById("empty-form-template");

  if (!form || !addBtn || !totalForms || !emptyTemplate) return;

  function toggleCurrent(scope) {
    const current = scope.querySelector('input[name$="-currently_work_here"]');
    const end = scope.querySelector('input[name$="-end_date"]');
    if (!current || !end) return;

    const apply = () => {
      if (current.checked) {
        end.value = "";
        end.disabled = true;
      } else {
        end.disabled = false;
      }
    };
    current.addEventListener("change", apply);
    apply(); // initial
  }

  function wireRow(scope) {
    // Delete checkbox UX (existing rows)
    const del = scope.querySelector('input[name$="-DELETE"]');
    if (del) {
      del.addEventListener("change", () => {
        scope.style.opacity = del.checked ? 0.6 : 1;
      });
    }
    // Current job toggle
    toggleCurrent(scope);
  }

  function addRow() {
    const idx = parseInt(totalForms.value, 10);
    const html = emptyTemplate.innerHTML.replace(/__prefix__/g, String(idx));

    const wrapper = document.createElement("div");
    wrapper.className = "formset-row border rounded p-4 mb-4";
    wrapper.innerHTML = html;

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-sm btn-outline-danger";
    removeBtn.textContent = "Remove this entry";
    removeBtn.addEventListener("click", () => {
      wrapper.remove();
      // Keep TOTAL_FORMS as-is; see comment in education_step.js
    });

    const nav = document.createElement("div");
    nav.className = "mt-2";
    nav.appendChild(removeBtn);
    wrapper.appendChild(nav);

    const navBlock = form.querySelector(".form-navigation");
    form.insertBefore(wrapper, navBlock);

    totalForms.value = String(idx + 1);
    wireRow(wrapper);
  }

  // Wire existing rows
  document.querySelectorAll("#experience-form .formset-row").forEach(wireRow);

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
    document.querySelectorAll('#experience-form .formset-row').forEach(scope => {
      const del = scope.querySelector('input[name$="-DELETE"]');
      if (del && del.checked) return;
      if (!rowHasAnyInput(scope)) return; // blank rows ignored

      const title = scope.querySelector('input[name$="-job_title"]');
      const company = scope.querySelector('input[name$="-company"]');
      const start = scope.querySelector('input[name$="-start_date"]');

      clearInvalid(title); clearInvalid(company); clearInvalid(start);
      if (!title || !title.value.trim()) { markInvalid(title, 'Job title is required.'); invalid = true; }
      if (!company || !company.value.trim()) { markInvalid(company, 'Company is required.'); invalid = true; }
      if (!start || !start.value.trim()) { markInvalid(start, 'Start date is required.'); invalid = true; }
      if (!invalid) validRows += 1;
    });
    // Require at least one valid row
    let global = document.getElementById('exp-global-error');
    if (!global) {
      global = document.createElement('div');
      global.id = 'exp-global-error';
      global.className = 'client-error';
      const heading = document.querySelector('.form-step-wrapper h2');
      if (heading && heading.parentNode) heading.parentNode.insertBefore(global, heading.nextSibling);
    }
    global.textContent = '';
    if (validRows === 0) {
      invalid = true;
      global.textContent = 'Please add at least one experience entry.';
    }
    if (invalid) {
      e.preventDefault();
      const first = document.querySelector('#experience-form .is-invalid');
      if (first) first.focus();
    }
  });
});
