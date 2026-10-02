# Claude Code 단계별 지시문

각 단계마다 **새 세션**을 열고, 아래 "입력" 블록을 그대로 붙여넣습니다. 에이전트가 보고하고 멈추면 "내가 확인할 것"을 확인한 뒤 다음 단계로 넘어갑니다.

- `[필수]` 표시는 사람이 반드시 확인해야 다음 단계로 갈 수 있는 지점입니다.
- 설계와 검토 단계(0-1)는 Claude Code를 **Plan 모드**로 시작합니다(Shift+Tab으로 전환).

---

## 시작 전 준비 [필수]

1. Git, Python 3.11 이상, Docker Desktop, Claude Code를 설치합니다.
2. 이 폴더를 저장소로 만듭니다.
   ```
   cd recipe-engine-starter
   git init
   git add .
   git commit -m "init: 계획서와 작업 규칙"
   ```
3. `docs/decisions.md`의 D1~D5 "결정"을 채웁니다. 기본값을 쓰려면 `기본값`이라고만 적습니다.
4. Codex도 함께 쓸 경우 `AGENTS.md`가 같은 규칙을 가리킵니다.

---

## 0-1. 설계 확정 (Plan 모드) [필수]

**입력**
```
CLAUDE.md, docs/plan.md, docs/decisions.md, knowledge/README.md와 knowledge/*.example.yaml을 읽고
Phase 0 설계안만 제시해줘. 코드는 아직 쓰지 마.

1) 최종 디렉터리 구조와 패키지 관리 방식(uv 또는 pip)
2) PostgreSQL DDL 초안(docs/plan.md 3장 기준)
3) knowledge/ YAML 형식: 예시 형식을 그대로 쓸지, 바꿀 점이 있는지
4) compile_knowledge.py의 동작 순서(로드 → 검증 → 그래프 확장 → DB 반영)
5) 엔진이 DB 없이 테스트될 수 있게 하는 데이터 주입 방식
6) docs/plan.md와 decisions.md에서 모호하거나 서로 충돌하는 부분
```

**내가 확인할 것**
- 6번 "모호하거나 충돌하는 부분"에 답을 줍니다.
- 설계가 마음에 들면 "승인. docs/progress.md에 설계 결정을 기록하고 커밋해"라고 지시합니다.

---

## 0-2. 스키마와 지식 컴파일러

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 0-2를 진행해.
승인된 설계대로 다음을 만들어줘.
- docker-compose.yml(PostgreSQL 16)과 Alembic 마이그레이션
- knowledge/의 example 파일을 실제 파일(allergens.yaml, ingredients.yaml, substitutes.yaml)로 옮기기
- scripts/compile_knowledge.py: YAML 검증, 순환 검사, is_a·derived_from 확장, allergen_closure 생성, DB 반영
- scripts/validate_data.py: docs/plan.md 5-4의 검증 항목
- 컴파일러 단위 테스트: 새우젓이 shrimp closure에 들어가는지, 순환이 있으면 실패하는지
README에 Windows 기준 실행 방법을 적고, 끝나면 보고하고 멈춰.
```

**내가 확인할 것**
- 보고된 테스트가 모두 통과했는지, README대로 실행이 되는지만 확인합니다.

---

## 0-3. 알레르기 회귀 테스트 먼저 작성 [필수]

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 0-3을 진행해.
docs/plan.md 7-1의 알레르기 회귀 테스트를 tests/allergy/에 작성해.
엔진은 아직 없으니 엔진 인터페이스만 정의하고 테스트는 실패하는 상태로 둬.
테스트용 레시피와 사용자는 테스트 안의 fixture로 만들어.
각 테스트의 의도와 시나리오를 표로 보고하고, 내가 추가할 시나리오가 있는지 물어봐.
```

**내가 확인할 것**
- 시나리오 표를 보고 빠진 경우를 추가합니다. 예: "굴소스와 조개류", "고추장과 밀(포함 가능)".
- 승인하면 "승인. 이제 tests/allergy/는 수정 금지야. 커밋해"라고 지시합니다.

