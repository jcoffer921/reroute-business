// ========== HELPER FUNCTIONS ==========

// Get content from an element by ID
function getText(id) {
  const el = document.getElementById(id);
  return el ? el.textContent.trim() : '';
}

// Get CSRF token from cookie
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ========== DATA COLLECTION ==========

function collectResumeData() {
  const data = {
    full_name: document.querySelector('h1[contenteditable]')?.textContent.trim() || '',
    contact_info: document.querySelector('.resume-header p[contenteditable]')?.textContent.trim() || '',
    summary: document.getElementById('summary-block')?.textContent.trim() || '',
    education: [],
    experience: [],
    skills: []
  };

  // Education
  document.querySelectorAll('.education-block').forEach(block => {
    data.education.push({
      school: block.querySelector('strong')?.textContent.trim() || '',
      degree: block.querySelector('em')?.textContent.trim() || '',
      dates: block.querySelector('span')?.textContent.trim() || '',
      description: block.querySelector('p')?.textContent.trim() || ''
    });
  });

  // Experience
  document.querySelectorAll('.experience-block').forEach(block => {
    const bullets = [];
    block.querySelectorAll('ul li').forEach(li => bullets.push(li.textContent.trim()));
    data.experience.push({
      job_title: block.querySelector('strong')?.textContent.trim() || '',
      company: block.querySelector('span')?.textContent.trim() || '',
      dates: block.querySelector('em')?.textContent.trim() || '',
      bullets: bullets
    });
  });

  // Skills
  document.querySelectorAll('.skills-list li').forEach(li => {
    const skill = li.textContent.trim();
    if (skill) data.skills.push(skill);
  });

  return data;
}

// ========== SAVE BUTTON ==========

function saveFinalEdits() {
  const resumeData = collectResumeData();
  const resumeId = document.getElementById('resume-preview').dataset.resumeId;

  return fetch(`/resume/${resumeId}/preview/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify(resumeData)
  })
  .then(response => {
    if (!response.ok) throw new Error('Failed to save resume.');
    return response.json();
  });
}

function triggerPrint() {
  console.log('🖨️ Print button clicked');
  saveFinalEdits()
    .then(() => {
      console.log('✅ Save successful, now printing...');
      window.print();
    })
    .catch(error => {
      alert('Could not save resume. Please try again before printing.');
      console.error('❌ Save error before print:', error);
    });
}



// ========== LIVE PREVIEW SYNC ==========

function syncLivePreview() {
  // Full name + contact
  const nameInput = document.querySelector('h1[contenteditable]');
  const contactInput = document.querySelector('.resume-header p[contenteditable]');
  const namePreview = document.getElementById('preview-name');
  const contactPreview = document.getElementById('preview-contact');

  if (nameInput && namePreview) {
    nameInput.addEventListener('input', () => {
      namePreview.textContent = nameInput.textContent.trim() || 'Your Name';
    });
  }

  if (contactInput && contactPreview) {
    contactInput.addEventListener('input', () => {
      contactPreview.textContent = contactInput.textContent.trim() || 'Email | Phone | Location';
    });
  }

  // Summary
  const summaryInput = document.getElementById('summary-block');
  const summaryPreview = document.getElementById('preview-summary');
  if (summaryInput && summaryPreview) {
    summaryInput.addEventListener('input', () => {
      summaryPreview.textContent = summaryInput.textContent.trim() || 'Professional summary...';
    });
  }

  // Education
  document.querySelectorAll('.education-block').forEach((block, i) => {
    block.querySelectorAll('[contenteditable]').forEach(editable => {
      editable.addEventListener('input', () => {
        const school = block.querySelector('strong')?.textContent.trim() || '';
        const degree = block.querySelector('em')?.textContent.trim() || '';
        const dates = block.querySelector('span')?.textContent.trim() || '';
        const desc = block.querySelector('p')?.textContent.trim() || '';

        document.getElementById(`preview-edu-school-${i}`).textContent = school;
        document.getElementById(`preview-edu-degree-${i}`).textContent = degree;
        document.getElementById(`preview-edu-dates-${i}`).textContent = dates;
        document.getElementById(`preview-edu-desc-${i}`).textContent = desc;
      });
    });
  });

  // Experience
  document.querySelectorAll('.experience-block').forEach((block, i) => {
    block.querySelectorAll('[contenteditable]').forEach(editable => {
      editable.addEventListener('input', () => {
        const job = block.querySelector('strong')?.textContent.trim() || '';
        const company = block.querySelector('span')?.textContent.trim() || '';
        const dates = block.querySelector('em')?.textContent.trim() || '';

        document.getElementById(`preview-exp-title-${i}`).textContent = job;
        document.getElementById(`preview-exp-company-${i}`).textContent = company;
        document.getElementById(`preview-exp-dates-${i}`).textContent = dates;

        const bullets = block.querySelectorAll('ul li');
        const previewBullets = document.getElementById(`preview-exp-bullets-${i}`);
        previewBullets.innerHTML = '';
        bullets.forEach(li => {
          const item = document.createElement('li');
          item.textContent = li.textContent.trim();
          previewBullets.appendChild(item);
        });
      });
    });
  });

  // Skills
  const skillInputs = document.querySelectorAll('.skills-list li');
  const skillsPreview = document.getElementById('preview-skills');
  if (skillsPreview) {
    skillInputs.forEach(li => {
      li.addEventListener('input', () => {
        skillsPreview.innerHTML = '';
        document.querySelectorAll('.skills-list li').forEach(skill => {
          const item = document.createElement('li');
          item.textContent = skill.textContent.trim();
          skillsPreview.appendChild(item);
        });
      });
    });
  }
}

// ========== INIT ==========

document.addEventListener('DOMContentLoaded', () => {
  syncLivePreview();
});
