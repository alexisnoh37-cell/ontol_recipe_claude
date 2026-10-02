# 레시피 추천 엔진 — 작업 규칙

사용자 선호(요리실력, 음식 종류, 맛, 알레르기, 식재료)와 보유 식재료를 반영해 레시피를 추천하는 엔진의 MVP를 만든다.

## 반드시 먼저 읽을 문서

- `docs/plan.md` — 설계 기준(데이터 모델, 추천 로직, 테스트, 로드맵). 상세 사항은 모두 여기를 따른다.
- `docs/decisions.md` — 사람이 정한 결정사항. "미정"인 항목이 지금 작업에 영향을 주면 진행하지 말고 질문한다.
- `docs/progress.md` — 지금까지 진행 상황. 새 세션은 이 파일부터 읽고 이어서 작업한다.

이 파일은 어떤 작업에서도 지켜야 할 규칙이다. 규칙과 계획서가 충돌하면 이 파일이 우선한다.

## 이번 구축 범위

Phase 0(기반 설계)과 Phase 1(MVP)까지만 만든다. LLM 연동, 개인화, 장보기 등 Phase 2 이후 기능은 만들지 않는다. 필요해 보이면 docs/progress.md의 "다음 단계 제안"에 적기만 한다.

## 아키텍처 규칙

- 식재료 지식은 `knowledge/*.yaml`이 원본이다(온톨로지 역할). 형식은 `knowledge/README.md`와 예시 파일을 따른다.
- `scripts/compile_knowledge.py`가 지식 원본을 DB 테이블과 `allergen_closure`로 컴파일한다. DB의 관계 테이블을 직접 수정하지 않는다.
- 그래프 탐색(알레르기 확장, is_a 상속)은 컴파일 시점에만 한다. 요청 처리 중에는 재귀 탐색을 하지 않는다.
- 추천 엔진(`engine/`)은 FastAPI, DB 드라이버와 독립된 순수 Python 패키지로 둔다. 데이터는 인터페이스(리포지토리)를 통해 주입받는다.
- 가중치, 계수, 기본 양념 목록은 `config/*.yaml`에 둔다. 코드에 하드코딩하지 않는다.
- 모든 추천 응답에는 항목별 점수(breakdown)와 부족 재료, 대체 안내를 포함한다. 제외된 레시피는 제외 사유를 로그로 남긴다.

## 안전 규칙 (예외 없음)

- 알레르기 판정에 LLM이나 확률적 방법을 쓰지 않는다.
- 알레르기는 점수 감점이 아니라 제외로 처리한다. 선택(optional) 재료와 고명도 제외 대상이다.
- certainty가 "포함 가능"인 재료도 알레르기 판정에서는 포함으로 간주한다.
- 정규 ID로 매핑되지 않은 재료가 있는 레시피는 알레르기가 있는 사용자에게 제외한다.
- `tests/allergy/` 테스트는 사람이 승인한 뒤에는 수정하거나 삭제하거나 skip 처리하지 않는다. 테스트가 틀렸다고 판단되면 수정 대신 이유를 보고하고 멈춘다.
- 식재료, 알레르기, 레시피 데이터는 사람이 검수하기 전까지 `status: draft`로 둔다. 검수표에서 확신이 낮은 항목은 `confidence: low`로 표시한다.

## 작업 방식

- 지시받은 단계만 수행한다. 다음 단계를 미리 구현하지 않는다.
- 단계가 끝나면 멈추고 다음을 보고한다: 변경한 파일, 테스트 결과(통과/실패 수), 사람이 확인해야 할 것, 남은 문제.
- 보고 전에 `docs/progress.md`를 갱신한다(완료한 단계, 주요 결정, 알려진 문제, 다음 할 일).
- `docs/plan.md`와 다르게 구현해야 할 이유가 생기면 먼저 제안하고 승인받는다. 승인되면 `docs/plan.md`도 함께 수정한다.
- 단계가 끝날 때마다 커밋한다. 커밋 메시지는 `phase0-2: 지식 컴파일러 추가`처럼 단계 번호로 시작한다.
- 모르는 사실(식품 성분, 표시 기준 등)은 추측해서 확정하지 않는다. `confidence: low`로 표시하고 검수표에 올린다.

## 기술 스택

- Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, pytest, Streamlit
- PostgreSQL 16 (로컬은 docker compose, 운영은 Supabase 예정). DB 종속 문법은 PostgreSQL 기준으로 쓴다.
- 패키지 관리는 uv 또는 pip + requirements 중 Phase 0-1에서 제안해 확정한다.
- 개발 환경은 Windows일 수 있다. 스크립트는 OS에 독립적으로 작성하고(경로는 pathlib), 실행 방법은 README에 Windows 기준으로도 적는다.

## 권장 디렉터리 구조 (Phase 0-1에서 확정)

```
engine/        normalize.py, candidates.py, filters.py, scoring.py, explain.py
api/           FastAPI 앱
app/           Streamlit 화면
knowledge/     식재료·관계·알레르기 지식 원본(YAML)
data/recipes/  레시피 시드(YAML 또는 JSON)
config/        weights.yaml, pantry_staples.yaml
scripts/       compile_knowledge.py, validate_data.py, load_recipes.py, bench.py
migrations/    Alembic
tests/         allergy/, logic/, golden/
docs/          plan.md, decisions.md, progress.md, review/(검수표)
```

## 성능 기준

LLM을 제외한 엔진 응답 p95 200ms 이하(레시피 1만 개 합성 데이터 기준, `scripts/bench.py`로 측정).