---

## 0-4. 식재료 200개 확장 [필수 · 검수 부담 큼]

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 0-4를 진행해.
knowledge/ingredients.yaml을 식재료 약 200개로 확장해줘.
- 한식 가정식에 자주 쓰는 재료 위주, 양식·일식·중식 기본 재료 일부
- 가공품은 derived_from 필수. docs/plan.md 5-2 체크리스트 항목은 모두 포함
- 별칭(aliases)을 충분히 넣고, 확실하지 않은 성분·관계는 confidence: low
- config/pantry_staples.yaml의 id가 모두 존재하게
그리고 docs/review/ingredients_review.md에 검수표를 만들어줘.
검수표는 confidence: low 항목을 맨 위에 모으고, 열은 id, 이름, 상위 개념, 파생 원천, 알레르기(상속 포함), 메모로 해.
compile_knowledge.py와 validate_data.py를 돌린 결과도 보고해.
```

**내가 확인할 것**
- `docs/review/ingredients_review.md`의 `confidence: low` 항목은 전부, 나머지는 훑어봅니다.
- 특히 액젓, 굴소스, 고추장, 된장, 카레가루, 어묵, 햄·소시지 같은 가공품의 원천 재료를 봅니다.
- 이 검수표를 Claude 앱의 별도 대화에 올려 교차 검토를 받으면 누락을 더 잘 잡습니다.
- 수정할 내용을 알려주고, 끝나면 "검수 완료. 확인한 항목 status를 reviewed로 바꾸고 커밋해"라고 지시합니다.

---

## 1-1. 필터 엔진

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 1-1을 진행해.
engine/에 입력 정규화(별칭 매핑), 후보 생성(동의어·상위 개념·대체재 매칭), 제약 필터를 구현해서
tests/allergy/를 모두 통과시켜. tests/allergy/는 수정하지 마.
요청 처리 중에는 재귀 탐색 없이 allergen_closure만 조회하도록 해.
제외된 레시피는 사유를 남기고, 끝나면 보고하고 멈춰.
```

**내가 확인할 것**
- 보고에 "tests/allergy 전부 통과"와 "테스트 파일 변경 없음"이 있는지 확인합니다. `git diff --stat tests/allergy`로 직접 확인해도 됩니다.

---

## 1-2. 점수 엔진 [선택]

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 1-2를 진행해.
docs/plan.md 4-4~4-6(점수 6개 항목, 구체성 우선 규칙, 다양성 보정)과 4-7(템플릿 설명)을 구현해.
가중치는 config/weights.yaml에서 읽어.
docs/plan.md 7-2의 로직 단위 테스트를 tests/logic/에 작성해서 통과시키고,
응답 예시 JSON 2개를 보고에 포함해.
```

**내가 확인할 것**
- 응답 예시의 점수 내역이 상식적인지 봅니다. 가중치 조정은 골든셋 이후에 해도 됩니다.

---

## 1-3. 레시피 시드 [필수 · 검수 부담 큼]

**입력**
```
CLAUDE.md와 docs/progress.md, docs/decisions.md D3을 읽고 Phase 1-3을 진행해.
data/recipes/에 레시피 50개를 만들어줘(한식 약 30, 일식·양식·중식 약 20).
- 재료는 knowledge의 id만 사용하고, 없는 재료는 먼저 knowledge에 추가 후 보고
- 재료마다 role(main/sub/seasoning/garnish)과 optional, raw_text
- 맛 강도 0~5, 난이도 1~3, 조리시간, 필수 조리기구
- 외부 레시피 본문을 복제하지 말고 일반적인 가정식 조리법으로 작성
scripts/load_recipes.py로 DB에 넣고, docs/review/recipes_review.md에 검수표를 만들어줘.
검수표 열: 제목, 종류, 난이도, 맛(매움/짠맛/단맛), 주재료, 선택재료, 걸리는 알레르기 그룹, confidence.
```

**내가 확인할 것**
- 매운맛 강도, 난이도, 주재료와 선택재료 구분이 상식에 맞는지 봅니다.
- "걸리는 알레르기 그룹" 열이 맞는지 봅니다. 김치가 들어간 레시피에 새우가 걸리는지가 대표 확인 포인트입니다.

---

## 1-4. 골든셋 [필수]

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 1-4를 진행해.
tests/golden/에 페르소나 8명 초안을 만들어줘.
페르소나마다 요리실력, 선호·불선호, 맛 선호와 매운맛 한도, 알레르기, 보유 재료 5~8개를 넣고,
"상위 3개 안에 나와야 할 레시피"는 비워 둔 채 현재 엔진의 상위 5개 결과를 옆에 보여줘.
평가 스크립트(상위 3개 적중률)도 만들고 멈춰.
```

