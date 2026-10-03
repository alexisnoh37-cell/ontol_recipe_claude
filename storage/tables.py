"""SQLAlchemy Core 테이블 정의. 스키마의 원본은 migrations/(부록 B DDL)이고 이 파일은 그 거울이다.

제약(CHECK 등)은 마이그레이션에만 둔다. 여기서는 읽기·쓰기에 필요한 컬럼만 정의한다.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

metadata = MetaData()

knowledge_build = Table(
    "knowledge_build", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("source_hash", Text, nullable=False),
    Column("compiled_at", DateTime(timezone=True)),
    Column("stats", JSONB, nullable=False),
)

ingredient = Table(
    "ingredient", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("category", Text),
    Column("is_pantry_staple", Boolean, nullable=False),
    Column("is_processed", Boolean, nullable=False),
    Column("status", Text, nullable=False),
    Column("confidence", Text, nullable=False),
    Column("note", Text),
)

ingredient_alias = Table(
    "ingredient_alias", metadata,
    Column("alias_norm", Text, primary_key=True),
    Column("alias", Text, nullable=False),
    Column("ingredient_id", Text, nullable=False),
    Column("form", Text),
    Column("is_primary", Boolean, nullable=False),
)

ingredient_relation = Table(
    "ingredient_relation", metadata,
    Column("from_id", Text, primary_key=True),
    Column("to_id", Text, primary_key=True),
    Column("type", Text, primary_key=True),
    Column("certainty", Text),
    Column("context", ARRAY(Text), nullable=False),
    Column("ratio", Numeric(3, 2)),
    Column("status", Text, nullable=False),
    Column("confidence", Text, nullable=False),
    Column("note", Text),
)

allergen_group = Table(
    "allergen_group", metadata,
    Column("id", Text, primary_key=True),
    Column("display_name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("official", Boolean, nullable=False),
    Column("source", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("confidence", Text, nullable=False),
    Column("note", Text),
)

allergen_group_member = Table(
    "allergen_group_member", metadata,
    Column("bundle_id", Text, primary_key=True),
    Column("member_id", Text, primary_key=True),
)

ingredient_allergen = Table(
    "ingredient_allergen", metadata,
    Column("ingredient_id", Text, primary_key=True),
    Column("allergen_group_id", Text, primary_key=True),
    Column("certainty", Text, nullable=False),
)

ingredient_ancestor = Table(
    "ingredient_ancestor", metadata,
    Column("ingredient_id", Text, primary_key=True),
    Column("ancestor_id", Text, primary_key=True),
    Column("depth", SmallInteger, nullable=False),
)

ingredient_contains = Table(
    "ingredient_contains", metadata,
    Column("ingredient_id", Text, primary_key=True),
    Column("contained_id", Text, primary_key=True),
    Column("certainty", Text, nullable=False),
    Column("via", ARRAY(Text), nullable=False),
)

allergen_closure = Table(
    "allergen_closure", metadata,
    Column("allergen_group_id", Text, primary_key=True),
    Column("ingredient_id", Text, primary_key=True),
    Column("certainty", Text, nullable=False),
    Column("via", ARRAY(Text), nullable=False),
)

recipe = Table(
    "recipe", metadata,
    Column("id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("cuisine", Text, nullable=False),
    Column("difficulty", SmallInteger, nullable=False),
    Column("cook_time_min", Integer, nullable=False),
    Column("servings", SmallInteger),
    Column("source", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("confidence", Text, nullable=False),
    Column("note", Text),
    Column("updated_at", DateTime(timezone=True)),
)

recipe_ingredient = Table(
    "recipe_ingredient", metadata,
    Column("recipe_id", Text, primary_key=True),
    Column("line_no", SmallInteger, primary_key=True),
    Column("ingredient_id", Text),
    Column("role", Text, nullable=False),
    Column("optional", Boolean, nullable=False),
    Column("amount", Numeric(8, 2)),
    Column("unit", Text),
    Column("raw_text", Text, nullable=False),
)

recipe_taste = Table(
    "recipe_taste", metadata,
    Column("recipe_id", Text, primary_key=True),
    Column("spicy", SmallInteger, nullable=False),
    Column("salty", SmallInteger, nullable=False),
    Column("sweet", SmallInteger, nullable=False),
    Column("sour", SmallInteger, nullable=False),
    Column("umami", SmallInteger, nullable=False),
    Column("savory", SmallInteger, nullable=False),
)

recipe_equipment = Table(
    "recipe_equipment", metadata,
    Column("recipe_id", Text, primary_key=True),
    Column("equipment", Text, primary_key=True),
    Column("required", Boolean, nullable=False),
)

recipe_step = Table(
    "recipe_step", metadata,
    Column("recipe_id", Text, primary_key=True),
    Column("step_no", SmallInteger, primary_key=True),
    Column("text", Text, nullable=False),
    Column("technique", Text),
)

user_profile = Table(
    "user_profile", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("display_name", Text, nullable=False),
    Column("skill_level", SmallInteger, nullable=False),
    Column("household_size", SmallInteger, nullable=False),
    Column("updated_at", DateTime(timezone=True)),
)

user_preference = Table(
    "user_preference", metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("target_type", Text, primary_key=True),
    Column("target_id", Text, primary_key=True),
    Column("polarity", SmallInteger, nullable=False),
    Column("strength", Numeric(3, 2), nullable=False),
    Column("is_hard", Boolean, nullable=False),
)

user_taste = Table(
    "user_taste", metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("dimension", Text, primary_key=True),
    Column("preferred_level", SmallInteger),
    Column("max_level", SmallInteger),
)

user_equipment = Table(
    "user_equipment", metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("equipment", Text, primary_key=True),
)

user_pantry = Table(
    "user_pantry", metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("ingredient_id", Text, primary_key=True),
    Column("expires_on", Date),
)

unmapped_term = Table(
    "unmapped_term", metadata,
    Column("term_norm", Text, primary_key=True),
    Column("raw_example", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("seen_count", Integer, nullable=False),
)

# 컴파일러가 매번 지우고 다시 넣는 지식 테이블(FK 의존 순서: 자식 먼저)
DERIVED_KNOWLEDGE_TABLES = (
    allergen_closure,
    ingredient_contains,
    ingredient_ancestor,
    ingredient_allergen,
    allergen_group_member,
    ingredient_relation,
    ingredient_alias,
)
