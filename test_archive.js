'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = __dirname;
// The archive is derived from the editions at build time; read the built page back.
const page = fs.readFileSync(path.join(root, '_site/findings.html'), 'utf8');
const data = [...page.matchAll(/<article class="finding" data-source="([^"]+)" data-fresh="(true|false)"[^>]*>([\s\S]*?)<\/article>/g)]
  .map(m => ({source: m[1], fresh: m[2] === 'true', text: m[3].replace(/<[^>]+>/g, ' ')}));
assert(data.length > 20, 'archive needs more than one page of findings');
const nodes = data.map(item => ({hidden: false, textContent: item.text, dataset: {source: item.source, fresh: String(item.fresh)}}));
const topSource = [...data.reduce((m, x) => m.set(x.source, (m.get(x.source) || 0) + 1), new Map())].sort((a, b) => b[1] - a[1])[0][0];
const word = data[0].text.trim().split(/\s+/).find(w => /^[a-zA-Zа-яА-Я]{5,}$/.test(w)).toLowerCase();
const controls = {};
for (const id of ['finding-search','finding-source','finding-period','finding-count','finding-previous','finding-next','finding-clear']) {
  controls[`#${id}`] = {value: id === 'finding-period' ? 'last30' : '', textContent: '', disabled: false, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }, focus() {}};
}
const archive = {querySelectorAll() { return nodes; }};
const document = {querySelector(selector) { return selector === '[data-findings]' ? archive : controls[selector]; }};
vm.runInNewContext(fs.readFileSync(path.join(root, 'assets/findings.js'), 'utf8'), {document, location: {search: ''}, URLSearchParams});
const visible = () => nodes.filter(node => !node.hidden);
const fire = (id, event) => controls[`#${id}`].listeners[event]();
assert.equal(visible().length, 20);
assert.equal(nodes[0].hidden, false);
assert.equal(controls['#finding-previous'].disabled, true);
fire('finding-next','click');
assert.equal(nodes[0].hidden, true);
assert.equal(nodes[20].hidden, false);
controls['#finding-period'].value = 'last10'; fire('finding-period','change');
assert(visible().every(node => node.dataset.fresh === 'true'));
assert(controls['#finding-count'].textContent.includes(String(data.filter(x => x.fresh).length)));
controls['#finding-source'].value = topSource; fire('finding-source','change');
assert(visible().every(node => node.dataset.source === topSource));
controls['#finding-search'].value = 'zzzz-no-such-finding'; fire('finding-search','input');
assert.equal(visible().length, 0);
assert(controls['#finding-count'].textContent.includes('Ничего не найдено'));
fire('finding-clear','click');
assert.equal(visible().length, 20);
controls['#finding-search'].value = `  ${word.toUpperCase()}  `; fire('finding-search','input');
assert(visible().length > 0 && visible().every(node => node.textContent.toLowerCase().includes(word)));
console.log('PASS: archive pagination, source/date filters, search, empty state and reset');
