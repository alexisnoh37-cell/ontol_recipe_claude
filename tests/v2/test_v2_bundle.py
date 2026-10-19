"""다른 앱용 데이터 묶음(scripts/export_v2_bundle.py, storage/v2_bundle.py)과 안내 문서 링크."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from engine.v2.model import V2Request
from engine.v2.profile import SimpleProfile
from scripts import export_v2_bundle
from storage.engine_source import load_files
from storage.v2_bundle import FORMAT_VERSION, recommender_from_json

ROOT = Path(__file__).resolve().parents[2]


def test_export_bundle_round_trip(tmp_path):
    assert export_v2_bundle.main(["--out", str(tmp_path)]) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format_version"] == FORMAT_VERSION and len(manifest["commit"]) == 40
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest, name
    load = lambda n: json.loads((tmp_path / n).read_text(encoding="utf-8"))  # noqa: E731
    knowledge, recipes, config, derived = (load("knowledge.json"), load("recipes.json")["recipes"],
                                           load("config.json"), load("derived.json"))
    data = load_files()
    assert len(recipes) == len(data.recipes) == manifest["counts"]["recipes"]
    assert {"weights", "engine", "v2", "display"} <= set(config)
    assert any(m["is_processed"] and m["confidence"] == "low" for m in knowledge["ingredient_meta"].values())
    # JSON만으로 조립한 엔진이 같은 매운맛 추정과 같은 추천을 낸다
    v2 = recommender_from_json(knowledge, recipes, config)
    assert set(derived["not_spicy_recipe_ids"]) == set(v2.not_spicy())
    original = data.recommender()
    from engine.v2.config import load_v2_config
    from engine.v2.recommend import RecommenderV2
    from storage.engine_source import CONFIG_DIR

    direct = RecommenderV2.from_v1(original, load_v2_config(CONFIG_DIR))
    user = SimpleProfile(allergens=frozenset({"shrimp"}), spicy_level=1).to_user_context(
        equipment=data.knowledge.vocab["equipment"])
    for req in (V2Request("pantry", pantry=frozenset({"egg", "rice", "onion"}), rerank=False),
                V2Request("dish", query="오늘은 얼큰한 국물이 끌려", rerank=False)):
        a = [i.item.recipe_id for i in v2.recommend(user, req).items]
        b = [i.item.recipe_id for i in direct.recommend(user, req).items]
        assert a == b


def test_integration_readme_links_resolve():
    for doc in (ROOT / "docs" / "integration" / "README.md", ROOT / "README.md"):
        text = doc.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+\.md)\)", text):
            assert (doc.parent / target).resolve().exists(), f"{doc.name}: {target}"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/integration/README.md" in readme.split("## 무엇이 들어 있나")[0]
