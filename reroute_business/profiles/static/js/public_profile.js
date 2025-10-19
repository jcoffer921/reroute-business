/* ============================================================================
 * ReRoute — Public Profile JS (Employer-facing, read-only)
 * Purpose:
 *   - Accessible tab switching for public profile sections
 *   - Small UI niceties: copy-to-clipboard, simple POST actions (e.g., shortlist)
 *   - Zero overlap with owner slide-in edit logic (handled by profile_panels.js)
 *
 * Assumptions:
 *   - Tabs use ARIA roles: [role="tablist"] > [role="tab"] with aria-controls -> [role="tabpanel"]
 *   - Optional action buttons use data-action + data-url, e.g.:
 *       <button data-action="shortlist" data-url="/profiles/123/shortlist/">Shortlist</button>
 *   - Copy buttons use data-copy pointing at a selector:
 *       <button data-copy="#emailText">Copy email</button><span id="emailText">user@mail.com</span>
 *   - CSRF cookie is named "csrftoken" (Django default)
 * ========================================================================== */

(() => {
  // ---------------------------------------------------------------------------
  // Small utilities
  // ---------------------------------------------------------------------------

  /**
   * Query helper (single element).
   */
  const qs = (sel, root = document) => root.querySelector(sel);

  /**
   * Query helper (NodeList to Array).
   */
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /**
   * Event helper.
   */
  const on = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);

  /**
   * Read csrftoken from cookie (Django standard).
   */
  const getCSRF = () => {
    const name = "csrftoken";
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
    return null;
  };

  /**
   * POST JSON helper for tiny actions (e.g., shortlist). Returns parsed JSON or throws.
   * NOTE: Response shape is expected as: { ok: true, ... } (matches our views).
   */
  async function postJSON(url, data = {}) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRF() || "",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(data),
    });
    let payload = {};
    try { payload = await resp.json(); } catch (_) {}
    if (!resp.ok || payload.ok !== true) {
      const message = (payload && (payload.message || payload.error)) || "Request failed";
      throw new Error(message);
    }
    return payload;
  }

  /**
   * Lightweight toast (optional). If you already have a sitewide toast, this will
   * defer to window.showToast. Otherwise, it uses alert as a minimal fallback.
   */
  function toast(msg) {
    if (typeof window.showToast === "function") {
      window.showToast(msg);
    } else {
      // Minimal fallback — replace with a nicer inline UI if you prefer
      // eslint-disable-next-line no-alert
      alert(msg);
    }
  }

  // ---------------------------------------------------------------------------
  // Accessible Tabs (public profile sections)
  // ---------------------------------------------------------------------------
  function initTabs() {
    // Find each tablist on the page (you may have only one)
    qsa('[role="tablist"]').forEach((tablist) => {
      const tabs = qsa('[role="tab"]', tablist);
      const panels = qsa('[role="tabpanel"]', tablist.parentElement || document);

      // Helper: show a specific tab + associated panel
      function activateTab(tab) {
        // Deactivate all
        tabs.forEach((t) => {
          t.setAttribute("aria-selected", "false");
          t.tabIndex = -1;
        });
        panels.forEach((p) => p.setAttribute("hidden", "true"));

        // Activate current
        tab.setAttribute("aria-selected", "true");
        tab.removeAttribute("tabindex");

        const panelId = tab.getAttribute("aria-controls");
        const panel = panelId ? document.getElementById(panelId) : null;
        if (panel) panel.removeAttribute("hidden");
        tab.focus({ preventScroll: true });
      }

      // Click handling
      tabs.forEach((tab) => {
        on(tab, "click", (e) => {
          e.preventDefault();
          activateTab(tab);
        });

        // Keyboard navigation: Left/Right arrows move across tabs
        on(tab, "keydown", (e) => {
          const i = tabs.indexOf(tab);
          if (e.key === "ArrowRight") {
            e.preventDefault();
            activateTab(tabs[(i + 1) % tabs.length]);
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            activateTab(tabs[(i - 1 + tabs.length) % tabs.length]);
          }
        });
      });

      // Ensure exactly one tab starts as selected; if none, select first
      const selected = tabs.find((t) => t.getAttribute("aria-selected") === "true");
      activateTab(selected || tabs[0]);
    });
  }

  // ---------------------------------------------------------------------------
  // Copy-to-clipboard buttons (email, phone, etc.)
  // ---------------------------------------------------------------------------
  function initCopyButtons() {
    qsa("[data-copy]").forEach((btn) => {
      on(btn, "click", async () => {
        const targetSel = btn.getAttribute("data-copy");
        if (!targetSel) return;

        const target = qs(targetSel);
        const text = target ? (target.value || target.textContent || "").trim() : "";
        if (!text) return;

        try {
          await navigator.clipboard.writeText(text);
          toast("Copied to clipboard");
        } catch {
          // Fallback for older browsers
          const tmp = document.createElement("textarea");
          tmp.value = text;
          document.body.appendChild(tmp);
          tmp.select();
          try {
            document.execCommand("copy");
            toast("Copied to clipboard");
          } catch {
            toast("Copy failed");
          } finally {
            document.body.removeChild(tmp);
          }
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Lightweight public actions (no overlap with owner editing)
  //   Examples: shortlist / save candidate, request contact, flag profile, etc.
  //   Buttons require data-action and data-url; we POST {action} and toggle UI.
  // ---------------------------------------------------------------------------
  function initPublicActions() {
    qsa("[data-action][data-url]").forEach((btn) => {
      on(btn, "click", async () => {
        const action = btn.getAttribute("data-action");
        const url = btn.getAttribute("data-url");
        if (!action || !url) return;

        // Optimistic UI: disable while posting
        const originalText = btn.textContent;
        btn.disabled = true;

        try {
          const data = await postJSON(url, { action });
          // You can switch on action names to adjust UI
          switch (action) {
            case "shortlist": {
              btn.classList.toggle("is-active");
              btn.textContent = btn.classList.contains("is-active") ? "Shortlisted" : "Shortlist";
              toast("Updated shortlist");
              break;
            }
            case "request-contact": {
              btn.textContent = "Requested";
              toast("Contact request sent");
              break;
            }
            case "flag-profile": {
              toast("Profile flagged for review");
              break;
            }
            default: {
              // For unknown actions, just acknowledge success
              toast("Action completed");
            }
          }
        } catch (err) {
          // Restore original label on failure
          btn.textContent = originalText;
          toast(err.message || "Something went wrong");
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Optional: simple accordions for read-only sections (e.g., skills list)
  //   Markup example:
  //     <button class="accordion-toggle" aria-expanded="false" aria-controls="skillsPanel">Skills</button>
  //     <div id="skillsPanel" hidden> ... </div>
  // ---------------------------------------------------------------------------
  function initAccordions() {
    qsa(".accordion-toggle[aria-controls]").forEach((toggle) => {
      const panelId = toggle.getAttribute("aria-controls");
      const panel = panelId ? document.getElementById(panelId) : null;
      if (!panel) return;

      function setOpen(isOpen) {
        toggle.setAttribute("aria-expanded", String(isOpen));
        if (isOpen) panel.removeAttribute("hidden");
        else panel.setAttribute("hidden", "true");
      }

      on(toggle, "click", () => {
        const isOpen = toggle.getAttribute("aria-expanded") === "true";
        setOpen(!isOpen);
      });

      // Ensure an initial state (collapsed unless aria-expanded="true")
      const startOpen = toggle.getAttribute("aria-expanded") === "true";
      setOpen(startOpen);
    });
  }

  // ---------------------------------------------------------------------------
  // Init on DOM ready
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    initTabs();           // Section tabs (Overview, Resume, etc.)
    initCopyButtons();    // Copy email/phone, etc.
    initPublicActions();  // Shortlist / request contact / flag
    initAccordions();     // Optional collapsible sections
  });
})();
