"""추천 v2 API (docs/plan.md 부록 G-6, decisions D7). 기존 앱(api/main.py)을 바꾸지 않고 감싸서 경로만 더한다.

실행(저장소 루트): uv run uvicorn api.v2:default_app --factory --port 8000
  - 기존 경로(/recommend, /browse, /viz 등)는 그대로이고 POST /v2/recommend, GET /v2/info가 더해진다.
  - Jev 재정렬은 .env의 TYPESAFE_API_KEY가 있을 때만 켜진다(없으면 규칙 순위, note rerank_off).
제외된 레시피는 v1과 같은 로그 파일에 "engine": "v2"로 남긴다.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import Field, model_validator

from api.main import create_app, user_context
from api.schemas import Strict
from engine.model import RecommendResult, UserContext
from engine.recommend import Recommender
from engine.v2.config import V2Config, load_v2_config
from engine.v2.model import V2Request, V2Result
from engine.v2.ports import Reranker
from engine.v2.profile import SimpleProfile
from engine.v2.recommend import RecommenderV2
from storage.engine_source import CONFIG_DIR, ROOT, EngineData
from storage.personas import Persona, load_personas
from storage.personas_v2 import V2Persona, load_v2_personas
from storage.users import ProfileNotFound, UserStore


class SimpleProfileIn(Strict):
    """다른 앱이 저장하는 6가지 사용자 정보(docs/plan.md 부록 G-11). 재료는 재료 id(GET /ingredients/search)."""

    allergens: list[str] = []  # 알레르기 그룹 id(GET /allergen-groups): 들어 있을 수도 있는 재료까지 제외
    never_eat: list[str] = []  # 절대 안 먹는 재료: 확실히 들어간 재료만 제외
    likes: list[str] = []  # 좋아하는 재료: 점수 가산
    dislikes: list[str] = []  # 싫어하는 재료: 점수 감산(제외 안 함)
    spicy_level: Annotated[int, Field(ge=0, le=5)] | None = None  # 매운맛 정도(넘으면 제외, 5는 한도 없음)
    cuisine_likes: list[str] = []
    cuisine_dislikes: list[str] = []
    skill_level: Annotated[int, Field(ge=1, le=3)] | None = None

    def to_profile(self) -> SimpleProfile:
        return SimpleProfile(frozenset(self.allergens), frozenset(self.never_eat), frozenset(self.likes),
                             frozenset(self.dislikes), self.spicy_level, frozenset(self.cuisine_likes),
                             frozenset(self.cuisine_dislikes), self.skill_level)


class V2RecommendIn(Strict):
    profile_id: int | None = None
    persona_id: str | None = None
    profile: SimpleProfileIn | None = None  # 다른 앱 연동: 사용자 정보를 요청에 바로 담는다(저장 안 함)
    mode: Literal["random", "pantry", "dish"]
    query: Annotated[str, Field(max_length=200)] | None = None  # dish 필수
    pantry: list[str] | None = None
    seed: Annotated[int, Field(ge=0)] | None = None
    rerank: bool | None = None  # 비우면 config/v2.yaml rerank.enabled
    max_time_min: Annotated[int, Field(gt=0)] | None = None
    time_is_hard: bool = False
    limit: Annotated[int, Field(ge=1, le=50)] | None = None

    @model_validator(mode="after")
    def _check(self) -> V2RecommendIn:
        if sum(x is not None for x in (self.profile_id, self.persona_id, self.profile)) != 1:
            raise ValueError("profile_id, persona_id, profile 중 정확히 하나를 주세요")
        if self.mode == "dish" and not (self.query and self.query.strip()):
            raise ValueError("요리 찾기(dish)에는 query가 필요합니다")
        return self


def jev_reranker_from_env(cfg: V2Config) -> Reranker | None:
    """인증키가 있으면 Jev 재정렬기, 없으면 None(규칙 순위)."""
    from integrations.jev import JevClient, JevReranker, api_key_from_env

    key = api_key_from_env()
    return JevReranker(JevClient(key, model=cfg.rerank_model)) if key else None


def create_v2_app(loader: Callable[[], EngineData], store: UserStore, *, config_dir: Path = CONFIG_DIR,
                  exclusion_log: Path | None = None, personas: Callable[[], list[Persona]] = load_personas,
                  reranker_factory: Callable[[V2Config], Reranker | None] = lambda cfg: None,
                  v2_personas: Callable[[], list[V2Persona]] = load_v2_personas) -> FastAPI:
    app = create_app(loader, store, config_dir=config_dir, exclusion_log=exclusion_log, personas=personas)
    state = app.state.engine_state
    cfg = load_v2_config(config_dir)
    display = (yaml.safe_load((config_dir / "v2.yaml").read_text(encoding="utf-8")) or {}).get("display") or {}
    reranker = reranker_factory(cfg)
    persona_index = {p.id: p for p in personas()}
    v2_persona_index = {p.id: p for p in v2_personas()}
    cache: dict[str, Any] = {}
    lock = threading.Lock()

    def v2_for(v1: Recommender) -> RecommenderV2:
        """v1 재적재(/admin/reload) 뒤에는 새 v1에 맞춰 다시 만든다."""
        with lock:
            if cache.get("v1") is not v1:
                cache["v1"], cache["v2"] = v1, RecommenderV2.from_v1(v1, cfg, reranker)
            return cache["v2"]

    def from_profile(profile: SimpleProfile) -> UserContext:
        """조리기구는 6가지 입력에 없으므로 모두 있다고 본다(기구 때문에 빠지는 레시피가 없게, G-11)."""
        cat = state.catalog
        unknown = sorted(i for i in profile.never_eat | profile.likes | profile.dislikes if i not in cat.ingredients)
        if unknown:
            raise HTTPException(status_code=400, detail=f"모르는 재료 id: {', '.join(unknown)}")
        cuisines = set(cat.vocab["cuisines"])
        unknown = sorted(c for c in profile.cuisine_likes | profile.cuisine_dislikes if c not in cuisines)
        if unknown:
            raise HTTPException(status_code=400, detail=f"모르는 음식 종류: {', '.join(unknown)}")
        try:
            return profile.to_user_context(equipment=cat.vocab["equipment"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    def subject(body: V2RecommendIn) -> tuple[int | None, UserContext, int | None, bool]:
        if body.profile is not None:
            return None, from_profile(body.profile.to_profile()), body.max_time_min, body.time_is_hard
        if body.persona_id is not None and body.persona_id in v2_persona_index:
            user = from_profile(v2_persona_index[body.persona_id].profile)
            return None, user, body.max_time_min, body.time_is_hard
        if body.persona_id is not None:
            persona = persona_index.get(body.persona_id)
            if persona is None:
                raise HTTPException(status_code=404, detail=f"페르소나 {body.persona_id}이(가) 없습니다")
            max_time = body.max_time_min if body.max_time_min is not None else persona.request.max_time_min
            return None, persona.user, max_time, body.time_is_hard or persona.request.time_is_hard
        assert body.profile_id is not None
        try:
            profile = store.get(body.profile_id)
        except ProfileNotFound:
            raise HTTPException(status_code=404, detail=f"프로필 {body.profile_id}이(가) 없습니다") from None
        return profile.id, user_context(profile), body.max_time_min, body.time_is_hard

    def log(profile_id: int | None, persona_id: str | None, result: V2Result) -> None:
        path = exclusion_log or ROOT / "logs" / "exclusions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        who: dict[str, Any] = {"profile_id": profile_id}
        if persona_id is not None:
            who["persona_id"] = persona_id
        with path.open("a", encoding="utf-8") as fh:
            for e in result.exclusions:
                fh.write(json.dumps({"ts": ts, "engine": "v2", "mode": result.mode, **who, "recipe_id": e.recipe_id,
                                     "reason": e.reason.value, "ingredient_id": e.ingredient_id, "target": e.target,
                                     "certainty": e.certainty, "via": list(e.via), "detail": e.detail},
                                    ensure_ascii=False) + "\n")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """API 주소를 브라우저로 열면 빈 Not Found 대신 API 문서(/docs)로 보낸다. 화면은 app/v2.py(Streamlit)."""
        return RedirectResponse("/docs")

    @app.get("/v2/info")
    def v2_info() -> dict[str, Any]:
        return {"modes": ["random", "pantry", "dish"], "rerank_available": reranker is not None,
                "rerank_default": cfg.rerank_enabled, "rerank_model": cfg.rerank_model,
                "near_max_missing": cfg.near_max_missing}

    @app.get("/v2/personas")
    def v2_personas_list() -> list[dict[str, Any]]:
        """직접 테스트용 페르소나(data/personas/v2_test_personas.yaml): 6가지 정보, 넣어 볼 재료·문장, 확인할 것."""
        cat = state.catalog
        groups = cat.groups
        named = lambda ids: [{"id": i, "name": cat.names.get(i, i)} for i in sorted(ids)]  # noqa: E731
        out = []
        for p in v2_persona_index.values():
            pr = p.profile
            out.append({
                "id": p.id, "name": p.name, "description": p.description,
                "allergens": [{"id": g, "name": groups[g].display_name if g in groups else g} for g in sorted(pr.allergens)],
                "never_eat": named(pr.never_eat), "likes": named(pr.likes), "dislikes": named(pr.dislikes),
                "spicy_level": pr.spicy_level, "cuisine_likes": sorted(pr.cuisine_likes),
                "cuisine_dislikes": sorted(pr.cuisine_dislikes), "skill_level": pr.skill_level,
                "try_pantry": named(p.try_pantry), "try_dish": list(p.try_dish), "checks": list(p.checks),
            })
        return out

    @app.post("/v2/recommend")
    def v2_recommend(body: V2RecommendIn) -> dict[str, Any]:
        profile_id, user, max_time, time_is_hard = subject(body)
        with state.lock:
            v1, catalog = state.recommender, state.catalog
        pantry = None
        if body.pantry is not None:
            unknown = [i for i in body.pantry if i not in catalog.ingredients]
            if unknown:
                raise HTTPException(status_code=400, detail=f"모르는 재료 id: {', '.join(unknown)}")
            pantry = frozenset(body.pantry)
        req = V2Request(mode=body.mode, query=body.query, pantry=pantry, seed=body.seed, rerank=body.rerank,
                        max_time_min=max_time, time_is_hard=time_is_hard, limit=body.limit)
        try:
            result = v2_for(v1).recommend(user, req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        log(profile_id, body.persona_id, result)
        labels = {**catalog.display["breakdown_labels"], **(display.get("breakdown_labels") or {})}
        notes_text = display.get("notes") or {}
        group_labels = display.get("group_labels") or {}
        items = []
        for it in result.items:
            out = catalog.item(it.item, has_allergy=bool(user.allergen_groups))
            out["breakdown"] = [{"key": k, "label": labels.get(k, k), "value": v} for k, v in it.item.breakdown.items()]
            out["group"] = it.group
            out["group_label"] = group_labels.get(it.group) if it.group else None
            out["required_missing_count"] = it.required_missing
            out["notes"] = out["notes"] + [notes_text.get(n, n) for n in it.notes]
            items.append(out)
        summary_src = RecommendResult(items=(), exclusions=result.exclusions, exclusion_summary=result.exclusion_summary)
        return {
            "mode": result.mode, "profile_id": profile_id, "persona_id": body.persona_id, "query": body.query,
            "seed": result.seed, "rerank_used": result.rerank_used, "rerank_model": result.rerank_model,
            "notes": [{"code": n, "text": notes_text.get(n, n)} for n in result.notes],
            "items": items,
            "exclusion_summary": catalog.exclusion_summary(summary_src),
            "excluded_total": len({e.recipe_id for e in result.exclusions}),
            "disclaimer": catalog.display["disclaimer"],
        }

    return app


def default_app() -> FastAPI:
    """uvicorn --factory 진입점(api.main.default_app과 같은 구성 + v2 경로 + Jev 재정렬)."""
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
    return create_v2_app(loader, SqlUserStore(engine), exclusion_log=log, reranker_factory=jev_reranker_from_env)
