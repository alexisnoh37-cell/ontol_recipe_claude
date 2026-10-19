"""추천 v2 데이터 묶음 내보내기 (docs/integration/README.md). 다른 앱이 v2 로직을 옮겨 심을 때 쓰는 입력이다.

    uv run python scripts/export_v2_bundle.py                    # → build/v2_bundle/
    uv run python scripts/export_v2_bundle.py --out D:/somewhere

만드는 파일(형식: storage/v2_bundle.py)
  knowledge.json  재료·별칭·is_a 조상·포함 관계·알레르기 closure·알레르기 그룹·대체재·기본 양념·분류 노드
  recipes.json    레시피 전체(엔진에 들어가는 1,522개). 재료 줄·역할·맛·난이도·조리시간·조리기구·기법·검수 상태
  config.json     weights.yaml · engine.yaml · v2.yaml · display.yaml(화면 문구) 내용
  derived.json    매운맛 추정(D9) 결과: 맛 정보는 없지만 매운맛 0으로 보는 레시피 id
  manifest.json   형식 버전, 출처 커밋, 건수, 파일별 SHA-256

깨끗한 checkout(커밋하지 않은 변경 없음)에서 실행해야 manifest의 커밋이 내용과 맞는다. 변경이 있으면 경고하고
`dirty: true`로 표시한다. 레시피 원문 조리 단계는 넣지 않는다(판정에 쓰지 않음, 출처별 이용 조건은 각 앱이 판단).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from engine.v2.config import load_v2_config  # noqa: E402
from engine.v2.spicy import not_spicy_ids  # noqa: E402
from storage.engine_source import CONFIG_DIR, load_files, recipe_from_spec  # noqa: E402
from storage.v2_bundle import config_to_json, knowledge_to_json, recipe_to_json, write_files  # noqa: E402

OUT = ROOT / "build" / "v2_bundle"


def read_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8")) or {}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    if dirty:
        print("경고: 커밋하지 않은 변경이 있습니다. manifest에 dirty: true로 표시합니다.", file=sys.stderr)
    data = load_files(ROOT)
    v1 = data.recommender()
    snapshot = v1.knowledge.snapshot()
    recipes = sorted((recipe_from_spec(s) for s in data.recipes), key=lambda r: r.id)
    cfg = load_v2_config(CONFIG_DIR)
    spicy0 = sorted(not_spicy_ids(snapshot, recipes, cfg.spicy_markers, cfg.spicy_title_markers)
                    if cfg.spicy_inference_enabled else ())
    files = {
        "knowledge.json": knowledge_to_json(snapshot, data.knowledge),
        "recipes.json": {"recipes": [recipe_to_json(r) for r in recipes]},
        "config.json": config_to_json(read_yaml("weights.yaml"), read_yaml("engine.yaml"), read_yaml("v2.yaml"),
                                      read_yaml("display.yaml")),
        "derived.json": {"not_spicy_recipe_ids": spicy0},
    }
    meta = {
        "source": "https://github.com/alexisnoh37-cell/ontol_recipe_claude",
        "commit": git("rev-parse", "HEAD"),
        "dirty": dirty,
        "generated": date.today().isoformat(),
        "counts": {"ingredients": len(snapshot.ingredient_names), "aliases": len(snapshot.alias_index),
                   "allergen_groups": len(snapshot.allergen_closure), "recipes": len(recipes),
                   "not_spicy_recipes": len(spicy0)},
    }
    manifest = write_files(args.out, files, meta)
    print(f"내보냄: {args.out} (레시피 {meta['counts']['recipes']}, 재료 {meta['counts']['ingredients']}, "
          f"커밋 {meta['commit'][:7]}{' dirty' if dirty else ''})")
    for name, h in manifest["files"].items():
        print(f"  {name}  {h[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
