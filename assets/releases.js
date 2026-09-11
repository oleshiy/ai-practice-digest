'use strict';
(() => {
  const list = document.querySelector('[data-release-list]');
  if (!list) return;
  const cards = [...list.querySelectorAll('[data-release]')];
  const more = document.querySelector('[data-show-more]');
  let visible = Number(list.dataset.initial) || 5;
  function render() {
    cards.forEach((card, index) => { card.hidden = index >= visible; });
    if (!more) return;
    const remaining = cards.length - visible;
    more.hidden = remaining <= 0;
    more.disabled = remaining <= 0;
    more.textContent = remaining > 0 ? `Показать ещё (${Math.min(10, remaining)})` : 'Показать ещё';
  }
  if (more) more.addEventListener('click', () => { visible += 10; render(); });
  render();
})();
