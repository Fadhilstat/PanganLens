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
    document.body.classList.add("dashboard-preview");
  }
}

function render() {
  const data = state.data;
  const readiness = PanganLensMetrics.snapshotReadiness(data);
  const national = readiness === "ready"
    ? data.national_prices.filter(PanganLensMetrics.isDisplayableNational) : [];
  const provinces = readiness === "ready" ? data.province_prices : [];
  const dashboardAvailable = PanganLensMetrics.hasDashboardContent(data);
  document.body.classList.toggle("dashboard-preview", !dashboardAvailable);

  hideNotice();
  if (readiness === "invalid" || readiness === "blocked") {
    setFreshness("Tidak dapat diverifikasi", null, "warning");
    showNotice("Snapshot harga ditahan karena versi, status publikasi, atau tanggal observasinya tidak valid. Angka yang belum disetujui tidak ditampilkan.");
  } else if (readiness === "ready" && !dashboardAvailable) {
    setFreshness("Harga belum tersedia", data.publish_state.active_observation_date, "warning");
    showNotice("Snapshot telah disetujui, tetapi belum berisi harga nasional valid yang bisa dibandingkan. Coba kalkulator dengan angkamu sendiri.");
  } else {
    renderPublishState(readiness === "ready" ? data.publish_state : null);
    if (!national.length) {
      showNotice("Data produksi belum dipublikasikan. Gunakan kalkulator dengan angkamu sendiri; data PIHPS tidak direka.");
    }
  }

  const commodities = [...new Map(national.map(row => [PanganLensMetrics.commodityKey(row.commodity_id), row.commodity_name])).entries()];
  document.getElementById("commodity-count").textContent = commodities.length ? String(commodities.length) : "-";
  document.getElementById("province-count").textContent = national.length && provinces.length ? String(new Set(provinces.map(row => row.province_id)).size) : "-";
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
  const { rise, fall } = PanganLensMetrics.selectMovers(rows);
  for (const [valueId, detailId, record, absent] of [
    ["top-rise", "top-rise-detail", rise, "Tidak ada kenaikan valid"],
    ["top-fall", "top-fall-detail", fall, "Tidak ada penurunan valid"]
  ]) {
    if (record) {
      setMover(valueId, detailId, record);
    } else {
      document.getElementById(valueId).textContent = "-";
      document.getElementById(detailId).textContent = rows.length ? absent : "Belum tersedia";
    }
  }
}

function setMover(valueId, detailId, row) {
  document.getElementById(valueId).textContent = percent.format(Number(row.daily_change_pct));
  document.getElementById(detailId).textContent = `${row.commodity_name} · ${formatPrice(row.price_idr)}`;
}

