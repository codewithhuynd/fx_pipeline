import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import collector_ecb  # noqa: E402
import collector_vcb  # noqa: E402
import config  # noqa: E402
import pipeline  # noqa: E402


def test_vcb_only_skips_ecb_and_persists_report(monkeypatch, tmp_path):
    fixture = config.FIXTURE_DIR / "vcb_sample.xml"
    monkeypatch.setattr(collector_vcb, "collect", lambda offline=False: collector_vcb.parse(
        fixture.read_text(encoding="utf-8")
    ))

    def unexpected_ecb_call(days):
        raise AssertionError("ECB must not be called for a VCB-only run")

    monkeypatch.setattr(collector_ecb, "collect", unexpected_ecb_call)
    monkeypatch.setattr(pipeline.storage, "merge_and_save", lambda records: records)
    monkeypatch.setattr(config, "REPORT_PATH", tmp_path / "cleaning_report.json")

    result = pipeline.run(vcb_only=True)

    assert result is not None
    records, reports = result
    assert records
    assert {record.source for record in records} == {"vcb"}
    assert [report.source for report in reports] == ["vcb"]
    assert config.REPORT_PATH.exists()
