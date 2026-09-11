'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function run(total) {
  const cards = Array.from({length: total}, () => ({hidden: false}));
  const more = {hidden: true, disabled: false, textContent: '', listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }};
  const list = {dataset: {initial: '5'}, querySelectorAll() { return cards; }};
  const document = {querySelector(selector) { return selector === '[data-release-list]' ? list : selector === '[data-show-more]' ? more : null; }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'assets/releases.js'), 'utf8'), {document});
  return {cards,more,click() { more.listeners.click(); }};
}
let state=run(25);
assert.equal(state.cards.filter(card => !card.hidden).length,5);
assert.equal(state.more.hidden,false);
state.click();assert.equal(state.cards.filter(card => !card.hidden).length,15);
state.click();assert.equal(state.cards.filter(card => !card.hidden).length,25);
assert.equal(state.more.hidden,true);assert.equal(state.more.disabled,true);
state=run(4);assert.equal(state.cards.filter(card => !card.hidden).length,4);assert.equal(state.more.hidden,true);
console.log('PASS: releases 5 → 15 → 25, final button hidden, short list intact');
