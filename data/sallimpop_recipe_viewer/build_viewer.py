from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml


PROJECT = Path(__file__).resolve().parent
DATASET = PROJECT.parent / "sallimpop_recipe_dataset"
RECIPES = DATASET / "recipes" / "sallimpop"
OUTPUT = PROJECT / "dist" / "recipes-data.js"


def video_id(url: str) -> str:
    match = re.search(r"[?&]v=([^&]+)", url)
    return match.group(1) if match else ""


def main() -> None:
    recipes = []
    ingredient_counts: Counter[str] = Counter()

    for path in sorted(RECIPES.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        vid = video_id(data["source"]["video_url"])
        item = {
            "id": data["id"],
            "title": data["title"],
            "cuisine": data["cuisine"],
            "difficulty": data["difficulty"],
            "cookTime": data["cook_time_min"],
            "servings": data["servings"],
            "status": data["status"],
            "confidence": data["confidence"],
            "note": data["note"],
            "source": {
                "videoTitle": data["source"]["video_title"],
                "videoUrl": data["source"]["video_url"],
                "publishedAt": data["source"]["published_at"],
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "",
            },
            "ingredients": data["ingredients"],
            "taste": data["taste"],
            "equipment": data["equipment"],
            "steps": data["steps"],
        }
        recipes.append(item)
        ingredient_counts.update(i["name"] for i in data["ingredients"])

    cuisine_counts = Counter(item["cuisine"] for item in recipes)
    payload = {
        "generatedAt": "2026-10-16",
        "channel": "살림팝",
        "channelUrl": "https://www.youtube.com/@%EC%82%B4%EB%A6%BC%ED%8C%9D",
        "summary": {
            "recipeCount": len(recipes),
            "candidateCount": 259,
            "skippedCount": 259 - len(recipes),
            "cuisines": dict(cuisine_counts),
            "topIngredients": [
                {"name": name, "count": count}
                for name, count in ingredient_counts.most_common(12)
            ],
        },
        "recipes": recipes,
    }
    OUTPUT.write_text(
        "window.RECIPE_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"생성 완료: {len(recipes)}개 레시피 → {OUTPUT}")


if __name__ == "__main__":
    main()
