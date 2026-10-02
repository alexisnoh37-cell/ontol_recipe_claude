"""초기 스키마 (docs/plan.md 부록 B DDL 그대로).

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-03
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# 부록 B와 문장 단위로 일치해야 한다(tests/logic/test_migration_matches_plan.py).
STATEMENTS = [
    """
CREATE TABLE knowledge_build (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_hash  text NOT NULL,
  compiled_at  timestamptz NOT NULL DEFAULT now(),
  stats        jsonb NOT NULL
)
    """,
    """
CREATE TABLE ingredient (
  id               text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  name             text NOT NULL,
  kind             text NOT NULL DEFAULT 'ingredient' CHECK (kind IN ('ingredient','concept')),
  category         text,
  is_pantry_staple boolean NOT NULL DEFAULT false,
  is_processed     boolean NOT NULL DEFAULT false,
  status           text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence       text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note             text
)
    """,
    """
CREATE TABLE ingredient_alias (
  alias_norm    text PRIMARY KEY,
  alias         text NOT NULL,
  ingredient_id text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  form          text,
  is_primary    boolean NOT NULL DEFAULT false
)
    """,
    """
CREATE INDEX ingredient_alias_prefix_idx ON ingredient_alias (alias_norm text_pattern_ops)
    """,
    """
CREATE INDEX ON ingredient_alias (ingredient_id)
    """,
    """
CREATE TABLE ingredient_relation (
  from_id    text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  to_id      text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  type       text NOT NULL CHECK (type IN ('is_a','derived_from','substitute','pairs_with')),
  certainty  text CHECK (certainty IN ('definite','possible')),
  context    text[] NOT NULL DEFAULT '{}',
  ratio      numeric(3,2) CHECK (ratio > 0 AND ratio <= 1),
  status     text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note       text,
  PRIMARY KEY (from_id, to_id, type),
  CHECK (from_id <> to_id),
  CHECK ((type = 'derived_from') = (certainty IS NOT NULL))
)
    """,
    """
CREATE INDEX ON ingredient_relation (to_id, type)
    """,
    """
CREATE TABLE allergen_group (
  id           text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  display_name text NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('base','bundle')),
  status       text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence   text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note         text
)
    """,
    """
CREATE TABLE allergen_group_member (
  bundle_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  member_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  PRIMARY KEY (bundle_id, member_id)
)
    """,
    """
CREATE TABLE ingredient_allergen (
  ingredient_id     text REFERENCES ingredient(id) ON DELETE CASCADE,
  allergen_group_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  certainty         text NOT NULL CHECK (certainty IN ('definite','possible')),
  PRIMARY KEY (ingredient_id, allergen_group_id)
)
    """,
    """
CREATE TABLE ingredient_ancestor (
  ingredient_id text REFERENCES ingredient(id) ON DELETE CASCADE,
  ancestor_id   text REFERENCES ingredient(id) ON DELETE CASCADE,
  depth         smallint NOT NULL CHECK (depth >= 1),
  PRIMARY KEY (ingredient_id, ancestor_id)
)
    """,
    """
CREATE TABLE ingredient_contains (
  ingredient_id text REFERENCES ingredient(id) ON DELETE CASCADE,
  contained_id  text REFERENCES ingredient(id) ON DELETE CASCADE,
  certainty     text NOT NULL CHECK (certainty IN ('definite','possible')),
  via           text[] NOT NULL,
  PRIMARY KEY (ingredient_id, contained_id)
)
    """,
    """
CREATE TABLE allergen_closure (
  allergen_group_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  ingredient_id     text REFERENCES ingredient(id) ON DELETE CASCADE,
  certainty         text NOT NULL CHECK (certainty IN ('definite','possible')),
  via               text[] NOT NULL,
  PRIMARY KEY (allergen_group_id, ingredient_id)
)
    """,
    """
CREATE INDEX ON allergen_closure (ingredient_id)
    """,
    """
CREATE TABLE recipe (
  id            text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  title         text NOT NULL,
  cuisine       text NOT NULL,
  difficulty    smallint NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  cook_time_min integer NOT NULL CHECK (cook_time_min > 0),
  servings      smallint CHECK (servings > 0),
  source        text NOT NULL,
  status        text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
  confidence    text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note          text,
  updated_at    timestamptz NOT NULL DEFAULT now()
)
    """,
    """
