(function (root) {
  "use strict";

  // Work only with numbers from the reviewed dashboard snapshot.
  // BigQuery NUMERIC values may be JSON strings; never coerce null or "" to zero.
  function finiteNumber(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(trimmed)) return null;
    const number = Number(trimmed);
    return Number.isFinite(number) ? number : null;
  }

  function isValidPrice(value) {
    const price = finiteNumber(value);
    return price !== null && price > 0;
  }

  // Commodity identifiers may arrive as JSON integers or strings.
  // Normalize both to one DOM select key without guessing missing IDs.
  function commodityKey(value) {
    if (typeof value === "number") return Number.isSafeInteger(value) ? String(value) : null;
    if (typeof value === "string") return value.trim() || null;
    return null;
  }

  function isDisplayableNational(row) {
    return Boolean(row && commodityKey(row.commodity_id) !== null &&
      typeof row.commodity_name === "string" && row.commodity_name.trim() &&
      isValidPrice(row.price_idr));
  }

  function selectMovers(rows) {
    let rise = null;
    let fall = null;
    if (!Array.isArray(rows)) return { rise, fall };
    for (const row of rows) {
      if (!row || typeof row.commodity_name !== "string" ||
          !row.commodity_name.trim() || !isValidPrice(row.price_idr)) continue;
      const change = finiteNumber(row.daily_change_pct);
      if (change === null) continue;
      if (change > 0 && (!rise || change > finiteNumber(rise.daily_change_pct))) rise = row;
      if (change < 0 && (!fall || change < finiteNumber(fall.daily_change_pct))) fall = row;
    }
    return { rise, fall };
  }

  function selectRegions(rows, maxRows = 10) {
    if (!Array.isArray(rows)) return [];
    const count = Number.isInteger(maxRows) ? Math.max(0, Math.min(maxRows, 100)) : 10;
    return rows.filter((row) => row && typeof row.province_name === "string" &&
      row.province_name.trim() && isValidPrice(row.price_idr) &&
      finiteNumber(row.price_gap_vs_province_average_pct) !== null)
      .sort((a, b) =>
        Math.abs(finiteNumber(b.price_gap_vs_province_average_pct)) -
        Math.abs(finiteNumber(a.price_gap_vs_province_average_pct)) ||
        a.province_name.localeCompare(b.province_name, "id"))
      .slice(0, count);
  }


  function validIsoDay(day) {
    if (typeof day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
    const date = new Date(day + "T00:00:00Z");
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === day;
  }

  function snapshotReadiness(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload) ||
        payload.schema_version !== 1 ||
        !Array.isArray(payload.national_prices) ||
        !Array.isArray(payload.province_prices)) return "invalid";

    const containsPrices = payload.national_prices.length > 0 || payload.province_prices.length > 0;
    const published = payload.publish_state;
    if (published == null) return containsPrices ? "blocked" : "empty";
    const valid = typeof published === "object" && !Array.isArray(published) &&
      published.active_run_status === "SUCCESS" &&
      validIsoDay(published.active_observation_date) &&
      ["Terkini", "Perlu diperiksa", "Data lama"].includes(published.freshness_label);
    return valid ? "ready" : "blocked";
  }
  function hasDashboardContent(payload) {
    return snapshotReadiness(payload) === "ready" &&
      payload.national_prices.some(isDisplayableNational);
  }

  const metrics = { finiteNumber, isValidPrice, commodityKey, isDisplayableNational,
    selectMovers, selectRegions, snapshotReadiness, hasDashboardContent };
  root.PanganLensMetrics = metrics;
  if (typeof module !== "undefined" && module.exports) module.exports = metrics;
})(typeof globalThis !== "undefined" ? globalThis : this);
