(() => {
  const routes = { '/honours': 'honours', '/degree': 'degree', '/masters': 'masters' };
  const base = 'https://nu-results-bd.vercel.app';
  const seo = {
    honours: { title: 'National University Results | Honours, Degree & Master’s', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online with NU Results. Fast, mobile-friendly result lookup and practical result-checking guides.', heading: 'National University Results', intro: 'Check Honours, Degree Pass and Master’s results online.', canonical: '/' },
    degree: { title: 'National University Results | Honours, Degree & Master’s', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online with NU Results. Fast, mobile-friendly result lookup and practical result-checking guides.', heading: 'National University Results', intro: 'Check Honours, Degree Pass and Master’s results online.', canonical: '/' },
    masters: { title: 'National University Results | Honours, Degree & Master’s', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online with NU Results. Fast, mobile-friendly result lookup and practical result-checking guides.', heading: 'National University Results', intro: 'Check Honours, Degree Pass and Master’s results online.', canonical: '/' }
  };
  const home = { title: 'National University Results | Honours, Degree & Master’s', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online with NU Results. Fast, mobile-friendly result lookup and practical result-checking guides.', heading: 'National University Results', intro: 'Check Honours, Degree Pass and Master’s results online.', canonical: '/' };
  const path = () => window.location.pathname.replace(/\/+$/, '') || '/';
  const absolute = p => `${base}${p}`;
  function setMeta(name, content) { let el = document.querySelector(`meta[name="${name}"]`); if (!el) { el = document.createElement('meta'); el.name = name; document.head.appendChild(el); } el.content = content; }
  function setProperty(property, content) { let el = document.querySelector(`meta[property="${property}"]`); if (!el) { el = document.createElement('meta'); el.setAttribute('property', property); document.head.appendChild(el); } el.content = content; }
  function applySEO() {
    const data = home;
    document.title = data.title;
    setMeta('description', data.description);
    const canonical = document.querySelector('link[rel="canonical"]'); if (canonical) canonical.href = absolute('/');
    setProperty('og:site_name', 'NU Results'); setProperty('og:title', data.title); setProperty('og:description', data.description); setProperty('og:type', 'website'); setProperty('og:url', absolute('/'));
    setMeta('twitter:card', 'summary'); setMeta('twitter:title', data.title); setMeta('twitter:description', data.description);
    const h1 = document.getElementById('home-title'), subtitle = document.querySelector('.home-selector-subtitle'), menu = document.querySelector('.official-menu'), intro = document.querySelector('.seo-intro-inner');
    if (h1) h1.textContent = data.heading;
    if (subtitle) subtitle.textContent = data.intro;
    if (menu) menu.hidden = false;
    if (intro) intro.innerHTML = '<h2 id="about-results-title">National University Result Archive</h2><p>NU Results is an independent, mobile-friendly interface for checking available National University Bangladesh result information. It supports Honours, Degree Pass and Master’s result searches and presents the response in a readable format.</p><p>Choose the result category that matches your examination, then enter the examination year and the requested roll, registration number and CAPTCHA. The result request is handled through the existing National University result workflow; this site does not create, modify or certify academic records.</p><h2>Choose your result type</h2><p><a href="/honours"><strong>Honours Results</strong></a> is for National University Honours examinations. <a href="/degree"><strong>Degree Pass Results</strong></a> is for Degree Pass examinations. <a href="/masters"><strong>Master’s Results</strong></a> covers supported Master’s and Preliminary to Master’s result searches.</p><h2>Result checking guides</h2><p>Need help with the form? Read the <a href="/how-to-use.html">step-by-step guide to checking a National University result</a>. You can also review <a href="/grading.html">National University grading and GPA information</a> to understand how academic values returned by the result service are presented.</p><div class="seo-links"><a href="/honours">Check Honours Results</a><a href="/degree">Check Degree Pass Results</a><a href="/masters">Check Master’s Results</a><a href="/how-to-use.html">How to check a NU result</a><a href="/grading.html">NU grading and GPA information</a><a href="/about.html">About NU Results</a></div><h2>Independent service and official verification</h2><p>NU Results is not the official website of National University. It provides a convenient interface for requesting and reading result information returned by the official result service. For certificates, transcripts, academic decisions or final verification, use the <a href="https://results.nu.ac.bd" target="_blank" rel="noopener noreferrer">National University Result Portal</a>.</p>';
    const schema = document.getElementById('site-schema');
    if (schema) schema.textContent = JSON.stringify({ '@context': 'https://schema.org', '@type': 'WebSite', name: 'NU Results', url: base + '/', description: data.description });
  }
  function setActive(module) {
    document.querySelectorAll('.site-nav .nav-link[data-module]').forEach(link => { const active = link.dataset.module === module; link.classList.toggle('active', active); if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); });
    const homeLink = document.querySelector('.site-nav .nav-link[href="/"]');
    if (homeLink) { const active = !module; homeLink.classList.toggle('active', active); if (active) homeLink.setAttribute('aria-current', 'page'); else homeLink.removeAttribute('aria-current'); }
  }
  function closeMobileNav() { const nav = document.getElementById('navLinks'), menu = document.getElementById('menu'); if (nav) nav.classList.remove('open'); if (menu) { menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Open navigation'); } }
  function openRoute(module, replace = false) {
    const target = module ? `/${module}` : '/';
    if (replace) window.history.replaceState({ module }, '', target);
    else if (window.location.pathname !== target) window.history.pushState({ module }, '', target);
    setActive(module);
    applySEO();
    closeMobileNav();
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
    applySEO();
    setActive(module || '');
  });
})();
