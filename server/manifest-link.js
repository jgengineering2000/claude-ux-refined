// Injects a "Manifest" chip into the .bar of every Claude doc page.
// Skips injection on manifest.html itself.
(function () {
  if (window.location.pathname.endsWith('/manifest.html')) return;
  function inject() {
    var bar = document.querySelector('.bar');
    if (!bar || bar.querySelector('.manifest-link')) return;
    var a = document.createElement('a');
    a.className = 'manifest-link';
    a.href = '/manifest.html';
    a.textContent = 'Manifest';
    a.title = 'All documents';
    a.style.cssText =
      'font-size:11px;color:var(--mu,#7f849c);text-decoration:none;' +
      'border:1px solid var(--bd,#3a3a55);padding:2px 8px;border-radius:4px;' +
      'margin-left:auto;flex-shrink:0;font-family:inherit;white-space:nowrap';
    a.onmouseenter = function () {
      this.style.borderColor = 'var(--ac,#89b4fa)';
      this.style.color = 'var(--ac,#89b4fa)';
    };
    a.onmouseleave = function () {
      this.style.borderColor = 'var(--bd,#3a3a55)';
      this.style.color = 'var(--mu,#7f849c)';
    };
    // Remove margin-left:auto from the existing right-side spacer (Alt+D label)
    // so Manifest takes over the right-push role.
    var spacer = bar.querySelector('[style*="margin-left:auto"]');
    if (spacer) {
      spacer.style.marginLeft = '';
      bar.insertBefore(a, spacer);
    } else {
      bar.appendChild(a);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
}());
