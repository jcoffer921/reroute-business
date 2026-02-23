(function () {
  function initAdminPortal() {
    const modal = document.getElementById("confirmModal");
    const msgEl = document.getElementById("confirmModalMessage");
    const btnOk = document.getElementById("confirmOk");
    const btnCancel = document.getElementById("confirmCancel");
    const backdrop = document.querySelector(".rr-modal__backdrop");
    let pendingForm = null;

    function openModal(message, form) {
      pendingForm = form;
      if (msgEl) msgEl.textContent = message || "Are you sure?";
      if (modal) {
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
      }
    }

    function closeModal() {
      if (modal) {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
      }
      pendingForm = null;
    }

    if (btnOk && !btnOk.dataset.bound) {
      btnOk.dataset.bound = "1";
      btnOk.addEventListener("click", () => {
        if (pendingForm) pendingForm.submit();
        closeModal();
      });
    }

    if (btnCancel && !btnCancel.dataset.bound) {
      btnCancel.dataset.bound = "1";
      btnCancel.addEventListener("click", closeModal);
    }

    if (backdrop && !backdrop.dataset.bound) {
      backdrop.dataset.bound = "1";
      backdrop.addEventListener("click", closeModal);
    }

    if (!document.body.dataset.adminPortalEscBound) {
      document.body.dataset.adminPortalEscBound = "1";
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeModal();
      });
    }

    document.querySelectorAll("form.js-confirm").forEach((form) => {
      if (form.dataset.bound) return;
      form.dataset.bound = "1";
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        openModal(form.dataset.message || "Are you sure?", form);
      });
    });

    const chartCanvas = document.getElementById("weeklyActivityChart");
    if (!chartCanvas) return;

    function renderWeeklyChart() {
      if (!window.Chart) return false;
      if ((chartCanvas.clientWidth || 0) < 40 || (chartCanvas.clientHeight || 0) < 40) return false;

      const labels = (chartCanvas.dataset.labels || "").split(",").filter(Boolean);
      const users = (chartCanvas.dataset.users || "").split(",").map((v) => Number(v || 0));
      const jobs = (chartCanvas.dataset.jobs || "").split(",").map((v) => Number(v || 0));
      const applications = (chartCanvas.dataset.applications || "").split(",").map((v) => Number(v || 0));
      const yMax = Math.max(Number(chartCanvas.dataset.max || 8) || 8, ...users, ...jobs, ...applications, 1);

      if (window.__weeklyActivityChart && typeof window.__weeklyActivityChart.destroy === "function") {
        window.__weeklyActivityChart.destroy();
      }

      window.__weeklyActivityChart = new Chart(chartCanvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "New Users",
              data: users,
              borderColor: "#4f5dff",
              backgroundColor: "#4f5dff",
              borderWidth: 2.25,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHitRadius: 18,
              tension: 0.42,
            },
            {
              label: "Jobs Posted",
              data: jobs,
              borderColor: "#10b981",
              backgroundColor: "#10b981",
              borderWidth: 2.25,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHitRadius: 18,
              tension: 0.42,
            },
            {
              label: "Applications",
              data: applications,
              borderColor: "#f59e0b",
              backgroundColor: "#f59e0b",
              borderWidth: 2.25,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHitRadius: 18,
              tension: 0.42,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          interaction: {
            mode: "index",
            intersect: false,
          },
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              enabled: true,
              backgroundColor: "#ffffff",
              titleColor: "#0f172a",
              bodyColor: "#334155",
              borderColor: "#dbe2ec",
              borderWidth: 1,
              displayColors: true,
              padding: 10,
            },
          },
          scales: {
            x: {
              grid: {
                display: false,
              },
              ticks: {
                color: "#8b95a6",
              },
              border: {
                display: false,
              },
            },
            y: {
              beginAtZero: true,
              suggestedMax: yMax,
              ticks: {
                color: "#8b95a6",
                stepSize: 2,
              },
              grid: {
                color: "#e6ebf2",
              },
              border: {
                display: false,
              },
            },
          },
        },
      });

      return true;
    }

    let attempts = 0;
    const maxAttempts = 30;
    const retryMs = 100;

    const tryInit = () => {
      attempts += 1;
      if (renderWeeklyChart()) return;
      if (attempts < maxAttempts) {
        window.setTimeout(tryInit, retryMs);
      }
    };

    const reinit = () => {
      attempts = 0;
      tryInit();
    };

    reinit();
    window.addEventListener("load", reinit);
    window.addEventListener("pageshow", reinit);

    if (!window.__weeklyChartResizeBound) {
      window.__weeklyChartResizeBound = true;
      window.addEventListener("resize", () => {
        if (window.__weeklyActivityChart && typeof window.__weeklyActivityChart.resize === "function") {
          window.__weeklyActivityChart.resize();
        }
      });
    }

    if (window.ResizeObserver) {
      if (window.__weeklyChartResizeObserver) {
        window.__weeklyChartResizeObserver.disconnect();
      }
      window.__weeklyChartResizeObserver = new ResizeObserver(() => {
        reinit();
      });
      window.__weeklyChartResizeObserver.observe(chartCanvas);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminPortal, { once: true });
  } else {
    initAdminPortal();
  }
})();
