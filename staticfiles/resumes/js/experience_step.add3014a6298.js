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
});
