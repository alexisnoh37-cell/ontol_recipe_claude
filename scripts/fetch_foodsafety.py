"""식품안전나라 조리식품 레시피 DB(Open API COOKRCP01) 원본을 내려받는다 (docs/plan.md 5-3-1, D3 보완 2).

    uv run python scripts/fetch_foodsafety.py            # → data/external/foodsafety/raw/COOKRCP01.json

인증키는 .env의 FOODSAFETY_API_KEY(식품안전나라에서 발급). 한 번에 최대 1000건씩 요청한다
(API 제한: 1000건/요청, 시간당 100회). 원본은 gitignore 대상이다(개인용 범위, 재배포하지 않음).
인증키는 출력이나 저장 파일에 남기지 않는다.
종료 코드: 0 성공, 1 API 오류, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb.foodsafety import SERVICE_ID, FoodsafetyApiError, parse_page  # noqa: E402
from storage.settings import load_dotenv  # noqa: E402

BASE_URL = "http://openapi.foodsafetykorea.go.kr/api"
PAGE_SIZE = 1000
DEFAULT_OUT = ROOT / "data" / "external" / "foodsafety" / "raw" / f"{SERVICE_ID}.json"


def fetch_page(key: str, start: int, end: int, timeout: float) -> object:
    url = f"{BASE_URL}/{key}/{SERVICE_ID}/json/{start}/{end}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - 고정된 공공 API 주소
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        # URL에 인증키가 들어 있으므로 예외 메시지에 URL을 싣지 않는다
        raise FoodsafetyApiError(f"{start}~{end}번 요청 실패: {type(exc).__name__}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    load_dotenv()
    key = os.environ.get("FOODSAFETY_API_KEY", "").strip()
    if not key:
        print(".env에 FOODSAFETY_API_KEY가 없습니다(식품안전나라에서 발급한 인증키).", file=sys.stderr)
        return 2

    rows: list[dict] = []
    total: int | None = None
    start = 1
    try:
        while total is None or start <= total:
            end = start + PAGE_SIZE - 1
            page_total, page_rows = parse_page(fetch_page(key, start, end, args.timeout))
            total = page_total
            rows += page_rows
            print(f"{start}~{end}: {len(page_rows)}건 (전체 {total}건)")
            if not page_rows:
                break
            start = end + 1
    except FoodsafetyApiError as exc:
        print(f"API 오류: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "service": SERVICE_ID,
        "source": "식품의약품안전처 식품안전나라 조리식품의 레시피 DB(Open API COOKRCP01)",
        "fetched_on": date.today().isoformat(),
        "total_count": total,
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {args.out} ({len(rows)}건)")
    if total is not None and len(rows) != total:
        print(f"경고: 받은 건수 {len(rows)}가 전체 {total}과 다릅니다.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
