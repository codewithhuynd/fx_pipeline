import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import collector_vcb  # noqa: E402
import config  # noqa: E402


def _setup(monkeypatch, tmp_path, response):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(collector_vcb, "http_get", lambda url: response)


def test_invalid_response_is_not_saved_as_raw(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, "<html><body>Service Unavailable</body></html>")
    assert collector_vcb.collect() == []
    assert not list((tmp_path / "raw").glob("vcb_*.xml"))


def test_valid_response_is_saved_as_raw(monkeypatch, tmp_path):
    xml = (config.FIXTURE_DIR / "vcb_sample.xml").read_text(encoding="utf-8")
    _setup(monkeypatch, tmp_path, xml)
    assert len(collector_vcb.collect()) == 8
    assert len(list((tmp_path / "raw").glob("vcb_*.xml"))) == 1
