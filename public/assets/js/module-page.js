document.addEventListener('DOMContentLoaded', () => {
  const module = document.body.dataset.module;
  if (module && typeof chooseModule === 'function') chooseModule(module);
});