**내가 확인할 것**
- 페르소나마다 "상위 3개 안에 나와야 할 레시피"를 직접 채웁니다. 이 판단은 에이전트에게 맡기지 않습니다.
- 채운 뒤 "골든셋 평가를 돌리고, 적중률이 낮은 페르소나는 원인을 점수 내역으로 설명해. 가중치 조정안은 제안만 해"라고 지시합니다.
- 조정안이 납득되면 승인합니다.

---

## 1-5. API, 화면, 성능

**입력**
```
CLAUDE.md와 docs/progress.md를 읽고 Phase 1-5를 진행해.
- FastAPI: 사용자 프로필 생성·수정, 선호 저장, POST /recommend, GET /ingredients/search?q= (별칭 검색)
- Streamlit: 프로필 선택·편집, 보유 재료 자동완성 입력, 추천 결과 카드(점수 내역, 부족 재료, 대체 안내, 알레르기 안내 문구)
- scripts/bench.py: 레시피 1만 개 합성 데이터로 엔진 응답 p50/p95 측정
README에 전체 실행 순서를 Windows 기준으로 정리하고, p95 결과를 보고해.
200ms를 넘으면 원인과 개선안을 먼저 보고하고 멈춰.
```

**내가 확인할 것**
- README대로 직접 실행해 화면이 뜨는지 봅니다. p95 수치만 확인하면 됩니다.

---

## 1-6. MVP 점검과 마무리 [필수]

직접 화면에서 여러 프로필로 써 봅니다. 이상한 추천이 나오면 아래처럼 지시합니다.

**입력(문제 발견 시)**
```
프로필 "<이름>"으로 보유 재료 <재료들>을 넣었더니 "<레시피>"가 <몇>위로 나왔어.
<기대: 안 나와야 함 / 더 위에 나와야 함>.
점수 내역과 필터 로그로 원인을 설명하고, 데이터 문제인지 로직 문제인지 구분해서 수정안을 제안해.
수정 전에 이 경우를 재현하는 테스트를 먼저 추가해.
```

**입력(마무리)**
```
MVP를 마무리해줘. 전체 테스트, 골든셋 평가, bench를 다시 돌려 결과를 docs/progress.md에 기록하고,
README를 최종 정리하고, Phase 2에서 할 일 목록을 docs/progress.md "다음 단계 제안"에 정리한 뒤 커밋해.
```

---

## 상황별 지시문

**새 세션에서 이어서 할 때**
```
CLAUDE.md와 docs/progress.md를 읽고 현재 상태를 요약해줘. 그다음 <단계 번호>를 이어서 진행해.
```

**에이전트가 테스트를 수정했을 때**
```
멈춰. tests/allergy/는 수정 금지야. 변경을 되돌리고, 테스트가 틀렸다고 판단한 이유만 설명해.
```

**계획서와 다르게 하자고 제안할 때**
```
제안 내용과 장단점, docs/plan.md에서 바뀌는 부분을 보여줘. 승인하면 plan.md도 함께 고쳐.
```

**보고가 너무 길거나 불명확할 때**
```
다음 형식으로만 다시 보고해: 변경 파일 / 테스트 결과(통과·실패 수) / 내가 확인할 것 / 남은 문제
```
