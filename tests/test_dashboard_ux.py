from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[1] / "website"


def test_dashboard_has_guided_reading_flow():
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")

    assert "Cara membaca PanganLens" in html
    assert "LANGKAH 1" in html
    assert "LANGKAH 2" in html
    assert "LANGKAH 3" in html
    assert "Ringkasan" in html
    assert "Komoditas" in html
    assert "Wilayah" in html


def test_dashboard_does_not_depend_on_external_frontend_runtime():
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")

    assert "https://" not in html
    assert '<script src="app.js" defer></script>' in html
    assert '<link rel="stylesheet" href="styles.css">' in html


def test_regional_color_semantics_also_have_text_labels():
    javascript = (WEBSITE / "app.js").read_text(encoding="utf-8")
    css = (WEBSITE / "styles.css").read_text(encoding="utf-8")

    assert "di atas rata-rata" in javascript
    assert "di bawah rata-rata" in javascript
    assert "directionLabel" in javascript
    assert "--red:" in css
    assert "--green:" in css
    assert "--blue:" in css


def test_dashboard_keeps_warning_and_empty_states_explicit():
    html = (WEBSITE / "index.html").read_text(encoding="utf-8")
    javascript = (WEBSITE / "app.js").read_text(encoding="utf-8")

    assert 'id="data-notice"' in html
    assert "Data produksi belum dipublikasikan" in javascript
    assert "Data tidak ditampilkan agar tidak menyesatkan" in javascript
