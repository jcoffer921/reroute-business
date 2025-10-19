document.addEventListener("DOMContentLoaded", () => {
  const tipElement = document.getElementById("tipText");
  const nextTipBtn = document.getElementById("nextTipBtn");

  const tips = [
    // Profile & Resume Tips
    { text: "💡 Upload your resume to unlock job matches instantly.", type: "profile" },
    { text: "📸 Add a profile picture to build trust with employers.", type: "profile" },
    { text: "📝 Keep your bio short, clear, and focused on your strengths.", type: "profile" },
    { text: "✅ Complete your profile to boost visibility to employers.", type: "profile" },
    { text: "📄 You can update your resume anytime from your dashboard.", type: "profile" },
    { text: "🔐 Keep your account info up to date and secure.", type: "profile" },
    { text: "🏷️ Use keywords in your skills to improve job matches.", type: "profile" },
    { text: "📍 Set your location so employers can find you more easily.", type: "profile" },
    { text: "💼 Track your applications directly from your dashboard.", type: "profile" },

    // Job Search Guidance
    { text: "🔎 Check ReRoute daily — new jobs are added all the time.", type: "job_search" },
    { text: "📬 Verify your email to receive job alerts and updates.", type: "job_search" },
    { text: "📅 Follow up on your applications after a few days.", type: "job_search" },
    { text: "📂 Save jobs you're interested in so you can apply later.", type: "job_search" },
    { text: "📈 Apply to multiple jobs to increase your chances.", type: "job_search" },
    { text: "🙋 Need help? Reach out to ReRoute Support anytime.", type: "job_search" },

    // Motivation & Encouragement
    { text: "🌱 Growth is a process. You're right where you need to be.", type: "motivation" },
    { text: "💪 You've made it this far. Keep going — your future is waiting.", type: "motivation" },
    { text: "🛠️ Your past doesn't define your future. Your effort does.", type: "motivation" },
    { text: "✨ Small consistent steps lead to big opportunities.", type: "motivation" },
    { text: "🚀 Every setback is a setup for a comeback.", type: "motivation" },
    { text: "🔥 You are more than your record. You are your potential.", type: "motivation" },
    { text: "🌟 Employers are looking for people just like you — show up strong.", type: "motivation" },
    { text: "📣 Believe in your story. It's powerful. It matters.", type: "motivation" },
    { text: "📘 ReRoute is your starting point — your next chapter begins now.", type: "motivation" }
  ];

  let index = Math.floor(Math.random() * tips.length);

  function showTip() {
    if (!tipElement) return;

    tipElement.classList.remove('visible');

    setTimeout(() => {
      tipElement.textContent = tips[index].text;
      tipElement.classList.add('visible');
      index = (index + 1) % tips.length;
    }, 300);
  }

  if (tipElement) {
    showTip(); // Initial tip
    setInterval(showTip, 8000); // Auto rotate every 8s

    if (nextTipBtn) {
      nextTipBtn.addEventListener("click", showTip);
    }
  }
});

(function () {
  const SCROLL_AMOUNT = 340;
  const container = document.getElementById("cardCarousel");
  const leftBtn = document.querySelector(".carousel-btn.left");
  const rightBtn = document.querySelector(".carousel-btn.right");

  function updateButtonStates() {
    leftBtn.disabled = container.scrollLeft === 0;
    rightBtn.disabled = container.scrollLeft + container.clientWidth >= container.scrollWidth;
  }

  window.scrollCarousel = function (direction) {
    container.scrollBy({ left: direction * SCROLL_AMOUNT, behavior: "smooth" });

    // Delay to ensure scroll position is updated
    setTimeout(updateButtonStates, 300);
  };

  // Initialize state on load
  window.addEventListener("load", updateButtonStates);
  container.addEventListener("scroll", updateButtonStates);
})();

function updateProgress(stepsCompleted) {
  const total = 3;
  const percent = (stepsCompleted / total) * 100;

  document.querySelector(".progress-bar-fill").style.width = `${percent}%`;
  document.getElementById("progressCount").textContent = stepsCompleted;
}

function scrollSuggested(direction) {
  const container = document.getElementById("suggestedJobsCarousel");
  const scrollAmount = 340;
  container.scrollBy({
    left: direction * scrollAmount,
    behavior: "smooth"
  });
}
