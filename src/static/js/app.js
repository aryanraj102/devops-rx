// Drag & drop
(function () {
  var zone = document.getElementById('drop-zone');
  var input = document.getElementById('log_file');
  var body = document.getElementById('drop-body');
  var chosen = document.getElementById('file-chosen');

  if (!zone) return;

  zone.addEventListener('dragover', function (e) {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', function () {
    zone.classList.remove('drag-over');
  });
  zone.addEventListener('drop', function (e) {
    e.preventDefault();
    zone.classList.remove('drag-over');
    var files = e.dataTransfer.files;
    if (files.length) {
      input.files = files;
      showFileName(files[0].name);
    }
  });
  if (input) {
    input.addEventListener('change', function () {
      if (input.files.length) showFileName(input.files[0].name);
    });
  }

  function showFileName(name) {
    if (body) body.style.display = 'none';
    if (chosen) { chosen.textContent = '📄 ' + name; chosen.style.display = 'block'; }
  }
})();

// Analyze form spinner
(function () {
  var form = document.getElementById('analyze-form');
  var btn = document.getElementById('analyze-btn');
  var label = document.getElementById('btn-label');
  var spinner = document.getElementById('btn-spinner');

  if (!form) return;

  form.addEventListener('submit', function () {
    if (label) label.textContent = 'Analyzing…';
    if (spinner) spinner.style.display = 'inline-block';
    if (btn) btn.disabled = true;
  });
})();

// Auto-dismiss flash messages after 5s
(function () {
  setTimeout(function () {
    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (el) {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    });
  }, 5000);
})();
