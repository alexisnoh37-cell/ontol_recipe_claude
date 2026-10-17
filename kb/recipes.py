"""레시피 시드 읽기 (data/recipes/*.yaml 등, 형식: data/recipes/README.md).

파일 하나에 레시피 하나. 검증 규칙은 kb.datacheck.check_recipes(RecipeSpec)가 원본이다.
엔진·DB가 읽는 폴더 목록은 config/engine.yaml의 recipe_dirs다(ar-1: data/recipes + data/recipes_foodsafety).
scripts/validate_data.py, scripts/load_recipes.py, scripts/make_recipe_review.py가 같은 함수를 쓴다.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from kb.compiled import CompiledKnowledge
from kb.datacheck import RecipeSpec, check_recipes
from kb.validate import Issue

# libyaml이 있으면 C 파서(같은 결과, 식품안전나라 1153개 기준 약 6배 빠름)
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class RecipeSeedError(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__(f"레시피 시드 오류 {len(issues)}건: " + "; ".join(str(i) for i in issues[:5]))


def read_recipe_dir(recipes_dir: Path, root: Path | None = None) -> list[tuple[str, Any]]:
    """(출처 표기, YAML 내용) 목록. 폴더가 없으면 빈 목록. 파일 이름 순."""
    if not recipes_dir.is_dir():
        return []
    out = []
    for path in sorted(recipes_dir.glob("*.yaml")):
        where = path.relative_to(root).as_posix() if root and path.is_relative_to(root) else path.as_posix()
        try:
            with path.open("r", encoding="utf-8") as fh:
                out.append((where, yaml.load(fh, Loader=_LOADER)))
        except yaml.YAMLError as exc:
            out.append((where, {"__yaml_error__": str(exc)}))
    return out


def load_recipe_specs(ck: CompiledKnowledge, recipes_dirs: Path | Sequence[Path],
                      root: Path | None = None) -> list[RecipeSpec]:
    """검증을 통과한 레시피만 돌려준다. 오류가 하나라도 있으면 RecipeSeedError(일부만 적재하지 않는다).

    폴더를 여러 개 주면 모두 읽어 한 목록으로 검증한다(id 중복은 오류). draft는 cuisine 미분류, 조리시간·난이도·맛
    없음을 허용하고 엔진이 '모름'으로 다룬다(ar-1, docs/plan.md 5-4). published는 검증 규칙이 모두 요구한다.
    """
    dirs = [recipes_dirs] if isinstance(recipes_dirs, Path) else list(recipes_dirs)
    items = [item for d in dirs for item in read_recipe_dir(d, root)]
    issues = check_recipes(ck, items)
    if issues:
        raise RecipeSeedError(issues)
    specs = [RecipeSpec.model_validate(item) for _, item in items]
    return sorted(specs, key=lambda r: r.id)


def load_display_specs(ck: CompiledKnowledge, recipes_dir: Path, root: Path | None = None) -> tuple[list[RecipeSpec], int]:
    """그래프 표시 전용 레시피(엔진·DB에 적재하지 않음, 예: data/recipes_foodsafety/). (검증 통과분, 건너뛴 수).

    draft 규칙(cuisine 미분류, cook_time_min 없음, 미매칭)을 허용하는 검증만 하고 적재 거부 규칙은 쓰지 않는다.
    지식과 맞지 않는 파일(없는 재료 id 등)은 그 파일만 건너뛴다(표시 전용이라 전체를 막지 않는다).
    """
    specs, skipped = [], 0
    for where, item in read_recipe_dir(recipes_dir, root):
        if check_recipes(ck, [(where, item)]):
            skipped += 1
            continue
        specs.append(RecipeSpec.model_validate(item))
    return sorted(specs, key=lambda r: r.id), skipped
