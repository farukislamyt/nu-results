(() => {
  const routes = { '/honours': 'honours', '/degree': 'degree', '/masters': 'masters' };
  const path = () => window.location.pathname.replace(/\/+$/, '') || '/';

  function openRoute(module, replace = false) {
    if (typeof chooseModule !== 'function') return;
    const target = module ? `/${module}` : '/';
    if (replace) window.history.replaceState({ module }, '', target);
    else window.history.pushState({ module }, '', target);
    if (module) chooseModule(module);
    else if (typeof resetToChooser === 'function') resetToChooser();
  }

  document.addEventListener('click', event => {
    const card = event.target.closest('.type-card[data-module]');
    if (!card) return;
    const module = card.dataset.module;
    if (!routes[`/${module}`]) return;
    event.preventDefault();
    openRoute(module);
  }, true);

  window.addEventListener('popstate', () => {
    const module = routes[path()];
    if (module) openRoute(module, true);
    else if (path() === '/' && typeof resetToChooser === 'function') resetToChooser();
  });

  window.addEventListener('DOMContentLoaded', () => {
    const module = routes[path()];
    if (module) openRoute(module, true);
  });
})();
