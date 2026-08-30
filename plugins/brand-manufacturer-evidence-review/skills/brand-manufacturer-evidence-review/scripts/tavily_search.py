"""Optional Tavily discovery search adapter.

Tavily results are discovery leads only. They must be verified against the
original page or an authoritative registry before becoming EVD evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://api.tavily.com/search"
DEFAULT_TIMEOUT_SECONDS = 20


class TavilyConfigError(ValueError):
    """Raised when Tavily configuration or response shape is invalid."""


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TavilyConfigError(f"TAVILY_RESPONSE_INVALID missing {field}")
    return value.strip()


def normalize_response(
    payload: Mapping[str, Any], *, query_id: str, accessed_at: str
) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("results"), list):
        raise TavilyConfigError("TAVILY_RESPONSE_INVALID results must be a list")
    query = _required_text(payload.get("query"), "query")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(payload["results"], start=1):
        if not isinstance(item, Mapping):
            raise TavilyConfigError("TAVILY_RESPONSE_INVALID result must be an object")
        title = _required_text(item.get("title"), "title")
        url = _required_text(item.get("url"), "url")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise TavilyConfigError("TAVILY_RESPONSE_INVALID url must be absolute http(s)")
        content = _required_text(item.get("content"), "content")
        record: dict[str, Any] = {
            "检索编号": f"{query_id}-{index:03d}",
            "检索词": query,
            "入口URL": url,
            "访问时间": accessed_at,
            "访问结果": "Tavily候选结果",
            "提取摘要": content,
            "失败原因": "",
            "候选标题": title,
            "候选评分": item.get("score"),
            "来源引擎": "Tavily",
        }
        records.append(record)
    return records


def search(
    query: str,
    *,
    max_results: int = 5,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    endpoint: str = DEFAULT_ENDPOINT,
) -> dict[str, Any]:
    """Run optional Tavily discovery search without making it a hard dependency."""
    if not isinstance(query, str) or not query.strip():
        raise TavilyConfigError("TAVILY_QUERY_INVALID query must be non-empty")
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return {"enabled": False, "reason": "TAVILY_API_KEY_NOT_CONFIGURED", "records": []}
    if not isinstance(max_results, int) or not 1 <= max_results <= 20:
        raise TavilyConfigError("TAVILY_CONFIG_INVALID max_results must be between 1 and 20")
    payload = json.dumps(
        {"api_key": api_key, "query": query.strip(), "search_depth": "advanced", "max_results": max_results, "include_answer": False},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    accessed_at = _utc_timestamp()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        records = normalize_response(
            response_payload,
            query_id=f"TAV-{uuid.uuid4().hex[:8].upper()}",
            accessed_at=accessed_at,
        )
        return {"enabled": True, "reason": "", "records": records}
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        return {"enabled": True, "reason": f"TAVILY_REQUEST_FAILED: {error}", "records": []}
    except json.JSONDecodeError as error:
        return {"enabled": True, "reason": f"TAVILY_RESPONSE_INVALID: {error}", "records": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run optional Tavily discovery search.")
    parser.add_argument("query")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args(argv)
    result = search(args.query, max_results=args.max_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
