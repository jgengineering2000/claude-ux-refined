// Injects into the .bar of every Claude doc page:
//   LEFT  — "← Manifest" plain link (skipped if page already has one)
//   RIGHT — document generation timestamp (from filename) + ↻ Refresh button
// Skips entirely on manifest.html itself.
(function () {
  if (window.location.pathname.endsWith('/manifest.html')) return;

  function parseDateFromPath() {
    var filename = window.location.pathname.split('/').pop();
    var m = filename.match(/-(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})(?:\.html)?$/);
    if (!m) return '';
    var h = parseInt(m[4], 10);
    return m[1] + '-' + m[2] + '-' + m[3] + ' ' +
           (h % 12 || 12) + ':' + m[5] + (h >= 12 ? 'pm' : 'am');
  }

  function linkStyle(el) {
    el.style.cssText =
      'font-size:12px;color:var(--ac,#89b4fa);text-decoration:none;flex-shrink:0;white-space:nowrap';
    el.onmouseenter = function () { this.style.textDecoration = 'underline'; };
    el.onmouseleave = function () { this.style.textDecoration = 'none'; };
  }

  function chipStyle(el) {
    el.style.cssText =
      'background:none;border:1px solid var(--bd,#3a3a55);color:var(--mu,#7f849c);' +
      'font-size:11px;padding:2px 8px;border-radius:4px;cursor:pointer;font-family:inherit;flex-shrink:0';
    el.onmouseenter = function () {
      this.style.borderColor = 'var(--ac,#89b4fa)';
      this.style.color = 'var(--ac,#89b4fa)';
    };
    el.onmouseleave = function () {
      this.style.borderColor = 'var(--bd,#3a3a55)';
      this.style.color = 'var(--mu,#7f849c)';
    };
  }

  function inject() {
    var bar = document.querySelector('.bar');
    if (!bar) return;

    // ── Left: ← Manifest link — skip if bar already has one ─────────────
    if (!bar.querySelector('a[href="/manifest.html"]')) {
      var a = document.createElement('a');
      a.className = 'manifest-link';
      a.href = '/manifest.html';
      a.textContent = '← Manifest';
      linkStyle(a);
      bar.insertBefore(a, bar.firstChild);
    }

    // ── Right: timestamp + ↻ Refresh — skip if already injected ──────────
    if (bar.querySelector('.doc-right')) return;

    var dtStr = parseDateFromPath();
    var right = document.createElement('span');
    right.className = 'doc-right';
    right.style.cssText =
      'display:flex;align-items:center;gap:8px;flex-shrink:0;margin-left:auto';

    if (dtStr) {
      var ts = document.createElement('span');
      ts.style.cssText = 'font-size:11px;color:var(--mu,#7f849c);opacity:.75';
      ts.textContent = dtStr;
      right.appendChild(ts);
    }

    var btn = document.createElement('button');
    btn.textContent = '↻ Refresh';
    chipStyle(btn);
    btn.onclick = function () { window.location.reload(); };
    right.appendChild(btn);

    // Replace the existing margin-left:auto spacer (Alt+D label) if present
    var spacer = bar.querySelector('[style*="margin-left:auto"]');
    if (spacer) {
      bar.replaceChild(right, spacer);
    } else {
      bar.appendChild(right);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
}());
