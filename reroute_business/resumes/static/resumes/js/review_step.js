document.addEventListener('DOMContentLoaded', () => {
  const reorderUrl = document.body.dataset.reorderUrl;
  if (!reorderUrl) return;

  function enableDrag(listEl, payloadKey) {
    let dragged = null;

    listEl.querySelectorAll('.drag-item').forEach((item) => {
      item.draggable = true;
      item.addEventListener('dragstart', () => {
        dragged = item;
        item.classList.add('dragging');
      });
      item.addEventListener('dragend', () => {
        item.classList.remove('dragging');
        dragged = null;
        sendOrder();
      });
    });

    listEl.addEventListener('dragover', (e) => {
      e.preventDefault();
      const after = getDragAfter(listEl, e.clientY);
      if (!dragged) return;
      if (after == null) {
        listEl.appendChild(dragged);
      } else {
        listEl.insertBefore(dragged, after);
      }
    });

    function getDragAfter(container, y) {
      const items = [...container.querySelectorAll('.drag-item:not(.dragging)')];
      return items.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        }
        return closest;
      }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    function sendOrder() {
      const ids = [...listEl.querySelectorAll('.drag-item')]
        .map((el) => el.dataset.id)
        .filter((val) => val);
      postJSON(reorderUrl, { [payloadKey]: ids }).catch(() => {});
    }
  }

  const sectionList = document.querySelector('[data-reorder=\"sections\"]');
  const experienceList = document.querySelector('[data-reorder=\"experience\"]');
  const educationList = document.querySelector('[data-reorder=\"education\"]');

  if (sectionList) enableDrag(sectionList, 'section_order');
  if (experienceList) enableDrag(experienceList, 'experience_order');
  if (educationList) enableDrag(educationList, 'education_order');

  document.querySelectorAll('[data-edit-link]').forEach((el) => {
    el.addEventListener('click', () => {
      const target = el.dataset.editLink;
      if (target) window.location.href = target;
    });
  });
});
