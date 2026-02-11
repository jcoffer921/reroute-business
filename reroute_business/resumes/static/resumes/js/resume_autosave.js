function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

function debounce(fn, delay = 600) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

function postJSON(url, payload) {
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify(payload || {}),
  });
}

function setSavedText(el, text) {
  if (!el) return;
  el.textContent = text;
  if (text) {
    setTimeout(() => {
      el.textContent = '';
    }, 2000);
  }
}
