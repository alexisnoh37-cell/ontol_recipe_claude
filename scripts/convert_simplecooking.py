"""자취요리신 데이터셋(data/simplecooking_recipe_dataset/)을 레시피 시드 형식(data/recipes/README.md)으로 변환한다.

    uv run python scripts/convert_simplecooking.py

원본 YAML은 읽기만 한다. 결과는 data/recipes/<id>.yaml(draft)과
data/simplecooking_recipe_dataset/CONVERSION.md(원본과 달라진 점)이다. knowledge/를 고친 뒤 다시 실행하면 매핑이 갱신된다.
변환 규칙은 kb/youtube_seed.py(살림팝과 공용, 2026-10-16 사람 결정, docs/decisions.md D3 예외).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb.youtube_seed import YoutubeDataset, run  # noqa: E402

DATASET = YoutubeDataset(
    name="simplecooking",
    label="자취요리신",
    script="scripts/convert_simplecooking.py",
    # 원본 id가 숫자로 시작해 시드 id 형식(kb/schema.py ID_PATTERN)에 맞지 않는 것. 원본 → 변환본
    id_overrides={
        "5bun_gimcijjim_pvrcuh": "obun_gimcijjim_pvrcuh",  # 5분 김치찜
    },
    # 원본 cuisine '기타'(vocab에 없음) → 임시 지정. 검수 필요
    cuisine_overrides={
        "beopalro_hasdalgdarisal_5ypayh": "양식",  # 버팔로 핫닭다리살
        "cadolbulgeuri_6g8c3x": "한식",  # 차돌불그리
        "ggareubo_buldalg_ddeogboggi_exlla0": "한식",  # 까르보 불닭 떡볶이
        "odengeul_hwalyonghayeo_buldalgbbalganodeng_vnp9_n": "한식",  # 불닭빨간오뎅
        "rojejjimdalg_qfddnt": "한식",  # 로제찜닭
    },
)

if __name__ == "__main__":
    sys.exit(run(DATASET, ROOT))
