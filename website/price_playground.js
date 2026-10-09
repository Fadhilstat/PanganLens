(function (environment) {
  "use strict";

  // This exercise processes user-entered values only. It never reads or invents PIHPS data.
  function positivePrice(value) {
    if (typeof value !== "number" && typeof value !== "string") return null;
    if (typeof value === "string" && !/^\s*\d+(?:\.\d+)?\s*$/.test(value)) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 && parsed <= Number.MAX_SAFE_INTEGER ? parsed : null;
  }

  function relativeChange(reference, observed) {
    const base = positivePrice(reference);
    const current = positivePrice(observed);
    if (base === null || current === null) return null;
    const result = (current - base) / base;
    return Number.isFinite(result) ? result : null;
  }

  function setupCalculator() {
    const form = document.getElementById("price-calculator");
    if (!form) return;
    const changeOutput = document.getElementById("calc-movement");
    const gapOutput = document.getElementById("calc-region");
    const statusOutput = document.getElementById("calc-message");
    const currency = new Intl.NumberFormat("id-ID", {
      style: "currency", currency: "IDR", maximumFractionDigits: 0, signDisplay: "exceptZero"
    });
    const percentage = new Intl.NumberFormat("id-ID", {
      style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero"
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const previous = positivePrice(form.elements.namedItem("previous").value);
      const current = positivePrice(form.elements.namedItem("current").value);
      const provincialAverage = positivePrice(form.elements.namedItem("average").value);
      const region = positivePrice(form.elements.namedItem("region").value);
      const movement = relativeChange(previous, current);
      const gap = relativeChange(provincialAverage, region);
      if (movement === null || gap === null) {
        changeOutput.textContent = "Belum dihitung";
        gapOutput.textContent = "Belum dihitung";
        statusOutput.textContent = "Isi keempat harga dengan angka positif. Nol, angka negatif, dan input kosong tidak bisa dibandingkan.";
        return;
      }
      changeOutput.textContent = percentage.format(movement) + " (" + currency.format(current - previous) + ")";
      gapOutput.textContent = percentage.format(gap) + " (" + currency.format(region - provincialAverage) + ")";
      statusOutput.textContent = "Hasil dihitung dari inputmu di browser. Angka ini bukan data PIHPS atau harga terkini.";
    });

    form.addEventListener("reset", function () {
      changeOutput.textContent = "Belum dihitung";
      gapOutput.textContent = "Belum dihitung";
      statusOutput.textContent = "Masukkan nilaimu untuk mencoba logika perhitungan.";
    });
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", setupCalculator);
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { positivePrice, relativeChange };
  }
})(this);
