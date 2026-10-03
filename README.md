# 레시피 추천 엔진 (MVP v1)

사용자 선호(요리 실력, 음식 종류, 맛, 알레르기, 식재료)와 보유 식재료를 반영해 레시피를 추천하는 엔진입니다.
Phase 0(기반 설계)과 Phase 1(MVP)까지 구현되어 있습니다(태그 `mvp-v1`). LLM 연동은 Phase 2부터입니다.

## 무엇이 들어 있나

- **지식 원본** `knowledge/*.yaml`(식재료 252개, 알레르기 그룹: 법정 19 + 자체 4 + 묶음 4) → `scripts/compile_knowledge.py`가 DB 테이블과 `allergen_closure`로 컴파일. 요청 처리 중에는 그래프 탐색 없이 조회만 합니다.
- **추천 엔진** `engine/`(순수 Python): 후보 → 제약 필터(알레르기는 감점이 아니라 제외) → 점수(I·K·T·P·D·M) → 다양성 보정 → 설명.
- **레시피** `data/recipes/*.yaml` 50개(사람 검수 완료).
- **API** `api/`(FastAPI), **화면** `app/`(Streamlit), **성능 측정** `scripts/bench.py`.
- **테스트**: 알레르기 회귀(`tests/allergy/`, 수정 금지), 로직, 골든셋(상위 3개 적중률 0.85 미만이면 실패), API, DB 통합.

## 문서

| 파일 | 내용 |
| --- | --- |
| `docs/plan.md` | 설계 기준(데이터 모델, 추천 로직, 테스트, 로드맵) |
| `docs/decisions.md` | 사람이 정한 결정사항 |
| `docs/progress.md` | 단계별 진행 기록, 측정 결과, Phase 2 이후 할 일 |
| `docs/review/` | 식재료·레시피 검수표, 골든셋 평가표 |
| `CLAUDE.md`, `PROMPTS.md` | 에이전트 작업 규칙과 단계별 지시문 |
| `knowledge/README.md`, `data/recipes/README.md` | 지식·레시피 YAML 형식 |

> 이 엔진의 알레르기 판정은 데이터에 의존합니다. 실제 식품 성분은 제품마다 다르므로, 화면 하단에 면책 문구를 두고, 알레르기 설정이 있는 사용자에게는 가공품 중 정보 확신이 낮은 재료가 든 레시피에 "제품 성분표를 확인하세요"를 표시합니다.

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

### 6-1. 3D 지식 그래프 (시각화, 부록 D)

API를 띄운 상태에서 브라우저로 `http://127.0.0.1:8000/viz`를 엽니다(별도 빌드 없음, three.js·3d-force-graph는 jsDelivr CDN에서 받으므로 인터넷 연결 필요).

- 4층 배치: 1층 알레르기 그룹(법정·자체·묶음), 2층 원천 재료·분류, 3층 가공품(derived_from이 있는 재료), 4층 레시피.
- 드래그 회전, 휠 확대, 우클릭 드래그 이동. 노드를 클릭하면 연결된 관계만 강조하고 오른쪽에 정보를 표시합니다(빈 곳 클릭 또는 Esc로 해제).
- 위쪽 검색창에서 재료 이름·별칭·레시피 제목을 찾으면 해당 노드로 카메라가 이동합니다. 층·간선 종류는 체크박스로 켜고 끕니다(레시피-재료 간선은 기본으로 숨김).
- API: `GET /graph?recipes=published|all|none&max_recipes=N`(노드·간선), `GET /personas`, `POST /recommend`의 `persona_id`·`trace` 옵션.

실행 순서(PowerShell, 저장소 루트):

```powershell
docker compose up -d --wait                                   # DB (위 2~4를 한 번 해 둔 상태)
uv run python scripts/seed_demo_profiles.py                   # 시연 프로필 3개(있으면 건너뜀)
uv run uvicorn api.main:default_app --factory --port 8000     # API
start http://127.0.0.1:8000/viz                               # 브라우저 열기
```

DB 없이 보려면 `$env:ENGINE_SOURCE = "files"`로 knowledge·레시피를 파일에서 읽습니다(저장 프로필 목록은 DB가 있어야 보임, 골든셋 페르소나는 항상 보임). 창이 가려져 있으면 브라우저가 그리기를 멈추므로 화면을 보이는 상태로 둡니다.

추천 과정 재생: 오른쪽 "추천 과정 재생"에서 프로필을 고르고 "추천 과정 보기" → 단계 번호(1~6), 이전/다음, 자동재생. 3단계에서 제외 레시피 행을 클릭하면 그 레시피의 경로만 보이고(다시 클릭하면 전체), 4·5단계에서 라벨이 겹치면 순위가 높은 것만 보이며 나머지는 레시피에 마우스를 올리면 보입니다.

#### 시연 순서

| 순서 | 프로필 | 단계 | 클릭·확인할 것 |
| --- | --- | --- | --- |
| 1 | 시연: 새우 알레르기 | 1 | 보유 재료 5개(배추김치·돼지고기·두부·계란·대파)가 초록으로 커짐, 기본 양념은 흐린 초록 |
| 2 | 〃 | 3 | 제외 4개가 빨갛게 가라앉음. 목록에서 **돼지고기 김치찌개** 행 클릭 → 배추김치 → 새우젓 → 새우 → 새우 그룹 경로로 빛이 이동(포함 가능). **계란찜** 행 클릭 → 새우젓(선택 재료) → 새우 경로(선택 재료도 제외) |
| 3 | 〃 | 4·5 | 남은 12개가 점수만큼 올라감, 5단계 순위 라벨(계란말이 1위 등). 숨은 라벨은 마우스 오버 |
| 4 | 〃 | 6 | 추천 카드(항목별 점수, 부족 재료, 대체 안내) |
| 5 | 시연: 매운 것 못 먹음 | 3 | 매운맛 한도 1: 제육볶음·돼지고기 김치찌개·오징어볶음·두부조림·마파두부가 **회색**으로 가라앉음(알레르기 빨강과 구분). 레시피에 마우스 → "매운맛 3 > 한도 1" |
| 6 | 〃 | 6 | 남은 4개(된장찌개·고추잡채 등) 추천 |
| 7 | 시연: 견과류 알레르기 | 3 | **멸치볶음** 행 클릭 → 아몬드(선택) → 기타 견과류 ⊂ 견과류(묶음) 경로. 감자 그라탕은 오븐 없음(회색, 조리기구) |
| 8 | (아무 프로필) | — | 재생을 끝내고 멸치볶음 노드 클릭 → 정보 패널 "걸리는 알레르기"에 기타 견과류(선택 재료 때문) 표시 |

### 7. 성능 측정

```powershell
uv run python scripts/bench.py       # 합성 레시피 1만 개, 요청 300회: p50/p95 출력 (기준 p95 200ms 이하)
uv run python scripts/bench.py --trace   # trace() 생성과 표시 변환이 응답 시간에 주는 영향
uv run python scripts/bench.py --recipes 1000 --graph-out viz/_bench/graph_1000.json
# → API 실행 중 http://127.0.0.1:8000/viz?graph=/viz/static/_bench/graph_1000.json (HUD에 로딩 시간·fps)
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
