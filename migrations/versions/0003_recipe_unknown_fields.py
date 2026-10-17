"""recipe.difficulty·cook_time_min을 비워 둘 수 있게 한다(모름). 식품안전나라 레시피 적재용 (docs/plan.md 부록 B, ar-1 승인).

Revision ID: 0003_recipe_unknown_fields
Revises: 0002_allergen_group_official
Create Date: 2026-10-17
"""

from alembic import op

revision = "0003_recipe_unknown_fields"
down_revision = "0002_allergen_group_official"
branch_labels = None
depends_on = None

# 부록 B의 "0003" 블록과 문장 단위로 일치해야 한다(tests/logic/test_migration_matches_plan.py).
STATEMENTS = [
    """
ALTER TABLE recipe
  ALTER COLUMN difficulty DROP NOT NULL,
  ALTER COLUMN cook_time_min DROP NOT NULL
    """,
]


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    # 예전 스키마에 맞지 않는 레시피(값을 모르는 레시피)는 지운다. 값을 지어내 채우지 않는다(하위 행은 ON DELETE CASCADE).
    # 다시 upgrade한 뒤 scripts/load_recipes.py로 재적재하면 돌아온다.
    op.execute("DELETE FROM recipe WHERE difficulty IS NULL OR cook_time_min IS NULL")
    op.execute("ALTER TABLE recipe ALTER COLUMN difficulty SET NOT NULL, ALTER COLUMN cook_time_min SET NOT NULL")
