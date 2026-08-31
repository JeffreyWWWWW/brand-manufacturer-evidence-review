import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "brand-manufacturer-evidence-review" / "skills" / "brand-manufacturer-evidence-review"
sys.path.insert(0, str(SKILL_ROOT))

from scripts.tavily_search import TavilyConfigError, main, normalize_response, search
from scripts.validate_evidence_review import _independent_source_hosts


def test_search_without_api_key_returns_disabled_result(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    result = search("CURT manufacturer")

    assert result["enabled"] is False
    assert result["reason"] == "TAVILY_API_KEY_NOT_CONFIGURED"
    assert result["records"] == []


def test_normalize_response_creates_auditable_candidate_records():
    payload = {
        "query": "CURT manufacturer",
        "results": [
            {
                "title": "CURT About",
                "url": "https://www.curtmfg.com/about-curt",
                "content": "CURT is a Lippert brand.",
                "score": 0.91,
            }
        ],
    }

    records = normalize_response(payload, query_id="TAV-001", accessed_at="2026-08-31T10:00:00+08:00")

    assert records == [
        {
            "检索编号": "TAV-001-001",
            "检索词": "CURT manufacturer",
            "入口URL": "https://www.curtmfg.com/about-curt",
            "访问时间": "2026-08-31T10:00:00+08:00",
            "访问结果": "Tavily候选结果",
            "提取摘要": "CURT is a Lippert brand.",
            "失败原因": "",
            "候选标题": "CURT About",
            "候选评分": 0.91,
            "来源引擎": "Tavily",
        }
    ]


def test_normalize_response_rejects_malformed_result():
    with pytest.raises(TavilyConfigError, match="TAVILY_RESPONSE_INVALID"):
        normalize_response({"results": [{"title": "missing url"}]}, query_id="TAV-001", accessed_at="2026-08-31T10:00:00+08:00")


def test_independent_source_hosts_deduplicates_same_domain():
    evidence = {
        "EVD-001": {"URL": "https://www.example.com/about"},
        "EVD-002": {"URL": "https://example.com/terms"},
        "EVD-003": {"URL": "https://registry.example.org/record"},
    }

    assert _independent_source_hosts(["EVD-001", "EVD-002", "EVD-003"], evidence) == {"example.com", "registry.example.org"}


def test_cli_without_key_emits_disabled_json(monkeypatch, capsys):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    assert main(["CURT manufacturer"]) == 0
    assert json.loads(capsys.readouterr().out)["reason"] == "TAVILY_API_KEY_NOT_CONFIGURED"


def test_search_uses_unique_batch_id_for_each_api_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"query": "CURT", "results": [{"title": "A", "url": "https://a.example", "content": "x"}]}).encode()

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("scripts.tavily_search.urlopen", lambda *args, **kwargs: FakeResponse())

    first = search("CURT")["records"][0]["检索编号"]
    second = search("CURT")["records"][0]["检索编号"]

    assert first != second


def test_search_requests_twenty_candidates_by_default(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"query": "CURT", "results": []}).encode()

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("scripts.tavily_search.urlopen", fake_urlopen)

    search("CURT")

    assert captured["payload"]["max_results"] == 20


def test_cli_requests_twenty_candidates_by_default(monkeypatch, capsys):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"query": "CURT", "results": []}).encode()

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("scripts.tavily_search.urlopen", fake_urlopen)

    assert main(["CURT"]) == 0
    capsys.readouterr()

    assert captured["payload"]["max_results"] == 20
