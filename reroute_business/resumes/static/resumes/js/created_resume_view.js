// resumes/js/created_resume_view.js
// PURPOSE: Save a "created" resume via JSON POST with reliable CSRF.
// IMPROVEMENTS:
//  - Guards against double-clicks and offline state
//  - Timeout + AbortController for hung requests
//  - Safer JSON parsing (handles non-JSON error bodies)
//  - Clear UI state helpers (spinner, status messages)
//  - Accessible status updates (aria-live)

"use strict";

/* ---------------- CSRF Helper (standard Django pattern) ---------------- */
function getCookie(name) {
  // Looks up "name=value" inside document.cookie safely
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift() || "");
  return null;
}

/* ---------------- Small Utilities ---------------- */
const SAVE_TIMEOUT_MS = 12000; // 12s network timeout

function withTimeout(promise, ms) {
  // Wrap a promise with a timeout using AbortController
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), ms);
  const wrapped = promise(controller.signal).finally(() => clearTimeout(id));
  return wrapped;
}

async function safeJson(res) {
  // Parse JSON only when content-type looks like JSON; otherwise return {}
  const ct = res.headers.get("content-type") || "";
  if (ct.toLowerCase().includes("application/json")) {
    try { return await res.json(); } catch (_) { return {}; }
  }
  return {};
}

/* ---------------- DOM Ready ---------------- */
document.addEventListener("DOMContentLoaded", () => {
  const saveBtn  = document.getElementById("saveResumeBtn");
  const statusEl = document.getElementById("saveStatus");
  if (!saveBtn || !statusEl) return;

  // Make status updates accessible to screen readers
  statusEl.setAttribute("role", "status");
  statusEl.setAttribute("aria-live", "polite");

  const url = saveBtn.dataset.saveUrl;
  const resumeId = saveBtn.dataset.resumeId;
  const spinner = saveBtn.querySelector(".spinner");
  const csrftoken = getCookie("csrftoken");

  if (!csrftoken) {
    // Helpful console note if CSRF not present (misconfigured middleware)
    console.warn("CSRF cookie not found. Is CsrfViewMiddleware enabled?");
  }

  // Track if a save is in-flight to prevent double submits
  let saving = false;

  function setSavingState(isSaving, msg) {
    saving = isSaving;
    if (spinner) spinner.style.display = isSaving ? "inline-block" : "none";
    saveBtn.disabled = isSaving;
    statusEl.textContent = msg || "";
  }

  async function doSave(signal) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken || "",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ resume_id: resumeId }),
      signal
    });
  }

  saveBtn.addEventListener("click", async () => {
    // 1) Prevent duplicate clicks & catch obvious offline state
    if (saving) return;
    if (!navigator.onLine) {
      statusEl.textContent = "⚠️ You appear to be offline. Please reconnect and try again.";
      return;
    }

    try {
      setSavingState(true, "Saving…");

      // 2) Perform fetch with a timeout
      const res = await withTimeout(doSave, SAVE_TIMEOUT_MS);
      const data = await safeJson(res);

      // 3) Handle common auth errors explicitly
      if (res.status === 401 || res.status === 403) {
        setSavingState(false, "🔒 Session expired. Please sign in again and retry.");
        return;
      }

      // 4) Success / failure messaging
      if (res.ok && data.status === "success") {
        setSavingState(false, "✅ Saved!");
        // Optional: clear the message after a short delay
        setTimeout(() => { if (!saving) statusEl.textContent = ""; }, 2000);
      } else {
        const errText = (data && data.error) ? `: ${data.error}` : "";
        setSavingState(false, `❌ Save failed${errText}.`);
      }
    } catch (err) {
      // AbortError => network timeout or manual abort
      const timedOut = (err && err.name === "AbortError");
      console.error(err);
      setSavingState(false, timedOut ? "⏳ Save timed out. Please try again." : "❌ Save error. Please try again.");
    }
  });
});
