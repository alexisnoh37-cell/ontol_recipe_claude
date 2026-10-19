"""추천 v2 화면 (docs/plan.md 부록 G-6). 기존 화면(app/main.py)과 따로 띄운다. API를 HTTP로만 호출한다.

    uv run uvicorn api.v2:default_app --factory --port 8000   # v2 경로가 있는 API
    uv run streamlit run app/v2.py                             # API_URL 기본값 http://127.0.0.1:8000

판정은 하지 않는다. 알레르기·먹지 않는 재료 제외(규칙)와 Jev 판단(순위)은 API(엔진)가 한다.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="레시피 추천 v2", page_icon="🍲", layout="wide")


def api(method: str, path: str, **kwargs: Any) -> Any:
    try:
        r = httpx.request(method, API_URL + path, timeout=30, **kwargs)
    except httpx.HTTPError as exc:
        st.error(f"API에 연결할 수 없습니다({API_URL}): {exc}. 'uv run uvicorn api.v2:default_app --factory'를 먼저 실행하세요.")
        st.stop()
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        st.error(f"{r.status_code}: {detail}")
        st.stop()
    return r.json()


info = api("GET", "/v2/info")
st.title("🍲 레시피 추천 v2")
st.caption(
    f"Jev 판단: {'사용 가능(' + info['rerank_model'] + ')' if info['rerank_available'] else '꺼짐(TYPESAFE_API_KEY 없음)'}"
    " · 알레르기와 먹지 않는 재료는 Jev와 관계없이 규칙으로 먼저 제외합니다."
)

# --- 사용자 -------------------------------------------------------------------------------------------

st.sidebar.header("누구를 위한 추천인가요?")
profiles = api("GET", "/profiles")
personas = api("GET", "/personas")
test_personas = {p["id"]: p for p in api("GET", "/v2/personas")}
# 직접 테스트용 페르소나(6가지 정보)를 맨 앞에 둔다
choices: dict[str, dict[str, Any]] = {f"테스트: {p['name']}": {"persona_id": p["id"]} for p in test_personas.values()}
choices.update({f"프로필: {p['display_name']}": {"profile_id": p["id"]} for p in profiles})
choices.update({f"골든셋: {p['name']}": {"persona_id": p["id"]} for p in personas})
if not choices:
    st.warning("프로필이 없습니다. 기존 화면(app/main.py)에서 프로필을 만드세요.")
    st.stop()
who_label = st.sidebar.selectbox("사용자", list(choices))
who = choices[who_label]
rerank = st.sidebar.toggle("Jev가 순위 정하기", value=bool(info["rerank_available"] and info["rerank_default"]),
                           disabled=not info["rerank_available"])
limit = st.sidebar.slider("보여 줄 개수", 1, 30, 8)

SKILL = {1: "초보", 2: "보통", 3: "숙련", None: "모름(보통으로 계산)"}


def names_of(items: list[dict[str, Any]]) -> str:
    return ", ".join(x["name"] for x in items) or "없음"


persona = test_personas.get(who.get("persona_id", ""))
if persona:
    with st.expander(f"👤 {persona['name']} — 사용자 정보와 확인할 것", expanded=True):
        st.write(persona["description"])
        c1, c2 = st.columns(2)
        spicy = persona["spicy_level"]
        spicy_text = "모름" if spicy is None else f"{spicy} / 5" + (" (한도 없음)" if spicy == 5 else "")
        c1.markdown("  \n".join([
            "**못 먹는 것**",
            f"알레르기: {names_of(persona['allergens'])}",
            f"절대 안 먹음: {names_of(persona['never_eat'])}",
            f"**좋아하는 재료**: {names_of(persona['likes'])}",
            f"**싫어하는 재료**: {names_of(persona['dislikes'])}",
        ]))
        c2.markdown("  \n".join([
            f"**매운맛 정도**: {spicy_text}",
            f"**좋아하는 음식 종류**: {', '.join(persona['cuisine_likes']) or '없음'}",
            f"**덜 좋아하는 음식 종류**: {', '.join(persona['cuisine_dislikes']) or '없음'}",
            f"**요리 실력**: {SKILL.get(persona['skill_level'])}",
        ]))
        st.markdown(f"**넣어 볼 재료**: {names_of(persona['try_pantry'])}  \n"
                    f"**찾아 볼 문장**: {' / '.join(persona['try_dish'])}")
        st.markdown("**확인할 것**\n" + "\n".join(f"- {c}" for c in persona["checks"]))


def ingredient_pick(key: str) -> list[str]:
    """검색 → "추가"로 선택 목록에 넣는다. 선택 목록에서 지우면 빠진다. 반환: 선택된 재료 id.

    키가 있는 multiselect는 default가 바뀌어도 이전 값을 유지한다(Streamlit 1.64). 그래서 "추가"는 위젯 값
    (ms_key)을 직접 바꾸고, 위젯을 그리기 전에만 바꿀 수 있으므로 버튼 처리 → multiselect 순서를 지킨다(app/main.py와 같음).
    이름 표는 지우지 않고 쌓아 둔다. format_func가 None을 돌려주면 Streamlit이 TypeError를 낸다.
    """
    names: dict[str, str] = st.session_state.setdefault(f"{key}_names", {})
    ms_key = f"{key}_ms"
    st.session_state.setdefault(ms_key, [])
    q = st.text_input("재료 검색(예: 달걀, 김치, 두부)", key=f"{key}_q")
    if q.strip():
        hits = api("GET", "/ingredients/search", params={"q": q})
        if hits:
            opts = {h["id"]: h["name"] for h in hits}
            names.update(opts)
            cols = st.columns([4, 1])
            pick = cols[0].selectbox("검색 결과", list(opts), format_func=lambda i: opts.get(i, i), key=f"{key}_pick")
            cols[1].write("")  # 버튼을 입력 칸 높이에 맞춘다
            if cols[1].button("추가", key=f"{key}_add") and pick not in st.session_state[ms_key]:
                st.session_state[ms_key] = st.session_state[ms_key] + [pick]
        else:
            st.caption("일치하는 재료가 없습니다.")
    chosen = list(st.session_state[ms_key])
    return st.multiselect("내 재료", chosen, format_func=lambda i: names.get(i, i), key=ms_key)


def show(body: dict[str, Any]) -> None:
    for n in body["notes"]:
        st.info(n["text"])
    meta = [f"추천 {len(body['items'])}개", f"제외 {body['excluded_total']}개"]
    if body.get("seed") is not None:
        meta.append(f"seed {body['seed']}")
    if body["rerank_used"]:
        how = "Jev가 순위 결정" if body.get("ranking") == "jev" else "Jev 재정렬"
        meta.append(f"{how}({body['rerank_model']})")
    elif body.get("ranking") == "rules":
        meta.append("규칙 점수 순서")
    st.caption(" · ".join(meta))
    group = None
    for it in body["items"]:
        if it.get("group") != group and it.get("group_label"):
            group = it["group"]
            st.subheader(it["group_label"])
        with st.container(border=True):
            head = f"**{it['title']}**  ·  점수 {it['score']}"
            if it.get("cuisine"):
                head += f"  ·  {it['cuisine']}"
            st.markdown(head)
            bd = " · ".join(f"{b['label']} {b['value']}" for b in it["breakdown"])
            st.caption(bd)
            if it.get("missing_text"):
                st.markdown(f"🛒 {it['missing_text']}")
            for s in it["substitutions"]:
                st.markdown(f"🔄 {s['text']}")
            if it.get("label_check"):
                st.markdown(f"🔎 {it['label_check']['text']}")
            for n in it["notes"]:
                st.caption(f"· {n}")
    if body["exclusion_summary"]:
        with st.expander("제외된 레시피(사유별)"):
            for s in body["exclusion_summary"]:
                st.markdown(f"- {s['label']}: {s['count']}개 (예: {', '.join(s['examples'])})")
    st.caption(body["disclaimer"])


def request(payload: dict[str, Any]) -> None:
    body = api("POST", "/v2/recommend", json={**who, "rerank": rerank, "limit": limit, **payload})
    show(body)


tab_random, tab_pantry, tab_dish = st.tabs(["🎲 랜덤", "🧊 내 재료로", "🔍 요리 찾기"])

with tab_random:
    st.write("먹을 수 있는 레시피 중에서 무작위로 골라 드립니다.")
    if st.button("랜덤 추천", key="random_go"):
        request({"mode": "random"})

with tab_pantry:
    st.write("가진 재료로 **지금 바로** 만들 수 있는 레시피와 **조금만 사면** 되는 레시피를 나눠 보여 드립니다.")
    if persona and persona["try_pantry"] and st.button("이 페르소나의 '넣어 볼 재료' 채우기", key="pantry_fill"):
        st.session_state.setdefault("pantry_names", {}).update({x["id"]: x["name"] for x in persona["try_pantry"]})
        st.session_state["pantry_ms"] = [x["id"] for x in persona["try_pantry"]]
    pantry = ingredient_pick("pantry")
    if st.button("추천 받기", key="pantry_go", disabled=not pantry):
        request({"mode": "pantry", "pantry": pantry})

with tab_dish:
    st.write("요리 이름(예: 김치찌개)이나 느낌(예: 오늘은 얼큰한 국물이 끌려)으로 찾아 드립니다.")
    query = st.text_input("무엇이 먹고 싶나요?", key="dish_q")
    if st.button("찾기", key="dish_go", disabled=not query.strip()):
        request({"mode": "dish", "query": query})
