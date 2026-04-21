from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.encar_parser import load_html_from_input, parse_encar_listings


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "encar_search_sample.html"


def test_parse_encar_listings_from_fixture() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")

    df = parse_encar_listings(html)

    assert len(df) == 4
    assert list(df.columns) == ["name", "price_manwon", "mileage_km", "year", "detail_link"]

    first = df.iloc[0]
    assert first["name"] == "기아 K5 2.0 프레스티지"
    assert first["price_manwon"] == 1450
    assert first["mileage_km"] == 58000
    assert first["year"] == 2019
    assert first["detail_link"].startswith("https://www.encar.com/")
    assert "리스" not in " ".join(df["name"].astype(str).tolist())
    assert "BMW M3 세단 컴페티션" in df["name"].tolist()


def test_load_html_from_input_returns_raw_html() -> None:
    html = "<html><body><p>hello</p></body></html>"
    assert load_html_from_input(html) == html


def test_load_html_from_input_reads_local_file(tmp_path: Path) -> None:
    html = "<html><body><div>local file</div></body></html>"
    file_path = tmp_path / "encar_extracted.html"
    file_path.write_text(html, encoding="utf-8")

    assert load_html_from_input(str(file_path)) == html