CREATE TABLE recipe_ingredient (
  recipe_id     text REFERENCES recipe(id) ON DELETE CASCADE,
  line_no       smallint,
  ingredient_id text REFERENCES ingredient(id) ON DELETE RESTRICT,  -- NULL = 미매칭
  role          text NOT NULL CHECK (role IN ('main','sub','seasoning','garnish')),
  optional      boolean NOT NULL DEFAULT false,
  amount        numeric(8,2),
  unit          text,
  raw_text      text NOT NULL,
  PRIMARY KEY (recipe_id, line_no)
)
    """,
    """
CREATE INDEX ON recipe_ingredient (ingredient_id)
    """,
    """
CREATE TABLE recipe_taste (
  recipe_id text PRIMARY KEY REFERENCES recipe(id) ON DELETE CASCADE,
  spicy  smallint NOT NULL CHECK (spicy  BETWEEN 0 AND 5),
  salty  smallint NOT NULL CHECK (salty  BETWEEN 0 AND 5),
  sweet  smallint NOT NULL CHECK (sweet  BETWEEN 0 AND 5),
  sour   smallint NOT NULL CHECK (sour   BETWEEN 0 AND 5),
  umami  smallint NOT NULL CHECK (umami  BETWEEN 0 AND 5),
  savory smallint NOT NULL CHECK (savory BETWEEN 0 AND 5)
)
    """,
    """
CREATE TABLE recipe_equipment (
  recipe_id text REFERENCES recipe(id) ON DELETE CASCADE,
  equipment text NOT NULL,
  required  boolean NOT NULL DEFAULT true,
  PRIMARY KEY (recipe_id, equipment)
)
    """,
    """
CREATE TABLE recipe_step (
  recipe_id text REFERENCES recipe(id) ON DELETE CASCADE,
  step_no   smallint,
  text      text NOT NULL,
  technique text,
  PRIMARY KEY (recipe_id, step_no)
)
    """,
    """
CREATE TABLE user_profile (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  display_name   text NOT NULL UNIQUE,
  skill_level    smallint NOT NULL DEFAULT 1 CHECK (skill_level BETWEEN 1 AND 3),
  household_size smallint NOT NULL DEFAULT 1 CHECK (household_size > 0),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
)
    """,
    """
CREATE TABLE user_preference (
  user_id     bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  target_type text NOT NULL CHECK (target_type IN ('ingredient','cuisine','allergen_group')),
  target_id   text NOT NULL,
  polarity    smallint NOT NULL CHECK (polarity IN (-1, 1)),
  strength    numeric(3,2) NOT NULL CHECK (strength BETWEEN 0 AND 1),
  is_hard     boolean NOT NULL DEFAULT false,
  PRIMARY KEY (user_id, target_type, target_id),
  CHECK (NOT is_hard OR polarity = -1),
  CHECK (target_type <> 'allergen_group' OR (is_hard AND polarity = -1))
)
    """,
    """
CREATE TABLE user_taste (
  user_id         bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  dimension       text NOT NULL CHECK (dimension IN ('spicy','salty','sweet','sour','umami','savory')),
  preferred_level smallint CHECK (preferred_level BETWEEN 0 AND 5),
  max_level       smallint CHECK (max_level BETWEEN 0 AND 5),
  PRIMARY KEY (user_id, dimension),
  CHECK (preferred_level IS NULL OR max_level IS NULL OR preferred_level <= max_level)
)
    """,
    """
CREATE TABLE user_pantry (
  user_id       bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  ingredient_id text REFERENCES ingredient(id) ON DELETE RESTRICT,
  expires_on    date,
  PRIMARY KEY (user_id, ingredient_id)
)
    """,
    """
CREATE TABLE user_equipment (
  user_id   bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  equipment text NOT NULL,
  PRIMARY KEY (user_id, equipment)
)
    """,
    """
CREATE TABLE unmapped_term (
  term_norm   text PRIMARY KEY,
  raw_example text NOT NULL,
  source      text NOT NULL CHECK (source IN ('recipe','user_input')),
  seen_count  integer NOT NULL DEFAULT 1,
  first_seen  timestamptz NOT NULL DEFAULT now(),
  last_seen   timestamptz NOT NULL DEFAULT now()
)
    """,
]

TABLES = ['knowledge_build', 'ingredient', 'ingredient_alias', 'ingredient_relation', 'allergen_group', 'allergen_group_member', 'ingredient_allergen', 'ingredient_ancestor', 'ingredient_contains', 'allergen_closure', 'recipe', 'recipe_ingredient', 'recipe_taste', 'recipe_equipment', 'recipe_step', 'user_profile', 'user_preference', 'user_taste', 'user_pantry', 'user_equipment', 'unmapped_term']


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
