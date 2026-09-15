(() => {
  const routes = { '/honours': 'honours', '/degree': 'degree', '/masters': 'masters' };
  const base = 'https://nu-results-bd.vercel.app';
  const seo = {
    honours: {
      title: 'National University Honours Result | NU Honours Results',
      description: 'Check National University Bangladesh Honours results by examination, year, roll and registration number with NU Results.',
      heading: 'National University Honours Result',
      intro: 'Check available National University Honours examination results using the official result workflow and CAPTCHA.',
      content: '<p>Use this page to check National University Bangladesh Honours result information. Select the correct Honours examination, enter the examination year, roll and registration number, then complete the CAPTCHA before viewing the returned result.</p><p>Honours result information may include student details, subject or course information, grades, credit values and GPA/CGPA when those fields are supplied by the National University result service. NU Results displays the returned information for convenient reading; it does not issue, change or certify academic records.</p><h2>How to check an Honours result</h2><ol><li>Select the appropriate Honours examination.</li><li>Enter the four-digit examination year.</li><li>Enter your examination roll and registration number.</li><li>Answer the current CAPTCHA and select <strong>View Result</strong>.</li></ol><p>For a detailed walkthrough, see <a href="/how-to-use.html">how to check a National University result</a>. For grade-point information, see <a href="/grading.html">NU grading and GPA information</a>.</p><p>For official verification or academic decisions, use the <a href="https://results.nu.ac.bd" target="_blank" rel="noopener noreferrer">official National University Result Portal</a>.</p>',
      canonical: '/honours'
    },
    degree: {
      title: 'National University Degree Result | NU Degree Pass Results',
      description: 'Check National University Bangladesh Degree Pass results by examination, year, roll and registration number with NU Results.',
      heading: 'National University Degree Pass Result',
      intro: 'Check available National University Degree Pass examination results using the official result workflow and CAPTCHA.',
      content: '<p>Use this page to check National University Bangladesh Degree Pass result information. Choose the appropriate Degree Pass examination and provide the examination year, registration number and any roll information requested by the form.</p><p>Degree Pass result responses can contain year-specific academic information and a GPA supplied by the National University result service. NU Results presents that returned information without inventing or altering academic values.</p><h2>How to check a Degree Pass result</h2><ol><li>Select the correct Degree Pass examination.</li><li>Enter the four-digit examination year.</li><li>Enter the examination roll if the form requires or accepts it.</li><li>Enter your registration number and current CAPTCHA answer.</li><li>Select <strong>View Result</strong> to request the result.</li></ol><p>If the result does not appear, confirm the examination, year and registration number, then refresh the CAPTCHA. See the <a href="/how-to-use.html">complete result-checking guide</a> for troubleshooting.</p><p>For official verification, use the <a href="https://results.nu.ac.bd" target="_blank" rel="noopener noreferrer">official National University Result Portal</a>.</p>',
      canonical: '/degree'
    },
    masters: {
      title: "National University Master's Result | NU Master's Results",
      description: "Check National University Bangladesh Master's results by examination, year, roll and registration number with NU Results.",
      heading: "National University Master's Result",
      intro: "Check available National University Master's and Preliminary to Master's results using the official result workflow and CAPTCHA.",
      content: '<p>Use this page to check National University Bangladesh Master’s result information. The available examination choices can include Master’s Final Result, Preliminary to Master’s Result and other result types supported by the current NU result service.</p><p>Enter the correct examination year, registration number and the examination roll when requested, then solve the current CAPTCHA. The viewer presents the result response returned by the NU service and does not create, modify or certify academic records.</p><h2>Master’s result search</h2><ol><li>Select the appropriate Master’s examination.</li><li>Enter the four-digit examination year.</li><li>Enter the exam roll when applicable.</li><li>Enter your registration number.</li><li>Complete the CAPTCHA and select <strong>View Result</strong>.</li></ol><p>Check the <a href="/how-to-use.html">result-checking guide</a> if you need help with the search form. You can also review <a href="/grading.html">grading and GPA information</a> for an explanation of how this interface presents returned academic values.</p><p>For official records and verification, use the <a href="https://results.nu.ac.bd" target="_blank" rel="noopener noreferrer">official National University Result Portal</a>.</p>",
      canonical: '/masters'
    }
  };
  const path = () => window.location.pathname.replace(/\/+$/, '') || '/';
  const absolute = p => `${base}${p}`;
  function setMeta(name, content) { let el = document.querySelector(`meta[name="${name}"]`); if (!el) { el = document.createElement('meta'); el.name = name; document.head.appendChild(el); } el.content = content; }
  function setProperty(property, content) { let el = document.querySelector(`meta[property="${property}"]`); if (!el) { el = document.createElement('meta'); el.setAttribute('property', property); document.head.appendChild(el); } el.content = content; }
  function applySEO(module) {
    const data = module ? seo[module] : { title: 'National University Results | Honours, Degree & Master’s', description: 'Check National University Bangladesh Honours, Degree Pass and Master’s results online with NU Results. Fast, mobile-friendly result lookup.', heading: 'National University Results', intro: 'Check Honours, Degree Pass and Master’s results online.', canonical: '/' };
    document.title = data.title;
    setMeta('description', data.description);
    const canonical = document.querySelector('link[rel="canonical"]'); if (canonical) canonical.href = absolute(data.canonical || '/');
    setProperty('og:title', data.title); setProperty('og:description', data.description); setProperty('og:type', 'website'); setProperty('og:url', absolute(data.canonical || '/'));
    setMeta('twitter:card', 'summary'); setMeta('twitter:title', data.title); setMeta('twitter:description', data.description);
    const h1 = document.getElementById('home-title'), subtitle = document.querySelector('.home-selector-subtitle'), menu = document.querySelector('.official-menu'), intro = document.querySelector('.seo-intro-inner');
    if (h1) h1.textContent = data.heading;
    if (subtitle) subtitle.textContent = data.intro;
    if (menu) menu.hidden = Boolean(module);
    if (intro) {
      if (module) intro.innerHTML = `<span class="hero-kicker">Result guide</span><h2 id="about-results-title">${data.heading}</h2>${data.content}`;
      else intro.innerHTML = '<h2 id="about-results-title">National University Result Archive</h2><p>NU Results is an independent, mobile-friendly interface for checking available National University Bangladesh result information. It supports Honours, Degree Pass and Master’s result searches and presents the response in a readable format.</p><p>Choose the result category that matches your examination, then enter the examination year and the requested roll, registration number and CAPTCHA. The result request is handled through the existing National University result workflow; this site does not create, modify or certify academic records.</p><div class="seo-links"><a href="/honours">Check Honours Results</a><a href="/degree">Check Degree Pass Results</a><a href="/masters">Check Master’s Results</a><a href="/how-to-use.html">How to check a NU result</a><a href="/grading.html">NU grading and GPA information</a><a href="/about.html">About NU Results</a></div><h3>Need the official result source?</h3><p>For official verification, certificates, transcripts and academic decisions, use the <a href="https://results.nu.ac.bd" target="_blank" rel="noopener noreferrer">National University Result Portal</a>.</p>';
    }
    const schema = document.getElementById('site-schema');
    if (schema) schema.textContent = JSON.stringify({ '@context': 'https://schema.org', '@type': 'WebPage', name: data.title, url: absolute(data.canonical || '/'), description: data.description, isPartOf: { '@type': 'WebSite', name: 'NU Results', url: base }, breadcrumb: { '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'Home', item: base + '/' }, ...(module ? [{ '@type': 'ListItem', position: 2, name: data.heading, item: absolute(data.canonical) }] : [])] } });
  }
  function setActive(module) {
    document.querySelectorAll('.site-nav .nav-link[data-module]').forEach(link => { const active = link.dataset.module === module; link.classList.toggle('active', active); if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); });
    const home = document.querySelector('.site-nav .nav-link[href="/"]'); if (home) { const active = !module; home.classList.toggle('active', active); if (active) home.setAttribute('aria-current', 'page'); else home.removeAttribute('aria-current'); }
  }
  function closeMobileNav() { const nav = document.getElementById('navLinks'), menu = document.getElementById('menu'); if (nav) nav.classList.remove('open'); if (menu) { menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Open navigation'); } }
  function openRoute(module, replace = false) { const target = module ? `/${module}` : '/'; if (replace) window.history.replaceState({ module }, '', target); else if (window.location.pathname !== target) window.history.pushState({ module }, '', target); setActive(module); applySEO(module); closeMobileNav(); if (module && typeof chooseModule === 'function') chooseModule(module); else if (!module && typeof resetToChooser === 'function') resetToChooser(); }
  document.addEventListener('click', event => { const moduleLink = event.target.closest('[data-module]'); if (!moduleLink) return; const module = moduleLink.dataset.module; if (!routes[`/${module}`]) return; event.preventDefault(); event.stopImmediatePropagation(); openRoute(module); }, true);
  document.addEventListener('click', event => { const homeLink = event.target.closest('.site-nav a[href="/"]'); if (!homeLink) return; event.preventDefault(); event.stopImmediatePropagation(); openRoute(''); }, true);
  window.addEventListener('popstate', () => { const module = routes[path()]; if (module) openRoute(module, true); else if (path() === '/') openRoute('', true); });
  window.addEventListener('DOMContentLoaded', () => { const module = routes[path()]; applySEO(module || ''); if (module) openRoute(module, true); else setActive(''); });
})();
