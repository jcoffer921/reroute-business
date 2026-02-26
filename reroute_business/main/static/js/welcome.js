(function () {
  function track(eventName, metadata) {
    var payload = {
      event: eventName,
      metadata: metadata || {},
      source: (window.REROUTE_WELCOME && window.REROUTE_WELCOME.source) || "",
      at: new Date().toISOString()
    };

    // TODO: replace with server-side event ingestion endpoint.
    if (window.console && typeof window.console.info === "function") {
      window.console.info("[welcome-track]", payload);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    track("welcome_view", {
      path: window.location.pathname,
      hasSource: Boolean((window.REROUTE_WELCOME && window.REROUTE_WELCOME.source) || "")
    });

    var trackedLinks = document.querySelectorAll("[data-track]");
    trackedLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        track("welcome_click", {
          target: link.getAttribute("data-track"),
          href: link.getAttribute("href") || ""
        });
      });
    });
  });
})();
