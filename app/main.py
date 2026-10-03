"""Streamlit 화면 (Phase 1-5). API를 HTTP로만 호출한다(docs/plan.md 부록 A: app → api).

    uv run streamlit run app/main.py          # API_URL 기본값 http://127.0.0.1:8000

판정은 하지 않는다. 안내 문구·면책 문구는 API(config/display.yaml)가 내려준 것을 그대로 보여 준다.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
NO_VALUE = "미입력"

st.set_page_config(page_title="레시피 추천", page_icon="🍳", layout="wide")


# --- API 호출 --------------------------------------------------------------------------------------


def api(method: str, path: str, **kwargs: Any) -> Any:
    try:
        r = httpx.request(method, API_URL + path, timeout=30, **kwargs)
    except httpx.HTTPError as exc:
        st.error(f"API에 연결할 수 없습니다({API_URL}): {exc}. README의 'API 실행'을 먼저 하세요.")
        st.stop()
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        raise RuntimeError(f"{r.status_code}: {detail}")
    return None if r.status_code == 204 else r.json()


@st.cache_data(ttl=300)
def vocab() -> dict[str, Any]:
    return api("GET", "/vocab")


@st.cache_data(ttl=300)
def allergen_groups() -> list[dict[str, Any]]:
    return api("GET", "/allergen-groups")


def names() -> dict[str, str]:
    """화면에서 본 재료 id → 이름(검색 결과·프로필에서 모은다)."""
    return st.session_state.setdefault("names", {})


def remember(items: list[dict[str, Any]]) -> None:
    for x in items:
        names()[x["id"]] = x["name"]


def ingredient_picker(label: str, key: str, current: list[str], *, include_concepts: bool = False) -> list[str]:
    """별칭 검색 → 선택 목록에 추가. 선택 목록에서 지우면 빠진다. 반환: 선택된 재료 id 목록."""
    sel_key = f"{key}_selected"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = list(current)
    q = st.text_input(f"{label} 검색(이름·별칭, 예: 달걀, 다진마늘)", key=f"{key}_q")
    if q.strip():
        hits = api("GET", "/ingredients/search", params={"q": q, "include_concepts": include_concepts})
        remember(hits)
        if hits:
            def fmt(h: dict[str, Any]) -> str:
                extra = f" ← '{h['matched']}'" if h["matched"] != h["name"] else ""
                staple = " · 기본 양념(보유로 간주)" if h["is_pantry_staple"] else ""
                return f"{h['name']}{extra}{staple}"
            options = {h["id"]: fmt(h) for h in hits}
            cols = st.columns([4, 1])
            pick = cols[0].selectbox("검색 결과", list(options), format_func=options.get, key=f"{key}_pick")
            if cols[1].button("추가", key=f"{key}_add") and pick not in st.session_state[sel_key]:
                st.session_state[sel_key] = st.session_state[sel_key] + [pick]
        else:
            st.caption("일치하는 재료가 없습니다.")
    selected = st.multiselect(label, st.session_state[sel_key], default=st.session_state[sel_key],
                              format_func=lambda i: names().get(i, i), key=f"{key}_ms")
    st.session_state[sel_key] = selected
    return selected


# --- 사이드바: 프로필 선택·생성 ------------------------------------------------------------------------

st.sidebar.header("프로필")
profiles = api("GET", "/profiles")
for p in profiles:
    remember(p["pantry"])
by_id = {p["id"]: p for p in profiles}
if profiles:
    pid = st.sidebar.selectbox("프로필 선택", list(by_id), format_func=lambda i: by_id[i]["display_name"])
else:
    pid = None
    st.sidebar.info("프로필이 없습니다. 아래에서 만드세요.")

with st.sidebar.form("new_profile", clear_on_submit=True):
    new_name = st.text_input("새 프로필 이름")
    if st.form_submit_button("프로필 만들기") and new_name.strip():
        try:
            api("POST", "/profiles", json={"display_name": new_name.strip()})
            st.rerun()
        except RuntimeError as exc:
            st.sidebar.error(str(exc))

if pid is None:
    st.title("레시피 추천")
    st.caption(vocab()["disclaimer"])
    st.stop()

profile = by_id[pid]
if st.session_state.get("loaded_profile") != pid:  # 프로필이 바뀌면 편집 상태를 새로 만든다
    for k in [k for k in st.session_state if k.endswith("_selected") or k.endswith("_ms") or k.startswith("pref_")]:
        del st.session_state[k]
    st.session_state["loaded_profile"] = pid

st.title(f"레시피 추천 — {profile['display_name']}")
tab_rec, tab_profile, tab_allergy = st.tabs(["추천", "프로필·선호 편집", "알레르기"])
v = vocab()

# --- 프로필·선호 편집 --------------------------------------------------------------------------------

with tab_profile:
    st.subheader("기본 정보")
    c1, c2, c3 = st.columns(3)
    display_name = c1.text_input("이름", profile["display_name"])
    skill = c2.radio("요리 실력", [1, 2, 3], index=profile["skill_level"] - 1, horizontal=True,
                     format_func={1: "초급", 2: "중급", 3: "숙련"}.get)
    household = c3.number_input("가구 인원", 1, 20, profile["household_size"])
    equipment = st.multiselect("보유 조리기구", v["equipment"], default=profile["equipment"])

    st.subheader("맛 선호 (0~5)")
    st.caption("선호: 좋아하는 정도(점수에 반영). 한도: 먹을 수 있는 최대치(넘으면 제외). 매운맛 한도가 대표적입니다.")
    tastes_now = {t["dimension"]: t for t in profile["tastes"]}
    levels = [NO_VALUE, 0, 1, 2, 3, 4, 5]
    taste_rows = []
    for t in v["tastes"]:
        d, cur = t["dimension"], tastes_now.get(t["dimension"], {})
        a, b, c = st.columns([1, 2, 2])
        a.markdown(f"**{t['label']}**")
        pref = b.selectbox("선호", levels, key=f"pref_t_{d}_p",
                           index=levels.index(cur["preferred_level"]) if cur.get("preferred_level") is not None else 0)
        mx = c.selectbox("한도", levels, key=f"pref_t_{d}_m",
                         index=levels.index(cur["max_level"]) if cur.get("max_level") is not None else 0)
        if pref != NO_VALUE or mx != NO_VALUE:
            taste_rows.append({"dimension": d, "preferred_level": None if pref == NO_VALUE else pref,
                               "max_level": None if mx == NO_VALUE else mx})

    st.subheader("보유 재료")
    st.caption("소금·간장·식용유 같은 기본 양념은 입력하지 않아도 있는 것으로 봅니다.")
    pantry = ingredient_picker("보유 재료", "pantry", [x["id"] for x in profile["pantry"]])

    if st.button("기본 정보·맛·보유 재료 저장", type="primary"):
        try:
            api("PATCH", f"/profiles/{pid}", json={
                "display_name": display_name, "skill_level": skill, "household_size": int(household),
                "equipment": equipment, "tastes": taste_rows, "pantry": pantry})
            st.success("저장했습니다.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("음식 종류·재료 선호")
    prefs = profile["preferences"]
    for p in prefs:
        if p["target_type"] == "ingredient":
            names()[p["target_id"]] = p["name"]

    def ids(kind: str, cond) -> list[str]:
        return [p["target_id"] for p in prefs if p["target_type"] == kind and cond(p)]

    likes_c = st.multiselect("좋아하는 음식 종류", v["cuisines"], default=ids("cuisine", lambda p: p["polarity"] > 0))
    dislikes_c = st.multiselect("덜 좋아하는 음식 종류(감점)", v["cuisines"],
                                default=ids("cuisine", lambda p: p["polarity"] < 0 and not p["is_hard"]))
    hard_c = st.multiselect("절대 먹지 않는 음식 종류(제외)", v["cuisines"],
                            default=ids("cuisine", lambda p: p["is_hard"]))
    strength = st.slider("선호·불선호 강도", 0.1, 1.0,
                         float(next((p["strength"] for p in prefs if not p["is_hard"]), 0.8)), 0.1)
    likes_i = ingredient_picker("좋아하는 재료", "pref_like", ids("ingredient", lambda p: p["polarity"] > 0),
                                include_concepts=True)
    dislikes_i = ingredient_picker("덜 좋아하는 재료(감점)", "pref_dislike",
                                   ids("ingredient", lambda p: p["polarity"] < 0 and not p["is_hard"]),
                                   include_concepts=True)
    hard_i = ingredient_picker("절대 먹지 않는 재료(그 재료로 만든 가공품까지 제외)", "pref_hard",
                               ids("ingredient", lambda p: p["is_hard"]), include_concepts=True)

    if st.button("선호 저장", type="primary"):
        rows = [{"target_type": "cuisine", "target_id": c, "polarity": 1, "strength": strength} for c in likes_c]
        rows += [{"target_type": "cuisine", "target_id": c, "polarity": -1, "strength": strength} for c in dislikes_c]
        rows += [{"target_type": "cuisine", "target_id": c, "polarity": -1, "is_hard": True} for c in hard_c]
        rows += [{"target_type": "ingredient", "target_id": i, "polarity": 1, "strength": strength} for i in likes_i]
        rows += [{"target_type": "ingredient", "target_id": i, "polarity": -1, "strength": strength}
                 for i in dislikes_i]
        rows += [{"target_type": "ingredient", "target_id": i, "polarity": -1, "is_hard": True} for i in hard_i]
        rows += [{"target_type": "allergen_group", "target_id": g["id"]} for g in profile["allergen_groups"]]
        try:
            api("PUT", f"/profiles/{pid}/preferences", json={"preferences": rows})
            st.success("저장했습니다.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

# --- 알레르기 --------------------------------------------------------------------------------------

with tab_allergy:
    st.subheader("알레르기")
    st.caption("알레르기 성분이 들어가거나 들어갈 수 있는 레시피는 점수와 관계없이 추천에서 제외됩니다. "
               "선택 재료·고명도 포함합니다.")
    groups = allergen_groups()
    current = {g["id"] for g in profile["allergen_groups"]}
    chosen: list[str] = []
    for category, title in (("official", "법정 표시 대상(식품 알레르기 유발물질 표시 기준)"),
                            ("custom", "자체 그룹(법정 표시 대상 외)"),
                            ("bundle", "묶음(여러 그룹을 한 번에)")):
        items = [g for g in groups if g["category"] == category]

        def label(gid: str, items=items) -> str:
            g = next(x for x in items if x["id"] == gid)
            members = ", ".join(m["display_name"] for m in g["members"])
            return f"{g['display_name']} ({members})" if members else g["display_name"]

        chosen += st.multiselect(title, [g["id"] for g in items], default=[g["id"] for g in items if g["id"] in current],
                                 format_func=label, key=f"allergy_{category}")
    for g in groups:
        if g["id"] in chosen and g.get("notice"):
            st.info(f"{g['display_name']}: {g['notice']}")
    if st.button("알레르기 저장", type="primary"):
        rows = [{k: p[k] for k in ("target_type", "target_id", "polarity", "strength", "is_hard")}
                for p in profile["preferences"] if p["target_type"] != "allergen_group"]
        rows += [{"target_type": "allergen_group", "target_id": g} for g in chosen]
        try:
            api("PUT", f"/profiles/{pid}/preferences", json={"preferences": rows})
            st.success("저장했습니다.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

# --- 추천 ------------------------------------------------------------------------------------------

with tab_rec:
    allergy_names = ", ".join(g["name"] for g in profile["allergen_groups"]) or "없음"
    pantry_names = ", ".join(x["name"] for x in profile["pantry"]) or "없음(프로필·선호 편집 탭에서 입력)"
    st.markdown(f"**보유 재료**: {pantry_names}  \n**알레르기**: {allergy_names}")
    c1, c2, c3 = st.columns(3)
    max_time = c1.number_input("희망 조리시간(분, 0이면 제한 없음)", 0, 240, 0, 5)
    time_hard = c2.checkbox("시간을 넘는 레시피는 빼기", disabled=max_time == 0)
    limit = c3.number_input("추천 개수", 1, 30, 10)

    if st.button("추천 받기", type="primary"):
        try:
            st.session_state["result"] = api("POST", "/recommend", json={
                "profile_id": pid, "max_time_min": int(max_time) or None, "time_is_hard": bool(time_hard),
                "limit": int(limit)})
        except RuntimeError as exc:
            st.error(str(exc))
    result = st.session_state.get("result")
    if result and result.get("profile_id") == pid:
        if not result["items"]:
            st.warning("추천할 레시피가 없습니다. 보유 재료를 늘리거나 조건을 완화해 보세요.")
        for n, item in enumerate(result["items"], start=1):
            with st.container(border=True):
                head, score = st.columns([5, 1])
                head.markdown(f"### {n}. {item['title']}")
                head.caption(f"{item['cuisine']} · 난이도 {item['difficulty']} · 약 {item['cook_time_min']}분")
                score.metric("점수", f"{item['score']:.2f}")
                cols = st.columns(len(item["breakdown"]))
                for col, b in zip(cols, item["breakdown"]):
                    col.progress(min(max(b["value"], 0.0), 1.0), text=f"{b['label']} {b['value']:.2f}")
                if item["missing_text"]:
                    st.markdown(f"**부족한 재료**: {item['missing_text']}")
                for s in item["substitutions"]:
                    st.markdown(f"🔄 {s['text']}")
                for note in item["notes"]:
                    if not any(note == s["text"] for s in item["substitutions"]):
                        st.markdown(f"- {note}")
                for notice in item["notices"]:
                    st.warning(notice)
                if item["label_check"]:
                    check = item["label_check"]
                    st.warning(f"⚠️ {check['message']}: " + ", ".join(c["text"] for c in check["ingredients"]))
        if result["exclusion_summary"]:
            with st.expander(f"제외된 레시피 {result['excluded_total']}개 — 사유 요약"):
                for s in result["exclusion_summary"]:
                    ex = f" (예: {', '.join(s['examples'])})" if s["examples"] else ""
                    st.markdown(f"- **{s['label']}**: {s['count']}개{ex}")

st.divider()
st.caption("⚠️ " + v["disclaimer"])
