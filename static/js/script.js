(() => {
  const root = document.documentElement;
  const themeButton = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');
  const year = document.getElementById('currentYear');
  const modal = document.getElementById('imageModal');
  const modalImage = modal && modal.querySelector('.modal-image');
  const closeButton = document.getElementById('modalClose');

  function setTheme(theme) {
    root.dataset.theme = theme;
    if (themeIcon) themeIcon.textContent = theme === 'dark' ? '☀' : '☾';
    if (themeButton) {
      themeButton.setAttribute('aria-label', theme === 'dark' ? '切换浅色模式' : '切换深色模式');
      themeButton.setAttribute('title', theme === 'dark' ? '切换浅色模式' : '切换深色模式');
    }
    try { localStorage.setItem('likui-theme', theme); } catch (_) {}
  }

  let savedTheme = '';
  try { savedTheme = localStorage.getItem('likui-theme') || ''; } catch (_) {}
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(savedTheme || (prefersDark ? 'dark' : 'light'));

  if (themeButton) {
    themeButton.addEventListener('click', () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));
  }
  if (year) year.textContent = new Date().getFullYear();

  const animatedItems = document.querySelectorAll('.resource-card, .project-card, .github-card, .skills-card');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    animatedItems.forEach((item) => {
      item.classList.add('reveal-ready');
      observer.observe(item);
    });
  }

  function openModal(src) {
    if (!modal || !modalImage || !src) return;
    modalImage.src = src;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  document.querySelectorAll('[data-preview-image]').forEach((button) => {
    button.addEventListener('click', () => openModal(button.dataset.previewImage));
  });
  if (closeButton) closeButton.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  }
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeModal(); });
})();