function renderCommoditySelect(commodities) {
  const select = document.getElementById("commodity-select");
  select.innerHTML = "";
  if (!commodities.length) {
    state.selectedCommodity = null;
    clearCommodityDetail();
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
  if (!commodities.some(([id]) => id === state.selectedCommodity)) state.selectedCommodity = commodities[0][0];
  select.value = state.selectedCommodity;
  select.onchange = event => {
    state.selectedCommodity = event.target.value;
    renderCommodityDetail();
  };
  renderCommodityDetail();
}

function clearCommodityDetail() {
  document.getElementById("latest-price").textContent = "-";
  document.getElementById("latest-price-meta").textContent = "Pilih komoditas untuk melihat harga.";
  document.getElementById("daily-change").textContent = "-";
  document.getElementById("daily-change").style.color = "var(--text)";
  document.getElementById("trend-chart").innerHTML = "";
  document.getElementById("trend-empty").classList.remove("hidden");
  document.getElementById("region-list").innerHTML = "";
  document.getElementById("region-empty").classList.remove("hidden");
}

function renderCommodityDetail() {
  const national = state.data.national_prices.filter(row =>
    PanganLensMetrics.commodityKey(row.commodity_id) === state.selectedCommodity &&
    PanganLensMetrics.isDisplayableNational(row));
  const provinces = state.data.province_prices.filter(row =>
    PanganLensMetrics.commodityKey(row.commodity_id) === state.selectedCommodity);
  const row = national[0];
  if (!row) return;

  document.getElementById("latest-price").textContent = PanganLensMetrics.isValidPrice(row.price_idr) ? formatPrice(row.price_idr) : "-";
  document.getElementById("latest-price-meta").textContent = `${row.commodity_name} · ${row.channel_name} · per ${row.unit_symbol}`;
  const changeElement = document.getElementById("daily-change");
  if (PanganLensMetrics.isValidPrice(row.price_idr) && PanganLensMetrics.finiteNumber(row.daily_change_pct) !== null) {
    const change = Number(row.daily_change_pct);
    changeElement.textContent = percent.format(change);
    changeElement.style.color = change > 0 ? "var(--red)" : change < 0 ? "var(--green)" : "var(--text)";
  } else {
    changeElement.textContent = "Belum ada pembanding";
    changeElement.style.color = "var(--text)";
  }
  renderTrend(row);
  renderRegions(provinces);
}

function renderTrend(row) {
  const svg = document.getElementById("trend-chart");
  const empty = document.getElementById("trend-empty");
  svg.innerHTML = "";
  const previous = PanganLensMetrics.isValidPrice(row.previous_price_idr) ? Number(row.previous_price_idr) : null;
  const current = PanganLensMetrics.isValidPrice(row.price_idr) ? Number(row.price_idr) : null;
  if (previous === null || current === null) {
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
  line.setAttribute("stroke", "#4b6f8d");
  line.setAttribute("stroke-width", "4");
  line.setAttribute("stroke-linecap", "round");
  svg.appendChild(line);
  points.forEach((point, index) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point.x);
    circle.setAttribute("cy", point.y);
    circle.setAttribute("r", "7");
    circle.setAttribute("fill", "#4b6f8d");
    svg.appendChild(circle);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", point.x);
    text.setAttribute("y", point.y - 18);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "14");
    text.setAttribute("fill", "#202522");
    text.textContent = formatPrice(point.value);
    svg.appendChild(text);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", point.x);
    label.setAttribute("y", "248");
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("font-size", "12");
    label.setAttribute("fill", "#6b716d");
    label.textContent = index === 0 ? "Sebelumnya" : "Terbaru";
    svg.appendChild(label);
  });
}

function renderRegions(rows) {
  const list = document.getElementById("region-list");
  const empty = document.getElementById("region-empty");
  list.innerHTML = "";
  const sorted = PanganLensMetrics.selectRegions(rows);
  if (!sorted.length) {
    empty.textContent = rows.length
      ? "Perbandingan provinsi belum tersedia: nilai harga atau selisih tidak valid."
      : "Data wilayah akan muncul setelah snapshot produksi tersedia.";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  const maxGap = Math.max(...sorted.map(row => Math.abs(Number(row.price_gap_vs_province_average_pct))), 0.01);
  for (const row of sorted) {
    const item = document.createElement("div");
    const gap = Number(row.price_gap_vs_province_average_pct);
    const directionClass = gap > 0 ? "above" : gap < 0 ? "below" : "same";
    const directionLabel = gap > 0 ? "di atas rata-rata" : gap < 0 ? "di bawah rata-rata" : "setara rata-rata";
    item.className = `region-row ${directionClass}`;
    item.innerHTML = `<div class="region-name"></div><div class="region-bar"><span></span></div><div class="region-value"></div>`;
    item.querySelector(".region-name").textContent = row.province_name;
    item.querySelector(".region-bar span").style.width = `${Math.min(100, Math.abs(gap) / maxGap * 100)}%`;
    const value = item.querySelector(".region-value");
    value.textContent = `${formatPrice(row.price_idr)} · ${percent.format(gap)}`;
    const note = document.createElement("small");
    note.textContent = directionLabel;
    value.appendChild(note);
    list.appendChild(item);
  }
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isFinite(number) ? rupiah.format(number) : "-";
}

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function hideNotice() {
  const el = document.getElementById("data-notice");
  el.textContent = "";
  el.classList.add("hidden");
}

function showNotice(message) {
  const el = document.getElementById("data-notice");
  el.textContent = message;
  el.classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", loadDashboard);
