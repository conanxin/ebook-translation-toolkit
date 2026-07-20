(() => {
  const body = document.body;
  const modeButton = document.getElementById('reading-mode');
  const popover = document.getElementById('footnote-popover');
  const content = popover.querySelector('.footnote-content');
  const closeButton = popover.querySelector('.footnote-close');
  let active = null;

  const close = (restoreFocus = false) => {
    if (active) {
      active.setAttribute('aria-expanded', 'false');
      if (restoreFocus) active.focus();
    }
    active = null;
    popover.hidden = true;
    content.replaceChildren();
  };

  const position = trigger => {
    if (window.innerWidth <= 600) return;
    const rect = trigger.getBoundingClientRect();
    const gap = 10;
    const width = Math.min(430, window.innerWidth - 24);
    const left = Math.min(Math.max(12, rect.left - width / 3), window.innerWidth - width - 12);
    popover.style.width = `${width}px`;
    popover.style.left = `${left}px`;
    popover.style.right = 'auto';
    const height = popover.offsetHeight;
    const below = rect.bottom + gap;
    popover.style.top = `${below + height < window.innerHeight ? below : Math.max(12, rect.top - height - gap)}px`;
    popover.style.bottom = 'auto';
  };

  const open = trigger => {
    if (active === trigger) { close(true); return; }
    close(false);
    const number = trigger.dataset.footnote;
    const template = document.getElementById(`footnote-template-${number}`);
    if (!template) return;
    content.append(template.content.cloneNode(true));
    trigger.setAttribute('aria-expanded', 'true');
    active = trigger;
    popover.hidden = false;
    position(trigger);
  };

  document.addEventListener('click', event => {
    const trigger = event.target.closest('.footnote-trigger');
    if (trigger) { event.preventDefault(); open(trigger); return; }
    if (event.target.closest('.footnote-popover')) return;
    close(false);
  });
  closeButton.addEventListener('click', () => close(true));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !popover.hidden) { event.preventDefault(); close(true); }
  });
  window.addEventListener('resize', () => { if (active) position(active); });
  modeButton.addEventListener('click', () => {
    const continuous = body.classList.toggle('continuous-mode');
    body.classList.toggle('paged-mode', !continuous);
    modeButton.setAttribute('aria-pressed', String(continuous));
    modeButton.textContent = continuous ? '分页阅读模式' : '连续阅读模式';
    close(false);
  });
})();
