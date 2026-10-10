const { test } = require('node:test');
const assert = require('node:assert/strict');
const { finiteNumber, isValidPrice, selectMovers, selectRegions } = require('../website/dashboard_metrics.js');

const national = (commodity_name, daily_change_pct, price_idr = '20000') =>
  ({ commodity_name, daily_change_pct, price_idr });
const province = (province_name, price_gap_vs_province_average_pct, price_idr = '20000') =>
  ({ province_name, price_gap_vs_province_average_pct, price_idr });

test('accepts exact numeric strings but refuses null, blank and nonfinite values', () => {
  assert.equal(finiteNumber('12000.25000'), 12000.25);
  assert.equal(finiteNumber(' -0.025 '), -0.025);
  for (const value of [null, undefined, '', '  ', 'NaN', 'Infinity', '12abc', {}, true]) {
    assert.equal(finiteNumber(value), null);
  }
});

test('prices must be strictly positive', () => {
  assert.equal(isValidPrice('1234.0'), true);
  for (const value of [null, 0, '0', '-1', '', 'NaN']) assert.equal(isValidPrice(value), false);
});

test('rise and fall are selected by sign, not just sorted extremes', () => {
  const rows = [national('Cabai', '-0.12'), national('Beras', '0.02'),
    national('Bawang', '0.18'), national('Telur', '-0.04')];
  assert.equal(selectMovers(rows).rise.commodity_name, 'Bawang');
  assert.equal(selectMovers(rows).fall.commodity_name, 'Cabai');
});

test('all-negative data has no increase and all-positive data has no decrease', () => {
  assert.equal(selectMovers([national('A', '-0.01'), national('B', '-0.04')]).rise, null);
  assert.equal(selectMovers([national('A', '0.01'), national('B', '0.04')]).fall, null);
});

test('flat, malformed, missing-change, and nonpositive-price records cannot become movers', () => {
  const rows = [national('Flat', '0'), national('Missing', null),
    national('No price', '0.25', null), national('Bad price', '-0.5', '-3'),
    national('Bad change', 'NaN'), national('', '2')];
  assert.deepEqual(selectMovers(rows), { rise: null, fall: null });
  assert.deepEqual(selectMovers(null), { rise: null, fall: null });
});

test('region ranking ignores missing gap rather than labeling it equal to average', () => {
  const rows = [province('Jakarta', null), province('Banten', '0.13'),
    province('Lampung', '-0.11'), province('Jabar', ''), province('Bali', '0')];
  assert.deepEqual(selectRegions(rows).map(x => x.province_name), ['Banten', 'Lampung', 'Bali']);
});

test('region ranking excludes missing or invalid prices and returns bounded list', () => {
  const rows = [province('Satu', '0.5', '-12'), province('Dua', '-0.2', '0'),
    province('Tiga', '0.3'), province('Empat', '0.01')];
  assert.deepEqual(selectRegions(rows, 1).map(x => x.province_name), ['Tiga']);
  assert.equal(selectRegions(rows, -1).length, 0);
  assert.deepEqual(selectRegions(null), []);
});

test('ties use stable alphabetical province order', () => {
  const rows = [province('Banten', '-0.2'), province('Aceh', '0.2')];
  assert.deepEqual(selectRegions(rows).map(x => x.province_name), ['Aceh', 'Banten']);
});

test('does not mutate dashboard rows', () => {
  const rows = [province('A', '-0.4'), province('B', '0.1')];
  selectRegions(rows);
  assert.deepEqual(rows.map(x => x.province_name), ['A', 'B']);
});
