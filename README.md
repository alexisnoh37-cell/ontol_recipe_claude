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

DB를 처음부터 다시 만들려면 `docker compose down -v` 후 위 두 줄을 다시 실행합니다.

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

### 4. 테스트

```powershell
uv run pytest                        # 전체
uv run pytest tests/kb               # 지식 컴파일러
```

`tests/allergy/`(알레르기 회귀 테스트)는 엔진을 구현하는 Phase 1-1 전까지 모두 실패하는 것이 정상입니다. 그 외 테스트만 보려면 `uv run pytest --ignore=tests/allergy`를 씁니다.

`tests/storage/`(DB 통합 테스트)는 `.env`에 `TEST_DATABASE_URL`이 있을 때만 실행되고, 없으면 skip됩니다.
이 테스트는 `recipe_test` DB의 테이블을 지우고 다시 만들므로 개발 DB(`DATABASE_URL`)와 다른 DB를 가리켜야 합니다.

### 참고

- Git Bash에서 한글 출력이 깨지면 `PYTHONUTF8=1`을 설정하거나 PowerShell을 쓰세요.
- 디렉터리 구조와 설계는 `docs/plan.md` 부록 A~C, 지식 YAML 형식은 `knowledge/README.md`를 봅니다.
