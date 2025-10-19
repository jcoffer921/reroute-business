//
// Employer Profile panel behavior
// - Opens the slide-out panel on "Edit Profile" click
// - Closes it on either top-right Cancel or bottom Cancel button
// - Uses .active and .hidden classes to control visibility and animation
//

(function () {
  // Cache DOM nodes for speed and clarity
  const openBtn = document.getElementById('openEditPanel');
  const closeBtn = document.getElementById('closeEditPanel');
  const cancelInside = document.getElementById('cancelInside');
  const panel = document.getElementById('editPanel');

  if (!panel) return; // Guard: if this isn’t the employer profile page

  // Helper to open the panel with a smooth transition
  function openPanel() {
    // Make it participate in layout so transitions can run
    panel.classList.remove('hidden');
    // Let the browser paint once before enabling the slide-in state
    requestAnimationFrame(() => {
      panel.classList.add('active');
      panel.setAttribute('aria-hidden', 'false');
    });
  }

  // Helper to close the panel with a smooth transition
  function closePanel() {
    panel.classList.remove('active');
    panel.setAttribute('aria-hidden', 'true');
    // After the transition, fully hide to avoid tab stops
    setTimeout(() => {
      panel.classList.add('hidden');
    }, 300); // Keep in sync with CSS transition (260ms rounded up)
  }

  // Wire up event listeners
  if (openBtn) openBtn.addEventListener('click', openPanel);
  if (closeBtn) closeBtn.addEventListener('click', closePanel);
  if (cancelInside) cancelInside.addEventListener('click', closePanel);
})();

