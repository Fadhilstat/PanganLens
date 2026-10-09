const { test } = require('node:test');
const assert = require('node:assert/strict');
const { positivePrice, relativeChange } = require('../website/price_playground.js');

test('accepts positive numeric strings and amounts', () => {
  assert.equal(positivePrice(' 23000.5 '), 23000.5);
  assert.equal(positivePrice(10000), 10000);
});

test('rejects missing, zero, negative, malformed, and non-finite input', () => {
  for (const value of ['', ' ', 0, '-3', '-1', 'Rp 10.000', '12e2', 'NaN',
    null, undefined, Infinity, NaN, {}, Number.MAX_SAFE_INTEGER + 1]) {
    assert.equal(positivePrice(value), null);
  }
});

test('calculates a positive price change using the previous price as denominator', () => {
  assert.equal(relativeChange(10000, 11000), 0.1);
});

test('calculates a negative price change', () => {
  assert.equal(relativeChange(20000, 18000), -0.1);
});

test('calculates a zero change', () => {
  assert.equal(relativeChange(20000, 20000), 0);
});

test('calculates a regional gap using the provincial average as denominator', () => {
  assert.equal(relativeChange(25000, 30000), 0.2);
});

test('never divides by zero or accepts invalid input', () => {
  assert.equal(relativeChange(0, 30000), null);
  assert.equal(relativeChange('', '30000'), null);
  assert.equal(relativeChange('20000', 'not a price'), null);
});
