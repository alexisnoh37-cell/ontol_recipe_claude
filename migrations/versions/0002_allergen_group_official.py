"""allergen_group에 법정 표시 대상 여부(official)와 출처(source) 추가 (docs/plan.md 부록 B, 0-4 승인).

Revision ID: 0002_allergen_group_official
Revises: 0001_initial
Create Date: 2026-10-03
"""

from alembic import op

revision = "0002_allergen_group_official"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

# 부록 B의 "0002" 블록과 문장 단위로 일치해야 한다(tests/logic/test_migration_matches_plan.py).
STATEMENTS = [
    """
ALTER TABLE allergen_group
  ADD COLUMN official boolean NOT NULL DEFAULT false,
  ADD COLUMN source   text    NOT NULL DEFAULT 'custom' CHECK (source IN ('law_annex2','custom')),
  ADD CONSTRAINT allergen_group_official_source CHECK (official = (source = 'law_annex2'))
    """,
]


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE allergen_group DROP CONSTRAINT allergen_group_official_source, "
        "DROP COLUMN source, DROP COLUMN official"
    )
