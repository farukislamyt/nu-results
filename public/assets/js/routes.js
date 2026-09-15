(() => {
  const routes = { '/honours': 'honours', '/degree': 'degree', '/masters': 'masters' };
  const seo = {
    honours: { title: 'National University Honours Result | NU Honours Results', description: 'Check National University Bangladesh Honours results online by examination, year, roll and registration number.', heading: 'National University Honours Result', intro: 'Check available National University Honours examination results using the official result workflow and CAPTCHA.', canonical: '/honours' },
    degree: { title: 'National University Degree Result | NU Degree Pass Results', description: 'Check National University Bangladesh Degree Pass results online by examination, year, roll and registration number.', heading: 'National University Degree Pass Result', intro: 'Check available National University Degree Pass examination results using the official result workflow and CAPTCHA.', canonical: '/degree' },
    masters: { title: "National University Master's Result | NU Master's Results", description: "Check National University Bangladesh Master's results online by examination, year, roll and registration number.", heading: "National University Master's Result", intro: "Check available National University Master's and Preliminary to Master's results using the official result workflow and CAPTCHA.", canonical: '/masters' }
  };
  const path = () => window.location.pathname.replace(/\/+$/, '') || '/';
  const absolute = p => `${window.location.origin}${p}`;

  function setMeta(name, content) {
    let el = document.querySelector(`meta[name="${name}"]`);
    if (!el) { el = document.createElement('meta'); el.name = name; document.head.appendChild(el); }
    el.content = content;
  }
  function setProperty(property, content) {
    let el = document.querySelector(`meta[property="${property}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute('property', property); document.head.appendChild(el); }
    el.content = content;
  }
  function applySEO(module) {
    const data = module ? seo[module] : { title: 'National University Result Archive | Honours, Degree & Master’s Results', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online.', heading: 'Select Result Type', intro: 'Choose the National University result category you want to view.' };
    document.title = data.title;
    setMeta('description', data.description);
    const canonical = document.querySelector('link[rel="canonical"]');
    if (canonical) canonical.href = absolute(data.canonical || '/');
    setProperty('og:title', data.title);
    setProperty('og:description', data.description);
    setProperty('og:type', 'website');
    setProperty('og:url', absolute(data.canonical || '/'));
    setMeta('twitter:card', 'summary');
    setMeta('twitter:title', data.title);
    setMeta('twitter:description', data.description);
    const h1 = document.getElementById('home-title');
    const subtitle = document.querySelector('.home-selector-subtitle');
    const menu = document.querySelector('.official-menu');
    if (h1) h1.textContent = data.heading;
    if (subtitle) subtitle.textContent = data.intro;
    if (menu) menu.hidden = Boolean(module);
    const schema = document.getElementById('site-schema');
    if (schema) schema.textContent = JSON.stringify({ '@context': 'https://schema.org', '@type': 'WebSite', name: 'National University Results Archive', url: absolute(data.canonical || '/'), description: data.description, potentialAction: { '@type': 'SearchAction', target: `${absolute('/')}?q={search_term_string}`, 'query-input': 'required name=search_term_string' } });
  }

  function setActive(module) {
    document.querySelectorAll('.site-nav .nav-link[data-module]').forEach(link => {
      const active = link.dataset.module === module;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    const home = document.querySelector('.site-nav .nav-link[href="/"]');
    if (home) { const active = !module; home.classList.toggle('active', active); if (active) home.setAttribute('aria-current', 'page'); else home.removeAttribute('aria-current'); }
  }
  function closeMobileNav() {
    const nav = document.getElementById('navLinks'), menu = document.getElementById('menu');
    if (nav) nav.classList.remove('open');
    if (menu) { menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Open navigation'); }
  }
  function openRoute(module, replace = false) {
    const target = module ? `/${module}` : '/';
    if (replace) window.history.replaceState({ module }, '', target); else if (window.location.pathname !== target) window.history.pushState({ module }, '', target);
    setActive(module); applySEO(module); closeMobileNav();
    if (module && typeof chooseModule === 'function') chooseModule(module); else if (!module && typeof resetToChooser === 'function') resetToChooser();
  }
  document.addEventListener('click', event => {
    const moduleLink = event.target.closest('[data-module]');
    if (!moduleLink) return;
    const module = moduleLink.dataset.module;
    if (!routes[`/${module}`]) return;
    event.preventDefault(); event.stopImmediatePropagation(); openRoute(module);
  }, true);
  document.addEventListener('click', event => {
    const homeLink = event.target.closest('.site-nav a[href="/"]');
    if (!homeLink) return;
    event.preventDefault(); event.stopImmediatePropagation(); openRoute('');
  }, true);
  window.addEventListener('popstate', () => { const module = routes[path()]; if (module) openRoute(module, true); else if (path() === '/') openRoute('', true); });
  window.addEventListener('DOMContentLoaded', () => { const module = routes[path()]; applySEO(module || ''); if (module) openRoute(module, true); else setActive(''); });
})();
