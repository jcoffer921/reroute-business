(function(){
  function parseJSON(id){ try{ const el=document.getElementById(id); return el ? JSON.parse(el.textContent||'{}') : {}; } catch(_){ return {}; } }
  window.dashboardData = parseJSON('admin-dashboard-data');
  document.addEventListener('DOMContentLoaded', function(){
    const data = window.dashboardData || {};
    const slides = document.querySelectorAll('.charts-carousel__slide');
    slides.forEach(slide => {
      const id = (slide.querySelector('.plotly-chart') || {}).id;
      if (id === 'applicationsChart' && (!data.applicationsByDay || !data.applicationsByDay.length)) slide.remove();
      if (id === 'employersChart' && (!data.employersByDay || !data.employersByDay.length)) slide.remove();
    });
  });
})();

