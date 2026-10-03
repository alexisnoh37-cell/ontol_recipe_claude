"""FastAPI 앱 (Phase 1-5).

실행(저장소 루트): uv run uvicorn api.main:default_app --factory --port 8000
  - ENGINE_SOURCE=db(기본): 시작 시 DB의 컴파일 결과·레시피를 읽어 엔진을 만든다(부록 A).
    재컴파일·레시피 적재 후에는 POST /admin/reload 또는 재시작.
  - ENGINE_SOURCE=files: knowledge/·data/recipes/를 직접 컴파일(DB 없이 확인할 때). 사용자 저장은 DB 필요.
엔진·표시 데이터는 storage.engine_source(골든셋·벤치·테스트와 같은 변환 함수)로 만든다.
제외된 레시피는 사유를 logs/exclusions.jsonl에 한 줄씩 남긴다(EXCLUSION_LOG로 경로 변경).
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response

from api.present import TASTE_DIMENSIONS, Catalog, load_display
from api.schemas import PreferencesIn, ProfileCreate, ProfileOut, ProfileUpdate, RecommendIn
from api.viz import GraphCatalog, RecipeScope
from engine.model import Preference, RecommendRequest, RecommendResult, TastePreference, UserContext
from engine.recommend import Recommender
from storage.engine_source import CONFIG_DIR, ROOT, EngineData
from storage.personas import Persona, load_personas
from storage.users import (
    DuplicateProfileName,
    PreferenceRow,
    Profile,
    ProfileNotFound,
    ProfilePatch,
    TasteRow,
    UserStore,
)


class State:
    """엔진과 표시 카탈로그. reload 때 통째로 바꾼다(요청 중에는 읽기만)."""

    def __init__(self, loader: Callable[[], EngineData], config_dir: Path):
        self.loader = loader
        self.config_dir = config_dir
        self.lock = threading.Lock()
        self.reload()

    def reload(self) -> None:
        data = self.loader()
        recommender = data.recommender(config_dir=self.config_dir)
        catalog = Catalog(data, load_display(self.config_dir))
        graph = GraphCatalog(data)
        with self.lock:
            self.recommender: Recommender = recommender
            self.catalog: Catalog = catalog
            self.graph: GraphCatalog = graph


def user_context(p: Profile) -> UserContext:
    return UserContext(
        skill_level=p.skill_level,
        allergen_groups=frozenset(r.target_id for r in p.preferences if r.target_type == "allergen_group"),
        preferences=tuple(Preference(r.target_type, r.target_id, r.polarity, r.strength, r.is_hard)  # type: ignore[arg-type]
                          for r in p.preferences if r.target_type != "allergen_group"),
        tastes=tuple(TastePreference(t.dimension, t.preferred_level, t.max_level)  # type: ignore[arg-type]
                     for t in p.tastes),
        pantry=frozenset(p.pantry),
        equipment=frozenset(p.equipment),
    )


def create_app(loader: Callable[[], EngineData], store: UserStore, *, config_dir: Path = CONFIG_DIR,
               exclusion_log: Path | None = None, personas: Callable[[], list[Persona]] = load_personas) -> FastAPI:
    state = State(loader, config_dir)
    persona_index = {p.id: p for p in personas()}
    app = FastAPI(title="레시피 추천 엔진 API", version="0.1.0")
    app.state.engine_state = state

    # --- 검증 도우미 ---------------------------------------------------------------------------------

    def bad(msg: str) -> HTTPException:
        return HTTPException(status_code=400, detail=msg)

    def check_pantry(ids: list[str]) -> list[str]:
        cat = state.catalog
        unknown = [i for i in ids if i not in cat.ingredients]
        if unknown:
            raise bad(f"모르는 재료 id: {', '.join(unknown)}")
        concepts = [i for i in ids if i in cat.snapshot.concept_ids]
        if concepts:
            raise bad(f"넓은 분류(concept)는 보유 재료로 쓸 수 없습니다: {', '.join(concepts)}")
        return ids

    def check_equipment(items: list[str]) -> list[str]:
        unknown = [e for e in items if e not in state.catalog.vocab["equipment"]]
        if unknown:
            raise bad(f"모르는 조리기구: {', '.join(unknown)}")
        return items

    def get_profile(profile_id: int) -> Profile:
        try:
            return store.get(profile_id)
        except ProfileNotFound:
            raise HTTPException(status_code=404, detail=f"프로필 {profile_id}이(가) 없습니다") from None

    def out(p: Profile) -> ProfileOut:
        names = state.catalog.names
        groups = state.catalog.groups
        return ProfileOut(
            id=p.id, display_name=p.display_name, skill_level=p.skill_level, household_size=p.household_size,
            preferences=[{"target_type": r.target_type, "target_id": r.target_id, "polarity": r.polarity,
                          "strength": r.strength, "is_hard": r.is_hard,
                          "name": names.get(r.target_id, r.target_id) if r.target_type == "ingredient"
                          else groups[r.target_id].display_name if r.target_type == "allergen_group"
                          and r.target_id in groups else r.target_id}
                         for r in p.preferences],
            allergen_groups=[{"id": r.target_id, "name": groups[r.target_id].display_name if r.target_id in groups
                              else r.target_id} for r in p.preferences if r.target_type == "allergen_group"],
            tastes=[{"dimension": t.dimension, "preferred_level": t.preferred_level, "max_level": t.max_level}
                    for t in p.tastes],
            pantry=[{"id": i, "name": names.get(i, i)} for i in p.pantry],
            equipment=list(p.equipment),
        )

    # --- 지식 조회 -----------------------------------------------------------------------------------

    @app.get("/health")
    def health() -> dict[str, Any]:
        cat = state.catalog
        return {"status": "ok", "source": cat.data.source, "recipes": len(cat.recipes),
                "ingredients": len(cat.ingredients), "knowledge_hash": cat.data.knowledge.source_hash[:12]}

    @app.get("/vocab")
    def vocab() -> dict[str, Any]:
        d = state.catalog.display
        return {"cuisines": list(state.catalog.vocab["cuisines"]), "equipment": list(state.catalog.vocab["equipment"]),
                "tastes": [{"dimension": k, "label": d["taste_labels"][k]} for k in TASTE_DIMENSIONS],
                "disclaimer": d["disclaimer"], "label_check": d["label_check"]}

    @app.get("/allergen-groups")
    def allergen_groups() -> list[dict[str, Any]]:
        return state.catalog.allergen_groups()

    @app.get("/ingredients/search")
    def search_ingredients(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100),
                           include_concepts: bool = False) -> list[dict[str, Any]]:
        return state.catalog.search(q, limit=limit, include_concepts=include_concepts)

    @app.get("/graph")
    def graph(request: Request, response: Response, recipes: RecipeScope = "published",
              max_recipes: int | None = Query(None, ge=0)) -> Any:
        """3D 시각화용 노드·간선(부록 D). 데이터가 바뀌지 않으면 ETag가 같아 304로 응답한다."""
        body, etag = state.graph.graph(recipes, max_recipes)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        response.headers["ETag"] = etag
        return body

    # --- 프로필 ---------------------------------------------------------------------------------------

    @app.get("/profiles", response_model=list[ProfileOut])
    def list_profiles() -> list[ProfileOut]:
        return [out(p) for p in store.list()]

    @app.post("/profiles", response_model=ProfileOut, status_code=201)
    def create_profile(body: ProfileCreate) -> ProfileOut:
        try:
            return out(store.create(body.display_name, body.skill_level, body.household_size))
        except DuplicateProfileName:
            raise HTTPException(status_code=409, detail=f"이미 있는 이름입니다: {body.display_name}") from None

    @app.get("/profiles/{profile_id}", response_model=ProfileOut)
    def read_profile(profile_id: int) -> ProfileOut:
        return out(get_profile(profile_id))

    @app.patch("/profiles/{profile_id}", response_model=ProfileOut)
    def update_profile(profile_id: int, body: ProfileUpdate) -> ProfileOut:
        get_profile(profile_id)
        patch = ProfilePatch(
            display_name=body.display_name, skill_level=body.skill_level, household_size=body.household_size,
            tastes=None if body.tastes is None else [TasteRow(t.dimension, t.preferred_level, t.max_level)
                                                     for t in body.tastes],
            pantry=None if body.pantry is None else check_pantry(body.pantry),
            equipment=None if body.equipment is None else check_equipment(body.equipment),
        )
        try:
            return out(store.update(profile_id, patch))
        except DuplicateProfileName:
            raise HTTPException(status_code=409, detail=f"이미 있는 이름입니다: {body.display_name}") from None

    @app.put("/profiles/{profile_id}/preferences", response_model=ProfileOut)
    def save_preferences(profile_id: int, body: PreferencesIn) -> ProfileOut:
        get_profile(profile_id)
        cat = state.catalog
        for p in body.preferences:
            if p.target_type == "ingredient" and p.target_id not in cat.ingredients:
                raise bad(f"모르는 재료 id: {p.target_id}")
            if p.target_type == "allergen_group" and p.target_id not in cat.groups:
                raise bad(f"모르는 알레르기 그룹 id: {p.target_id}")
            if p.target_type == "cuisine" and p.target_id not in cat.vocab["cuisines"]:
                raise bad(f"모르는 음식 종류: {p.target_id}")
        rows = [PreferenceRow(p.target_type, p.target_id, p.polarity, p.strength, p.is_hard) for p in body.preferences]
        return out(store.update(profile_id, ProfilePatch(preferences=rows)))

    @app.delete("/profiles/{profile_id}", status_code=204)
    def delete_profile(profile_id: int) -> None:
        get_profile(profile_id)
        store.delete(profile_id)

    # --- 추천 -----------------------------------------------------------------------------------------

    def log_exclusions(profile_id: int | None, result: RecommendResult, persona_id: str | None = None) -> None:
        path = exclusion_log
        if path is None or not result.exclusions:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        subject: dict[str, Any] = {"profile_id": profile_id}
        if persona_id is not None:
            subject["persona_id"] = persona_id
        with path.open("a", encoding="utf-8") as fh:
            for e in result.exclusions:
                fh.write(json.dumps({
                    "ts": ts, **subject, "recipe_id": e.recipe_id, "reason": e.reason.value,
                    "ingredient_id": e.ingredient_id, "target": e.target, "certainty": e.certainty,
                    "via": list(e.via), "detail": e.detail,
                }, ensure_ascii=False) + "\n")

    @app.get("/personas")
    def list_personas() -> list[dict[str, Any]]:
        """골든셋 페르소나(시각화의 프로필 선택용, 부록 D-3)."""
        names = state.catalog.names
        groups = state.catalog.groups
        return [{
            "id": p.id, "name": p.name, "description": p.description, "skill_level": p.user.skill_level,
            "allergen_groups": [{"id": g, "name": groups[g].display_name if g in groups else g}
                                for g in sorted(p.user.allergen_groups)],
            "pantry": [{"id": i, "name": names.get(i, i)} for i in sorted(p.user.pantry)],
            "equipment": sorted(p.user.equipment), "max_time_min": p.request.max_time_min,
        } for p in persona_index.values()]

    @app.post("/recommend")
    def recommend(body: RecommendIn) -> dict[str, Any]:
        if body.persona_id is not None:
            persona = persona_index.get(body.persona_id)
            if persona is None:
                raise HTTPException(status_code=404, detail=f"페르소나 {body.persona_id}이(가) 없습니다")
            profile_id, user = None, persona.user
            max_time = body.max_time_min if body.max_time_min is not None else persona.request.max_time_min
            time_is_hard = body.time_is_hard or persona.request.time_is_hard
        else:
            assert body.profile_id is not None
            profile = get_profile(body.profile_id)
            profile_id, user = profile.id, user_context(profile)
            max_time, time_is_hard = body.max_time_min, body.time_is_hard
        pantry = None if body.pantry is None else frozenset(check_pantry(body.pantry))
        req = RecommendRequest(max_time_min=max_time, time_is_hard=time_is_hard, pantry=pantry, limit=body.limit)
        with state.lock:
            recommender, catalog, graph = state.recommender, state.catalog, state.graph
        try:
            if body.trace:
                result, trace = recommender.trace(user, req)
            else:
                result, trace = recommender.recommend(user, req), None
        except ValueError as exc:  # 모르는 알레르기 그룹·재료 id 등(1-1 승인: 400)
            raise bad(str(exc)) from None
        log_exclusions(profile_id, result, body.persona_id)
        out: dict[str, Any] = {
            "profile_id": profile_id,
            "items": [catalog.item(i, has_allergy=bool(user.allergen_groups)) for i in result.items],
            "exclusion_summary": catalog.exclusion_summary(result),
            "excluded_total": len({e.recipe_id for e in result.exclusions}),
            "disclaimer": catalog.display["disclaimer"],
        }
        if body.persona_id is not None:
            out["persona_id"] = body.persona_id
        if trace is not None:
            out["trace"] = graph.trace(result, trace, weights=dict(recommender.scoring.weights),
                                       labels=catalog.display["exclusion_labels"], limit=req.limit)
        return out

    @app.post("/admin/reload")
    def reload() -> dict[str, Any]:
        state.reload()
        return health()

    return app


def default_app() -> FastAPI:
    """uvicorn --factory 진입점. 환경변수(.env 포함)로 구성한다."""
    from sqlalchemy import create_engine

    from storage.engine_source import load_db, load_files
    from storage.settings import database_url
    from storage.users import SqlUserStore

    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL이 없습니다(.env 확인). 프로필 저장에 DB가 필요합니다.")
    engine = create_engine(url)
    source = os.environ.get("ENGINE_SOURCE", "db")

    def loader() -> EngineData:
        if source == "files":
            return load_files(ROOT)
        with engine.connect() as conn:
            return load_db(conn)

    log = Path(os.environ.get("EXCLUSION_LOG", ROOT / "logs" / "exclusions.jsonl"))
    return create_app(loader, SqlUserStore(engine), exclusion_log=log)
