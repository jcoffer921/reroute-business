(function(){
  function onReady(fn){
    if (document.readyState !== 'loading'){ fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  function buildLetters(element){
    var text = element.textContent || '';
    element.textContent = '';
    var letters = text.split('');
    var delays = [];
    letters.forEach(function(_, idx){
      delays[idx] = Math.random() * 0.8;
    });
    letters.forEach(function(char, idx){
      var span = document.createElement('span');
      span.className = 'clarify-letter';
      span.style.setProperty('--clarify-delay', delays[idx].toFixed(2) + 's');
      span.textContent = char === ' ' ? '\u00A0' : char;
      element.appendChild(span);
    });
  }

  onReady(function(){
    var targets = document.querySelectorAll('.clarify-text');
    targets.forEach(function(target){
      buildLetters(target);
    });
  });
})();
