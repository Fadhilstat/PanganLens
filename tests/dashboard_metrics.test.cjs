const { test } = require('node:test');
const assert = require('node:assert/strict');
const { finiteNumber, isValidPrice, selectMovers, selectRegions, commodityKey,
  isDisplayableNational, hasDashboardContent } = require('../website/dashboard_metrics.js');

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


test('empty snapshot is accepted only when it contains no published prices', () => {
  const { snapshotReadiness } = require('../website/dashboard_metrics.js');
  assert.equal(snapshotReadiness({
    schema_version: 1, generated_at: null, publish_state: null,
    national_prices: [], province_prices: []
  }), 'empty');
  assert.equal(snapshotReadiness({
    schema_version: 1, publish_state: null,
    national_prices: [{ price_idr: '25000' }], province_prices: []
  }), 'blocked');
});

test('unsupported, missing or malformed schema cannot be rendered', () => {
  const { snapshotReadiness } = require('../website/dashboard_metrics.js');
  for (const payload of [null, [], 42, {}, {
    schema_version: 2, publish_state: null, national_prices: [], province_prices: []
  }, {
    schema_version: 1, publish_state: null, national_prices: null, province_prices: []
  }]) assert.equal(snapshotReadiness(payload), 'invalid');
});

test('publication state must be a successful run and a valid calendar date', () => {
  const { snapshotReadiness } = require('../website/dashboard_metrics.js');
  const base = {
    schema_version: 1, national_prices: [{ price_idr: '30000' }], province_prices: []
  };
  const good = { active_run_status: 'SUCCESS',
    active_observation_date: '2026-10-09', freshness_label: 'Terkini' };
  assert.equal(snapshotReadiness({ ...base, publish_state: good }), 'ready');
  for (const value of [
    { ...good, active_run_status: 'FAILED' },
    { ...good, active_observation_date: '2026-02-30' },
    { ...good, active_observation_date: null },
    { ...good, freshness_label: 'unspecified' },
    {}
  ]) assert.equal(snapshotReadiness({ ...base, publish_state: value }), 'blocked');
});

test('reviewed stale publication is still displayable with its warning label', () => {
  const { snapshotReadiness } = require('../website/dashboard_metrics.js');
  const data = { schema_version: 1, national_prices: [], province_prices: [],
    publish_state: { active_run_status: 'SUCCESS',
      active_observation_date: '2026-10-08', freshness_label: 'Data lama' } };
  assert.equal(snapshotReadiness(data), 'ready');
});


test('commodity selection matches numeric warehouse IDs and string DOM values', () => {
  assert.equal(commodityKey(12), '12');
  assert.equal(commodityKey('12'), '12');
  assert.equal(commodityKey(' 12 '), '12');
  for (const value of [null, undefined, '', ' ', 12.5, NaN, Infinity, {}]) {
    assert.equal(commodityKey(value), null);
  }
});

test('preview mode stays until a verified, usable national price exists', () => {
  const publication = { active_run_status: 'SUCCESS',
    active_observation_date: '2026-10-09', freshness_label: 'Terkini' };
  const row = { commodity_id: 12, commodity_name: 'Cabai', price_idr: '35000' };
  const payload = { schema_version: 1, publish_state: publication,
    national_prices: [row], province_prices: [] };
  assert.equal(isDisplayableNational(row), true);
  assert.equal(hasDashboardContent(payload), true);
  assert.equal(hasDashboardContent({ ...payload, publish_state: null }), false);
  assert.equal(hasDashboardContent({ ...payload, national_prices: [] }), false);
  assert.equal(hasDashboardContent({ ...payload, national_prices: [],
    province_prices: [{ commodity_id: 12, price_idr: '35000' }] }), false);
  for (const invalid of [{ ...row, price_idr: null }, { ...row, price_idr: 0 },
    { ...row, commodity_id: null }, { ...row, commodity_name: ' ' }]) {
    assert.equal(isDisplayableNational(invalid), false);
    assert.equal(hasDashboardContent({ ...payload, national_prices: [invalid] }), false);
  }
});
