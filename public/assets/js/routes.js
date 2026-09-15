(() => {
  const routes = { '/honours': 'honours', '/degree': 'degree', '/masters': 'masters' };
  const path = () => window.location.pathname.replace(/\/+$/, '') || '/';

  function setActive(module) {
    document.querySelectorAll('.site-nav .nav-link[data-module]').forEach(link => {
      const active = link.dataset.module === module;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    const home = document.querySelector('.site-nav .nav-link[href="/"]');
    if (home) {
      const active = !module;
      home.classList.toggle('active', active);
      if (active) home.setAttribute('aria-current', 'page');
      else home.removeAttribute('aria-current');
    }
  }

  function closeMobileNav() {
    const nav = document.getElementById('navLinks');
    const menu = document.getElementById('menu');
    if (nav) nav.classList.remove('open');
    if (menu) {
      menu.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-label', 'Open navigation');
    }
  }

  function openRoute(module, replace = false) {
    const target = module ? `/${module}` : '/';
    if (replace) window.history.replaceState({ module }, '', target);
    else if (window.location.pathname !== target) window.history.pushState({ module }, '', target);

    setActive(module);
    closeMobileNav();

    if (module && typeof chooseModule === 'function') chooseModule(module);
    else if (!module && typeof resetToChooser === 'function') resetToChooser();
  }

  document.addEventListener('click', event => {
    const moduleLink = event.target.closest('[data-module]');
    if (!moduleLink) return;
    const module = moduleLink.dataset.module;
    if (!routes[`/${module}`]) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openRoute(module);
  }, true);

  document.addEventListener('click', event => {
    const homeLink = event.target.closest('.site-nav a[href="/"]');
    if (!homeLink) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openRoute('');
  }, true);

  window.addEventListener('popstate', () => {
    const module = routes[path()];
    if (module) openRoute(module, true);
    else if (path() === '/') openRoute('', true);
  });

  window.addEventListener('DOMContentLoaded', () => {
    const module = routes[path()];
    if (module) openRoute(module, true);
    else setActive('');
  });
})();
