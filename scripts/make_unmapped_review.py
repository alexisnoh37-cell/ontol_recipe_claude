"""세 출처 미매칭 보강 검수표(docs/review/unmapped_review.md)를 만든다. 판단(승인 열)은 사람이 한다.

    uv run python scripts/make_unmapped_review.py

제안 데이터 docs/review/unmapped_proposal.yaml을 지식 원본에 메모리 안에서만 얹어 컴파일해 검사하고
(별칭 충돌, 없는 재료 id), 엔진 레시피(자취요리신·살림팝)와 식품안전나라의 미매칭 표기 영향을 세어
엔진 레시피 영향 순으로 정렬한다. knowledge/와 data/는 바꾸지 않는다. 이미 적힌 승인 열은 유지한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import KnowledgeError  # noqa: E402
from kb.unmapped_review import OUT, ProposalError, make  # noqa: E402


def main() -> int:
    try:
        text = make(ROOT)
    except (ProposalError, KnowledgeError) as exc:
        print(f"제안 데이터 오류:\n{exc}", file=sys.stderr)
        return 1
    (ROOT / OUT).write_text(text, encoding="utf-8")
    print(f"검수표: {OUT.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
