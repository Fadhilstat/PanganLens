const state = { data: null, selectedCommodity: null };

const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat("id-ID", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" });
const dateFormat = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" });

async function loadDashboard() {
  try {
    const response = await fetch("data/dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    render();
  } catch (error) {
    showNotice("Snapshot dashboard belum dapat dimuat. Data tidak ditampilkan agar tidak menyesatkan.");
    setFreshness("Tidak tersedia", null, "warning");
  }
}

function render() {
  const data = state.data;
  const national = Array.isArray(data.national_prices) ? data.national_prices : [];
  const provinces = Array.isArray(data.province_prices) ? data.province_prices : [];
  renderPublishState(data.publish_state);

  if (!national.length) {
    showNotice("Data produksi belum dipublikasikan ke website. Struktur dashboard sudah siap dan akan terisi setelah snapshot BigQuery pertama lolos quality gate.");
  }

  const commodities = [...new Map(national.map(row => [row.commodity_id, row.commodity_name])).entries()];
  document.getElementById("commodity-count").textContent = String(commodities.length);
  document.getElementById("province-count").textContent = String(new Set(provinces.map(row => row.province_id)).size);
  renderMovers(national);
  renderCommoditySelect(commodities);
}

function renderPublishState(publishState) {
  if (!publishState) {
    setFreshness("Belum dipublikasikan", null, "warning");
    return;
  }
  const label = publishState.freshness_label || "Status tidak tersedia";
  const tone = label === "Terkini" ? "healthy" : "warning";
  setFreshness(label, publishState.active_observation_date, tone);
}

function setFreshness(label, observationDate, tone) {
  document.getElementById("freshness-label").textContent = label;
  document.getElementById("observation-date").textContent = observationDate ? `Data ${dateFormat.format(new Date(`${observationDate}T00:00:00+07:00`))}` : "Tanggal data belum tersedia";
  document.getElementById("status-dot").style.background = tone === "healthy" ? "var(--green)" : "var(--amber)";
}

function renderMovers(rows) {
  const comparable = rows.filter(row => finite(row.daily_change_pct));
  if (!comparable.length) return;
  comparable.sort((a, b) => Number(b.daily_change_pct) - Number(a.daily_change_pct));
  setMover("top-rise", "top-rise-detail", comparable[0]);
  setMover("top-fall", "top-fall-detail", comparable[comparable.length - 1]);
}

function setMover(valueId, detailId, row) {
  document.getElementById(valueId).textContent = percent.format(Number(row.daily_change_pct));
  document.getElementById(detailId).textContent = `${row.commodity_name} · ${formatPrice(row.price_idr)}`;
}

function renderCommoditySelect(commodities) {
  const select = document.getElementById("commodity-select");
  select.innerHTML = "";
  if (!commodities.length) {
    const option = document.createElement("option");
    option.textContent = "Belum ada data";
    select.appendChild(option);
    select.disabled = true;
    return;
  }
  for (const [id, name] of commodities) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = name;
    select.appendChild(option);
  }
  select.disabled = false;
  state.selectedCommodity = state.selectedCommodity || commodities[0][0];
  select.value = state.selectedCommodity;
  select.addEventListener("change", event => {
    state.selectedCommodity = event.target.value;
    renderCommodityDetail();
  });
  renderCommodityDetail();
}

function renderCommodityDetail() {
  const national = state.data.national_prices.filter(row => row.commodity_id === state.selectedCommodity);
  const provinces = state.data.province_prices.filter(row => row.commodity_id === state.selectedCommodity);
  const row = national[0];
  if (!row) return;

  document.getElementById("latest-price").textContent = formatPrice(row.price_idr);
  document.getElementById("latest-price-meta").textContent = `${row.commodity_name} · ${row.channel_name} · per ${row.unit_symbol}`;
  document.getElementById("daily-change").textContent = finite(row.daily_change_pct) ? percent.format(Number(row.daily_change_pct)) : "Belum ada pembanding";
  renderTrend(row);
  renderRegions(provinces);
}

function renderTrend(row) {
  const svg = document.getElementById("trend-chart");
  const empty = document.getElementById("trend-empty");
  svg.innerHTML = "";
  const previous = finite(row.previous_price_idr) ? Number(row.previous_price_idr) : null;
  const current = Number(row.price_idr);
  if (previous === null || !Number.isFinite(current)) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  const values = [previous, current];
  const min = Math.min(...values) * 0.98;
  const max = Math.max(...values) * 1.02;
  const span = Math.max(max - min, 1);
  const points = values.map((value, index) => {
    const x = 120 + index * 560;
    const y = 215 - ((value - min) / span) * 170;
    return { x, y, value };
  });
  const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
  line.setAttribute("d", `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`);
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "#356859");
  line.setAttribute("stroke-width", "4");
  line.setAttribute("stroke-linecap", "round");
  svg.appendChild(line);
  points.forEach((point, index) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point.x); circle.setAttribute("cy", point.y); circle.setAttribute("r", "7"); circle.setAttribute("fill", "#356859");
    svg.appendChild(circle);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", point.x); text.setAttribute("y", point.y - 18); text.setAttribute("text-anchor", "middle"); text.setAttribute("font-size", "14"); text.setAttribute("fill", "#202522");
    text.textContent = formatPrice(point.value);
    svg.appendChild(text);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", point.x); label.setAttribute("y", "248"); label.setAttribute("text-anchor", "middle"); label.setAttribute("font-size", "12"); label.setAttribute("fill", "#6b716d");
    label.textContent = index === 0 ? "Observasi sebelumnya" : "Observasi terbaru";
    svg.appendChild(label);
  });
}

function renderRegions(rows) {
  const list = document.getElementById("region-list");
  const empty = document.getElementById("region-empty");
  list.innerHTML = "";
  if (!rows.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  const sorted = [...rows].sort((a, b) => Math.abs(Number(b.price_gap_vs_province_average_pct || 0)) - Math.abs(Number(a.price_gap_vs_province_average_pct || 0))).slice(0, 10);
  const maxGap = Math.max(...sorted.map(row => Math.abs(Number(row.price_gap_vs_province_average_pct || 0))), 0.01);
  for (const row of sorted) {
    const item = document.createElement("div");
    item.className = "region-row";
    const gap = Number(row.price_gap_vs_province_average_pct || 0);
    item.innerHTML = `<div class="region-name"></div><div class="region-bar"><span></span></div><div class="region-value"></div>`;
    item.querySelector(".region-name").textContent = row.province_name;
    item.querySelector(".region-bar span").style.width = `${Math.min(100, Math.abs(gap) / maxGap * 100)}%`;
    item.querySelector(".region-value").textContent = `${formatPrice(row.price_idr)} · ${percent.format(gap)}`;
    list.appendChild(item);
  }
}

function formatPrice(value) {
  const number = Number(value);
  return Number.isFinite(number) ? rupiah.format(number) : "-";
}

function finite(value) { return value !== null && value !== undefined && Number.isFinite(Number(value)); }
function showNotice(message) { const el = document.getElementById("data-notice"); el.textContent = message; el.classList.remove("hidden"); }

document.addEventListener("DOMContentLoaded", loadDashboard);
