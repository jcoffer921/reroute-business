document.addEventListener("DOMContentLoaded", function () {
    // 🔁 1. Sidebar Toggle
    const container = document.getElementById("bioContainer");
    const button = document.getElementById("bioToggleBtn");

    if (container && button) {
        button.addEventListener("click", function () {
            container.classList.toggle("collapsed");
            button.innerHTML = container.classList.contains("collapsed") ? "⮞" : "⮜";
        });
    }

    // 🧭 2. Dashboard Tabs (Edit Profile, Saved Jobs, Resume)
    const navLinks = document.querySelectorAll(".dashboard-nav a");
    const sections = document.querySelectorAll(".dashboard-section");

    navLinks.forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const targetId = this.getAttribute("data-target");

            sections.forEach(section => {
                section.style.display = section.id === targetId ? "block" : "none";
            });

            navLinks.forEach(l => l.classList.remove("active"));
            this.classList.add("active");
        });
    });

    // 🧩 3. Subnav inside Edit Profile
    const subLinks = document.querySelectorAll(".profile-subnav a");
    const subSections = document.querySelectorAll(".profile-section");

    subLinks.forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const targetId = this.getAttribute("data-subtarget");

            subSections.forEach(section => {
                section.style.display = section.id === targetId ? "block" : "none";
            });

            subLinks.forEach(l => l.classList.remove("active"));
            this.classList.add("active");
        });
    });

    // ✅ 4. Handle AJAX Save for Each Profile Section
    const forms = document.querySelectorAll(".profile-section form, form.profile-section");
    const updateUrl = document.getElementById("dashboard-wrapper")?.dataset.updateUrl;

    forms.forEach(form => {
        form.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(form);
            fetch(updateUrl, {
                method: "POST",
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log("✅ Profile updated!");
                } else {
                    console.error("❌ Update failed.");
                }
            })
            .catch(() => console.error("❌ Network error."));
        });
    });
});

let cropper;

function openPhotoModal() {
  document.getElementById("photoModal").style.display = "block";
}

function closePhotoModal() {
  document.getElementById("photoModal").style.display = "none";
  if (cropper) {
    cropper.destroy();
    cropper = null;
  }
  document.getElementById("imagePreview").style.display = "none";
}

document.getElementById('uploadImageInput').addEventListener('change', function (e) {
  const file = e.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = function (event) {
      const img = document.getElementById('imagePreview');
      img.src = event.target.result;
      img.style.display = 'block';

      if (cropper) cropper.destroy();
      cropper = new Cropper(img, {
        aspectRatio: 1,
        viewMode: 1,
        autoCropArea: 1,
      });
    };
    reader.readAsDataURL(file);
  }
});

function submitCroppedImage(e) {
  e.preventDefault(); // prevent default form submission

  if (!cropper) return false;

  cropper.getCroppedCanvas({
    width: 300,
    height: 300
  }).toBlob(blob => {
    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    formData.append('cropped_image', blob, 'profile.jpg');

    fetch(uploadProfileURL, {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (response.ok) {
        window.location.reload();
      } else {
        alert("Upload failed.");
      }
    });
  });

  return false;
}

function triggerUpload() {
  document.getElementById("uploadImageInput").click();
}

function triggerCropEdit() {
  const img = document.getElementById('imagePreview');

  if (!img.src || img.style.display === "none") {
    alert("No image to edit.");
    return;
  }

  if (cropper) cropper.destroy(); // prevent duplicate cropper
  cropper = new Cropper(img, {
    aspectRatio: 1,
    viewMode: 1,
    autoCropArea: 1
  });

  // Show save button if hidden
  document.querySelector('.save-btn').style.display = 'inline-block';
}


function openFrameSelector() {
  alert("Frame selector coming soon!");
}
