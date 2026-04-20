(function () {
  const KEY = 'theme';
  const root = document.documentElement;

  function apply(theme) {
    root.dataset.theme = theme;
    const btn = document.getElementById('themeToggle');
    if (btn) btn.dataset.theme = theme;
  }

  function detect() {
    const saved = localStorage.getItem(KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  apply(detect());

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  });

  window.__theme = { apply, detect };
})();
