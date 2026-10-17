"""살림팝 데이터셋(data/sallimpop_recipe_dataset/)을 레시피 시드 형식(data/recipes/README.md)으로 변환한다.

    uv run python scripts/convert_sallimpop.py

원본 YAML은 읽기만 한다. 결과는 data/recipes/<id>.yaml(draft)과
data/sallimpop_recipe_dataset/CONVERSION.md(원본과 달라진 점)이다. knowledge/를 고친 뒤 다시 실행하면 매핑이 갱신된다.
변환 규칙은 kb/youtube_seed.py(자취요리신과 공용, docs/decisions.md D3 예외를 살림팝에 적용, int-2 사람 승인 2026-10-16).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb.youtube_seed import YoutubeDataset, run  # noqa: E402

DATASET = YoutubeDataset(
    name="sallimpop",
    label="살림팝",
    script="scripts/convert_sallimpop.py",
    # 원본 cuisine '기타'(vocab에 없음) → 임시 지정(자취요리신의 불닭·로제 요리와 같은 기준). 검수 필요
    cuisine_overrides={
        "buldalggyerandubutang_tzkjhp": "한식",  # 불닭계란두부탕
        "rojeddeogboggi_6zduy7": "한식",  # 로제떡볶이
    },
)

if __name__ == "__main__":
    sys.exit(run(DATASET, ROOT))
