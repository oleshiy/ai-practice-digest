'use strict';
(() => {
  const root = document.querySelector('[data-findings]');
  if (!root) return;
  const input = document.querySelector('#finding-search');
  const source = document.querySelector('#finding-source');
  const period = document.querySelector('#finding-period');
  const count = document.querySelector('#finding-count');
  const previous = document.querySelector('#finding-previous');
  const next = document.querySelector('#finding-next');
  const clear = document.querySelector('#finding-clear');
  const normalize = value => value.toLocaleLowerCase('ru').replaceAll('ё', 'е');
  const records = [...root.querySelectorAll('.finding')].map(node => ({node, text: normalize(node.textContent), source: node.dataset.source, fresh: node.dataset.fresh === 'true'}));
  let page = 0;
  const size = 20;
  const initial = new URLSearchParams(location.search).get('period');
  if (initial === 'last10') period.value = initial;
  function render(reset = false) {
    if (reset) page = 0;
    const words = normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    const matches = records.filter(item => (!source.value || item.source === source.value) && (period.value !== 'last10' || item.fresh) && words.every(word => item.text.includes(word)));
    const pages = Math.max(1, Math.ceil(matches.length / size));
    page = Math.min(page, pages - 1);
    records.forEach(item => { item.node.hidden = true; });
    matches.slice(page * size, (page + 1) * size).forEach(item => { item.node.hidden = false; });
    count.textContent = matches.length ? `Показаны ${page * size + 1}–${Math.min((page + 1) * size, matches.length)} из ${matches.length} находок` : 'Ничего не найдено. Измените запрос или фильтры.';
    previous.disabled = page === 0;
    next.disabled = page + 1 >= pages;
  }
  input.addEventListener('input', () => render(true));
  source.addEventListener('change', () => render(true));
  period.addEventListener('change', () => render(true));
  previous.addEventListener('click', () => { page--; render(); });
  next.addEventListener('click', () => { page++; render(); });
  clear.addEventListener('click', () => { input.value = ''; source.value = ''; period.value = 'last30'; render(true); input.focus(); });
  render();
})();
