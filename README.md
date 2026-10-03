# 레시피 추천 엔진 — 시작 키트

Claude Code로 레시피 추천 엔진 MVP를 구축하기 위한 지시문과 참고 파일 묶음입니다.

## 사용 순서

1. 이 폴더를 원하는 위치에 두고 Git 저장소로 만듭니다.
2. `docs/decisions.md`의 결정 5가지를 채웁니다.
3. `PROMPTS.md`를 열고 "시작 전 준비"부터 순서대로 진행합니다. 단계마다 새 Claude Code 세션에 지시문을 붙여넣습니다.

## 파일 안내

| 파일 | 누가 읽나 | 내용 |
| --- | --- | --- |
| `PROMPTS.md` | 나 | 단계별로 Claude Code에 붙여넣을 지시문과 확인할 것 |
| `CLAUDE.md` | 에이전트 | 매 세션 자동으로 읽는 작업 규칙(안전 규칙, 범위, 보고 방식) |
| `AGENTS.md` | 에이전트(Codex) | CLAUDE.md를 따르라는 안내 |
| `docs/plan.md` | 둘 다 | 구현 계획서(데이터 모델, 추천 로직, 테스트, 로드맵) |
| `docs/decisions.md` | 나 → 에이전트 | 시작 전에 내가 정하는 5가지 |
| `docs/progress.md` | 에이전트 → 나 | 단계별 진행 기록. 세션이 바뀌어도 이어서 작업하는 기준 |
| `knowledge/` | 둘 다 | 식재료 지식 원본 형식과 예시(숨은 알레르기 가공품 포함) |
| `config/` | 둘 다 | 점수 가중치 초기값, 기본 양념 목록 |

## 이 구축이 끝나면

- Streamlit 화면에서 프로필과 보유 재료를 넣으면 추천 결과와 이유가 나옵니다.
- 알레르기 회귀 테스트, 로직 테스트, 골든셋 평가, 성능 측정이 모두 자동으로 돌아갑니다.
- Phase 2(LLM 자연어 입력과 설명) 이후 할 일이 `docs/progress.md`에 정리됩니다.

> 이 엔진의 알레르기 판정은 데이터에 의존합니다. 실제 식품 성분은 제품마다 다르므로, 화면에 "제품 성분표를 확인하세요" 안내를 반드시 둡니다.

## 실행 방법 (Windows 기준)

PowerShell에서 저장소 루트 기준으로 실행합니다. macOS·Linux도 명령은 같고 `copy` 대신 `cp`를 씁니다.

### 1. 준비 (처음 한 번)

```powershell
winget install astral-sh.uv          # 또는: pip install uv
uv sync                              # .python-version(3.12)의 파이썬과 의존성을 .venv에 설치
copy .env.example .env               # DB 포트·계정을 바꾸려면 .env를 수정
```

로컬에 이미 PostgreSQL이 5432 포트를 쓰고 있으면 `.env`의 `POSTGRES_PORT`와 두 URL의 포트를 함께 바꿉니다(예: 5433).

### 2. DB 띄우기와 마이그레이션

Docker Desktop을 켠 뒤:

```powershell
docker compose up -d --wait          # PostgreSQL 16 (처음 만들 때 테스트용 recipe_test DB도 생성)
uv run alembic upgrade head          # 스키마 생성 (docs/plan.md 부록 B)
```

저장소를 새로 받은 뒤(새 마이그레이션이 추가되었을 수 있음)에도 `uv run alembic upgrade head`를 먼저 실행합니다. DB를 처음부터 다시 만들려면 `docker compose down -v` 후 위 두 줄을 다시 실행합니다.

### 3. 지식 컴파일

```powershell
uv run python scripts/compile_knowledge.py --dry-run                       # 검증·리포트만 (DB 불필요)
uv run python scripts/compile_knowledge.py --dry-run --dump build/knowledge.json   # 결과 JSON 저장
uv run python scripts/compile_knowledge.py                                 # DB 반영
uv run python scripts/validate_data.py                                     # 지식 + 레시피 검증
uv run python scripts/validate_data.py --db                                # + DB의 보유 재료·선호 검증
```

`knowledge/*.yaml`이나 `config/pantry_staples.yaml`을 고친 뒤에는 항상 다시 컴파일합니다. DB의 지식 테이블은 직접 고치지 않습니다.
검증 오류가 하나라도 있으면 종료 코드 1로 끝나고 DB는 바뀌지 않습니다.

### 4. 레시피 시드 적재와 검수표

