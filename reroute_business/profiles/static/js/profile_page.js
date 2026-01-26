(function () {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProfileUploads);
  } else {
    initProfileUploads();
  }

  function initProfileUploads() {
    const avatarWrap = document.querySelector('[data-role="avatar-trigger"]');
    const coverWrap = document.querySelector('[data-role="cover-trigger"]');
    const avatarInput = document.getElementById('avatarInput');
    const coverInput = document.getElementById('coverInput');
    const avatarPreview = document.getElementById('avatarPreview');
    const coverPreview = document.getElementById('coverPreview');
    const saveAvatarBtn = document.getElementById('saveAvatarBtn');
    const saveCoverBtn = document.getElementById('saveCoverBtn');
    const bgModal = document.getElementById('bgModal');

    if (avatarWrap && avatarInput) {
      avatarWrap.addEventListener('click', () => avatarInput.click());
      avatarInput.addEventListener('change', () => handleFile(avatarInput, avatarPreview, saveAvatarBtn));
    }

    if (coverWrap && coverInput && !bgModal) {
      coverWrap.addEventListener('click', () => coverInput.click());
      coverInput.addEventListener('change', () => handleFile(coverInput, coverPreview, saveCoverBtn));
    }
  }

  function handleFile(inputEl, imgEl, saveBtn) {
    if (!inputEl || !inputEl.files || !inputEl.files[0] || !imgEl) return;
    const file = inputEl.files[0];
    if (!file.type || !file.type.startsWith('image/')) return;

    const url = URL.createObjectURL(file);
    imgEl.src = url;
    if (saveBtn) saveBtn.classList.remove('hidden');
  }
})();
