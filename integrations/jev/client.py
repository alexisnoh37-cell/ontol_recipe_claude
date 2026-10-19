"""Jev HTTP 클라이언트(라벨링·재정렬 공용).

인증키는 환경변수 TYPESAFE_API_KEY(.env)에서 읽는다(D6의 JEV_API_KEY도 받는다). 키는 출력·로그·예외 메시지에
넣지 않는다. 429·529는 남은 시간 안에서 한 번 더 시도한다.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Mapping
from typing import Any

import httpx

BASE_URL = "https://api.typesafe.ai"
ENDPOINT = "/v1/systemone"
KEY_VARS = ("TYPESAFE_API_KEY", "JEV_API_KEY")
RETRY_STATUS = (429, 529)


class JevError(Exception):
    """호출 실패(네트워크, 시간 초과, 4xx·5xx, 응답 형식). 메시지에 인증키를 넣지 않는다."""


def api_key_from_env() -> str | None:
    from storage.settings import load_dotenv

    load_dotenv()
    for var in KEY_VARS:
        value = os.environ.get(var, "").strip()
        if value:
            return value
    return None


class JevClient:
    def __init__(self, api_key: str, *, model: str, base_url: str = BASE_URL,
                 transport: httpx.BaseTransport | None = None):
        if not api_key:
            raise ValueError("Jev 인증키가 비었습니다")
        self.model = model
        # 사용량(평가·비용 확인용). 걸러내기는 병렬로 부르므로 잠금으로 더한다
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self._usage_lock = threading.Lock()
        self._client = httpx.Client(base_url=base_url, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}"})

    def __repr__(self) -> str:  # 키가 repr로 새지 않게
        return f"JevClient(model={self.model!r})"

    def close(self) -> None:
        self._client.close()

    def system_one(self, state: Any, questions: Mapping[str, Mapping[str, Any]], *,
                   timeout_s: float) -> dict[str, dict[str, Any]]:
        """질문 key → 답(dict). timeout_s는 재시도를 포함한 전체 시간 한도."""
        body = {"model": self.model, "state": state, "questions": dict(questions)}
        deadline = time.monotonic() + timeout_s
        for attempt in range(2):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise JevError("시간 초과")
            try:
                resp = self._client.post(ENDPOINT, json=body, timeout=remaining)
            except httpx.TimeoutException:
                raise JevError("시간 초과") from None
            except httpx.HTTPError as exc:
                raise JevError(f"네트워크 오류: {type(exc).__name__}") from None
            if resp.status_code in RETRY_STATUS and attempt == 0:
                time.sleep(min(0.3, max(0.0, deadline - time.monotonic())))
                continue
            if resp.status_code != 200:
                raise JevError(f"HTTP {resp.status_code}: {_error_detail(resp)}")
            try:
                data = resp.json()
                answers = data["answers"]
            except (ValueError, KeyError, TypeError):
                raise JevError("응답 형식 오류(answers 없음)") from None
            usage = data.get("usage") if isinstance(data, dict) else None
            with self._usage_lock:
                self.calls += 1
                if isinstance(usage, dict):
                    self.input_tokens += int(usage.get("input_tokens") or 0)
                    self.output_tokens += int(usage.get("output_tokens") or 0)
            if not isinstance(answers, dict):
                raise JevError("응답 형식 오류(answers가 객체가 아님)")
            return answers
        raise JevError("재시도 후에도 실패")


def _error_detail(resp: httpx.Response) -> str:
    try:
        text = resp.text
    except Exception:  # noqa: BLE001
        return ""
    return text[:200].replace("\n", " ")
