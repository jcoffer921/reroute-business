document.addEventListener("DOMContentLoaded", function () {
  const fields = ["education", "experience", "skills", "certifications"];

  fields.forEach((field) => {
    const input = document.getElementById("id_" + field);
    const preview = document.getElementById("preview-" + field);
    if (!input || !preview) return;

    const updatePreview = () => {
      const lines = input.value.split('\n').filter((line) => line.trim() !== "");
      preview.innerHTML = "";
      lines.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        preview.appendChild(li);
      });
    };

    input.addEventListener("input", updatePreview);
    updatePreview(); // Initial call
  });
});
