from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpResult:
    ok: bool
    status: int | None = None
    body: str | None = None
    error: str | None = None


def http_post_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_s: float = 10.0,
) -> HttpResult:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            return HttpResult(ok=True, status=getattr(resp, "status", None), body=body)
    except urllib.error.HTTPError as e:
        try:
            b = e.read().decode("utf-8", errors="replace")
        except Exception:
            b = None
        return HttpResult(ok=False, status=getattr(e, "code", None), body=b, error=str(e))
    except Exception as e:
        return HttpResult(ok=False, error=f"{type(e).__name__}: {e}")

