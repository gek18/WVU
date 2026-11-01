(() => {
  const shell = document.querySelector('[data-app-shell]');
  if (!shell) return;

  const themeButton = document.querySelector('[data-theme-toggle]');
  const themeKey = 'yurttakip-theme';
  let savedTheme = 'soft';
  try { savedTheme = localStorage.getItem(themeKey) || 'soft'; } catch (_) {}
  const applyTheme = (theme) => {
    const selected = theme === 'night' ? 'night' : 'soft';
    shell.dataset.theme = selected;
    document.documentElement.style.colorScheme = selected === 'night' ? 'dark' : 'light';
    if (themeButton) themeButton.setAttribute('aria-pressed', String(selected === 'night'));
  };
  applyTheme(savedTheme);
  themeButton?.addEventListener('click', () => {
    const next = shell.dataset.theme === 'night' ? 'soft' : 'night';
    applyTheme(next);
    try { localStorage.setItem(themeKey, next); } catch (_) {}
  });

  const menu = document.getElementById('site-navigation');
  const menuToggle = document.querySelector('[data-nav-toggle]');
  const closeMenu = (restoreFocus = false) => {
    document.body.classList.remove('nav-open');
    menuToggle?.setAttribute('aria-expanded', 'false');
    menu?.setAttribute('aria-hidden', String(window.matchMedia('(max-width: 991px)').matches));
    if (restoreFocus) menuToggle?.focus();
  };
  menuToggle?.addEventListener('click', () => {
    const open = menuToggle.getAttribute('aria-expanded') !== 'true';
    document.body.classList.toggle('nav-open', open);
    menuToggle.setAttribute('aria-expanded', String(open));
    menu?.setAttribute('aria-hidden', String(!open));
    if (open) menu?.querySelector('a, button')?.focus();
  });
  document.querySelectorAll('[data-nav-close]').forEach((button) => button.addEventListener('click', () => closeMenu(true)));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.body.classList.contains('nav-open')) closeMenu(true);
  });
  window.matchMedia('(min-width: 992px)').addEventListener('change', (event) => {
    if (event.matches) {
      document.body.classList.remove('nav-open');
      menuToggle?.setAttribute('aria-expanded', 'false');
      menu?.setAttribute('aria-hidden', 'false');
    } else menu?.setAttribute('aria-hidden', 'true');
  });
  if (menu) menu.setAttribute('aria-hidden', String(window.matchMedia('(max-width: 991px)').matches));

  document.querySelectorAll('[data-flow-demo]').forEach((demo) => {
    const tabs = Array.from(demo.querySelectorAll('[data-flow-step]'));
    const panel = demo.querySelector('[role="tabpanel"]');
    const activate = (tab, focus = false) => {
      tabs.forEach((item) => {
        const active = item === tab;
        item.classList.toggle('active', active);
        item.setAttribute('aria-selected', String(active));
        item.tabIndex = active ? 0 : -1;
      });
      panel.textContent = tab.dataset.copy || '';
      panel.setAttribute('aria-labelledby', tab.id);
      if (focus) tab.focus();
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activate(tab));
      tab.addEventListener('keydown', (event) => {
        const rtl = document.documentElement.dir === 'rtl';
        let next = index;
        if (event.key === 'ArrowRight') next = (index + (rtl ? -1 : 1) + tabs.length) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + (rtl ? 1 : -1) + tabs.length) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault();
        activate(tabs[next], true);
      });
    });
  });
})();
