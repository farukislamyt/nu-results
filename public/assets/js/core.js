(async function(){
  const load = async (id, file) => {
    const target = document.getElementById(id);
    if (!target) return;
    try {
      const response = await fetch(file, {cache:'no-store'});
      if (!response.ok) throw new Error(`Failed to load ${file}`);
      target.innerHTML = await response.text();
    } catch (error) {
      console.error(error);
    }
  };

  await Promise.all([
    load('global-header','/components/header.html'),
    load('global-nav','/components/nav.html'),
    load('global-footer','/components/footer.html')
  ]);

  const module = document.body.dataset.module || 'home';
  document.querySelectorAll('[data-nav]').forEach(link => {
    if (link.dataset.nav === module) {
      link.classList.add('active');
      link.setAttribute('aria-current','page');
    }
  });

  const menu = document.getElementById('menu');
  const nav = document.getElementById('navLinks');
  if (menu && nav) {
    menu.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => nav.classList.remove('open')));
  }

  document.dispatchEvent(new CustomEvent('nu-layout-ready'));
})();