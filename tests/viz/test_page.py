"""GET /viz 정적 페이지 (docs/plan.md 부록 D). JS 동작은 브라우저로 확인하고, 여기서는 제공 경로와 CDN 버전 고정만 본다."""

from __future__ import annotations

import re

from api.main import VIZ_DIR


def test_viz_page_and_static_files_are_served(client):
    r = client.get("/viz")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "/viz/static/app.js" in r.text
    for el in ('id="subject"', 'id="pantry-add"', 'id="run"', 'id="prev"', 'id="next"', 'id="auto"', 'id="cards"'):
        assert el in r.text, el  # 재생 패널(viz-4)
    for el in ('id="adhoc-title"', 'id="adhoc-text"', 'id="adhoc-subject"', 'id="adhoc-run"', 'id="adhoc-result"'):
        assert el in r.text, el  # 외부 레시피 분석 카드(부록 E)
    for name in ("app.js", "scene.js", "palette.js", "playback.js", "adhoc.js", "style.css"):
        assert client.get(f"/viz/static/{name}").status_code == 200, name


def test_cdn_versions_are_pinned_and_share_one_three():
    """3d-force-graph의 ESM이 가져오는 three와 페이지가 직접 쓰는 three가 같은 버전이어야 재질·메시가 한 인스턴스를 쓴다."""
    urls = set()
    for path in VIZ_DIR.glob("*.js"):
        urls |= set(re.findall(r"https://cdn\.jsdelivr\.net/npm/[^\"']+", path.read_text(encoding="utf-8")))
    assert urls == {
        "https://cdn.jsdelivr.net/npm/3d-force-graph@1.80.1/+esm",
        "https://cdn.jsdelivr.net/npm/three@0.186.1/+esm",
    }


def test_browse_card_is_served(client):
    """재료로 레시피 찾기 카드(ui-2). 동작은 브라우저로 확인한다."""
    html = client.get("/viz").text
    for el in ('id="browse-add"', 'id="browse-pick"', 'id="browse-subject"', 'id="browse-run"', 'id="browse-list"'):
        assert el in html, el
    assert client.get("/viz/static/browse.js").status_code == 200


def test_tree_layout_controls_are_served(client):
    """나무 배치(부록 D-9): 배치 선택, 출처 토글 자리, tree.js. 좌표·전환은 브라우저로 확인한다."""
    html = client.get("/viz").text
    for el in ('id="layout-mode"', 'id="origin-toggles"', 'id="display-toggle"'):
        assert el in html, el
    tree = client.get("/viz/static/tree.js")
    assert tree.status_code == 200 and "export function treeLayout" in tree.text
    scene = client.get("/viz/static/scene.js").text
    assert all(k in scene for k in ('"tree-ingredient"', '"tree-cuisine"', "flat:"))
