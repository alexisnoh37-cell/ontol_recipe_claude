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


def test_v2_playback_panel_is_served(client):
    """v2(Jev) 추천 과정 탭(부록 H-4). 단계·그래프 강조는 브라우저로 확인한다."""
    html = client.get("/viz").text
    for el in ('data-tab="v1"', 'data-tab="v2"', 'id="v2-persona"', 'id="v2-ranking"', 'data-v2-run="random"',
               'data-v2-run="pantry"', 'data-v2-run="dish"', 'id="v2-query"', 'id="v2-step-body"', 'id="v2-cards"'):
        assert el in html, el
    js = client.get("/viz/static/playback_v2.js")
    assert js.status_code == 200 and "export function setupPlaybackV2" in js.text
    assert "setupPlaybackV2" in client.get("/viz/static/app.js").text


def test_v2_stage_controls_are_served(client):
    """v2 재생 무대(부록 H-7): 깔때기 막대·자동 재생·카메라 따라가기, 장면의 무대 함수. 움직임은 브라우저로 확인한다."""
    html = client.get("/viz").text
    for el in ('id="v2-funnel"', 'id="v2-autoplay"', 'id="v2-follow"'):
        assert el in html, el
    scene = client.get("/viz/static/scene.js").text
    assert all(k in scene for k in ("setStage", "setTargets", "stageInfo", "homeOf", "lookAt", "function buildStage"))
    play = client.get("/viz/static/playback_v2.js").text
    assert all(k in play for k in ("targetsFor", "renderFunnel", "followCamera"))


def test_v2_petals_are_served():
    """Jev 꽃잎(부록 H-8): 장면의 꽃 그리기, 재생의 꽃·범례. 모양·움직임은 브라우저로 확인한다."""
    scene = (VIZ_DIR / "scene.js").read_text(encoding="utf-8")
    assert all(k in scene for k in ("setGlyphs", "const PETAL ", "PETAL_SIZE"))
    play = (VIZ_DIR / "playback_v2.js").read_text(encoding="utf-8")
    assert all(k in play for k in ("glyphsFor", "petalLegend", "PETAL_COLOR"))
    for aspect in ("request", "taste", "ingredients", "cuisine", "skill", "pantry"):  # Jev 항목마다 꽃잎 색
        assert f"{aspect}:" in play, aspect


def test_v2_whatif_is_served(client):
    """What-if(부록 H-9): 패널 자리와 재생 코드. 비교·움직임은 브라우저로 확인한다."""
    assert 'id="v2-whatif"' in client.get("/viz").text
    play = (VIZ_DIR / "playback_v2.js").read_text(encoding="utf-8")
    assert all(k in play for k in ("applyWhatif", "diffRuns", "overlayDiff", "renderWhatif"))
    assert "body.seed = base.t.seed" in play  # 랜덤은 같은 seed로 다시 실행해야 비교가 된다
    assert '"/allergen-groups"' in play


def test_sector_map_layout_is_served(client):
    """분류 지도 배치(부록 H-10): 배치 선택에 들어 있고, sector.js·물결·탑을 제공한다. 좌표·움직임은 브라우저로 확인한다."""
    sector = client.get("/viz/static/sector.js")
    assert sector.status_code == 200 and "export function sectorLayout" in sector.text
    scene = (VIZ_DIR / "scene.js").read_text(encoding="utf-8")
    assert 'sector: "분류 지도(위에서)"' in scene
    assert all(k in scene for k in ("setWave", "setTowers", "function decorateSector", "sectorMapLayout"))
    play = (VIZ_DIR / "playback_v2.js").read_text(encoding="utf-8")
    assert all(k in play for k in ("towersFor", "allergenReach"))
    assert 'v2Panel ? "bowl"' in (VIZ_DIR / "app.js").read_text(encoding="utf-8")  # v2 탭 기본 배치


def test_scene_imports_do_not_shadow_local_functions():
    """모듈 안 같은 이름 선언은 브라우저에서 SyntaxError로 화면 전체가 멈춘다(분류 지도 작업 중 실제로 겪음)."""
    for path in VIZ_DIR.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        imported = set()
        for spec in re.findall(r"import\s*\{([^}]*)\}", text):
            for part in spec.split(","):
                name = part.split(" as ")[-1].strip()
                if name:
                    imported.add(name)
        declared = re.findall(r"^(?:export\s+)?(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)", text, re.M)
        assert not imported & set(declared), (path.name, imported & set(declared))


def test_bowl_layout_is_served():
    """원형 경기장(부록 H-11): 배치 선택, 계단 높이 배치, 3D 장식, 바닥으로 미끄러지는 제외. 모양은 브라우저로 확인한다."""
    sector = (VIZ_DIR / "sector.js").read_text(encoding="utf-8")
    assert all(k in sector for k in ("export function bowlLayout", "export const BOWL", "heightAt", "pitR", "BOWL_LAYERS"))
    for name in ("알레르기 그룹", "원천 재료·분류", "가공품", "레시피"):  # 층 이름(옆 눈금·먼 쪽 벽·계단 테두리 색)
        assert f'name: "{name}"' in sector, name
    scene = (VIZ_DIR / "scene.js").read_text(encoding="utf-8")
    assert 'bowl: "원형 경기장(3D)"' in scene and "function decorateBowl" in scene
    play = (VIZ_DIR / "playback_v2.js").read_text(encoding="utf-8")
    assert "info.bowl" in play and "heightAt: info.heightAt" in play
