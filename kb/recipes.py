"""레시피 시드 읽기 (data/recipes/*.yaml, 형식: data/recipes/README.md).

파일 하나에 레시피 하나. 검증 규칙은 kb.datacheck.check_recipes(RecipeSpec)가 원본이다.
scripts/validate_data.py, scripts/load_recipes.py, scripts/make_recipe_review.py가 같은 함수를 쓴다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from kb.compiled import CompiledKnowledge
from kb.datacheck import RecipeSpec, check_recipes
from kb.validate import Issue


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
                out.append((where, yaml.safe_load(fh)))
        except yaml.YAMLError as exc:
            out.append((where, {"__yaml_error__": str(exc)}))
    return out


def load_recipe_specs(ck: CompiledKnowledge, recipes_dir: Path, root: Path | None = None) -> list[RecipeSpec]:
    """검증을 통과한 레시피만 돌려준다. 오류가 하나라도 있으면 RecipeSeedError(일부만 적재하지 않는다)."""
    items = read_recipe_dir(recipes_dir, root)
    issues = check_recipes(ck, items)
    if issues:
        raise RecipeSeedError(issues)
    specs = [RecipeSpec.model_validate(item) for _, item in items]
    return sorted(specs, key=lambda r: r.id)