```powershell
uv run python scripts/load_recipes.py --dry-run      # 레시피 검증만 (DB 불필요)
uv run python scripts/load_recipes.py                # 검증 후 DB 반영 (지식을 먼저 컴파일해 둘 것)
uv run python scripts/load_recipes.py --prune        # 시드에 없는 DB 레시피도 삭제
uv run python scripts/make_recipe_review.py          # docs/review/recipes_review.md 다시 만들기
uv run python scripts/make_review.py                 # docs/review/ingredients_review.md 다시 만들기
```

레시피 시드는 `data/recipes/<id>.yaml`(파일 하나에 레시피 하나, 형식은 `data/recipes/README.md`)이 원본입니다.
시드나 지식을 고친 뒤에는 검수표를 다시 만듭니다(최신이 아니면 테스트가 실패합니다).
엔진은 기본적으로 published 레시피만 추천합니다. 검수 전(draft) 레시피를 보려면 `config/engine.yaml`의 `serve_draft_recipes`를 `true`로 바꿉니다.

### 5. API 실행 (FastAPI)

새 PowerShell 창에서(저장소 루트):

```powershell
uv run uvicorn api.main:default_app --factory --port 8000
```

- 시작할 때 DB의 컴파일 결과·레시피를 읽어 엔진을 만듭니다. 지식을 재컴파일하거나 레시피를 다시 적재한 뒤에는 API를 재시작하거나 `Invoke-RestMethod -Method Post http://127.0.0.1:8000/admin/reload`를 실행합니다.
- 브라우저에서 `http://127.0.0.1:8000/docs`를 열면 엔드포인트를 직접 호출해 볼 수 있습니다.
  - `POST /profiles`, `PATCH /profiles/{id}`(기본 정보·맛·보유 재료·조리기구), `PUT /profiles/{id}/preferences`(음식 종류·재료 선호, 알레르기)
  - `POST /recommend`, `GET /ingredients/search?q=달걀`(별칭 검색), `GET /allergen-groups`(법정/자체/묶음 구분), `GET /vocab`
- 제외된 레시피의 사유는 `logs/exclusions.jsonl`에 한 줄씩 쌓입니다(경로는 환경변수 `EXCLUSION_LOG`).
- DB 없이 지식·레시피를 파일에서 직접 읽으려면 `$env:ENGINE_SOURCE = "files"` 후 실행합니다(프로필 저장에는 여전히 DB가 필요).

### 6. 화면 실행 (Streamlit)

API를 띄운 상태에서 또 다른 PowerShell 창에서:

```powershell
uv run streamlit run app/main.py
```

브라우저가 `http://localhost:8501`로 열립니다. 왼쪽에서 프로필을 만들고, "프로필·선호 편집" 탭에서 보유 재료(별칭 검색)와 맛·선호를, "알레르기" 탭에서 알레르기를 저장한 뒤 "추천" 탭에서 추천을 받습니다. API 주소가 다르면 `$env:API_URL = "http://127.0.0.1:8000"`.

### 7. 성능 측정

```powershell
uv run python scripts/bench.py       # 합성 레시피 1만 개, 요청 300회: p50/p95 출력 (기준 p95 200ms 이하)
```

### 전체 실행 순서 요약 (Windows, 처음부터)

```powershell
docker compose up -d --wait                          # 1. DB
uv run alembic upgrade head                          # 2. 마이그레이션
uv run python scripts/compile_knowledge.py           # 3. 지식 컴파일
uv run python scripts/load_recipes.py                # 4. 레시피 적재
uv run uvicorn api.main:default_app --factory --port 8000   # 5. API (창 1)
uv run streamlit run app/main.py                     # 6. 화면 (창 2)
```

### 8. 테스트

```powershell
uv run pytest                        # 전체
uv run pytest tests/kb               # 지식 컴파일러
uv run pytest tests/api              # API (DB 없이 메모리 저장소로)
uv run python scripts/eval_golden.py # 골든셋 상위 3개 적중률(0.85 미만이면 tests/golden 실패)
```

`tests/allergy/`(알레르기 회귀 테스트)는 Phase 1-1부터 전부 통과해야 합니다. 하나라도 실패하면 배포하지 않습니다. 알레르기 테스트만 돌리려면 `uv run pytest tests/allergy`를 씁니다.

`tests/storage/`(DB 통합 테스트)는 `.env`에 `TEST_DATABASE_URL`이 있을 때만 실행되고, 없으면 skip됩니다.
이 테스트는 `recipe_test` DB의 테이블을 지우고 다시 만들므로 개발 DB(`DATABASE_URL`)와 다른 DB를 가리켜야 합니다.

### 참고

- Git Bash에서 한글 출력이 깨지면 `PYTHONUTF8=1`을 설정하거나 PowerShell을 쓰세요.
- 디렉터리 구조와 설계는 `docs/plan.md` 부록 A~C, 지식 YAML 형식은 `knowledge/README.md`를 봅니다.
