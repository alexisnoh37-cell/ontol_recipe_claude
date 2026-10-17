# 레시피 추천 엔진 구현 계획

> 이 문서는 설계의 기준입니다. 구현 중 이 문서와 다르게 해야 할 이유가 생기면, 먼저 제안하고 승인받은 뒤 이 문서를 함께 수정합니다.

## 1. 개요와 설계 원칙

PostgreSQL(Supabase) 하나에 식재료 지식그래프를 테이블로 구현하고, 규칙 기반 필터와 점수로 MVP를 만든다. 사용자 행동 데이터가 쌓이면 개인화 재정렬을 붙인다.

설계 원칙:

1. **알레르기는 결정적으로 판정한다.** 점수가 아니라 제외로 처리하고, 하위 개념과 파생 재료까지 그래프로 추적한다. 판정에 LLM은 쓰지 않는다.
2. **제약(hard)과 선호(soft)를 분리한다.** 같은 속성이라도 "못 먹음"은 제외, "별로"는 감점이다.
3. **지식그래프는 식재료에 집중한다.** 레시피와 사용자는 일반 테이블로 둔다.
4. **구체적인 선호가 상위 선호보다 우선한다.** "해산물 좋음, 새우 싫음"이면 새우는 감점된다.
5. **규칙으로 시작해 학습으로 넘어간다.** 가중치는 코드가 아니라 설정 파일에 둔다.
6. **LLM은 입출력 계층에만 둔다.** 자연어 입력 해석, 추천 사유 설명, 레시피 데이터 태깅을 맡는다.
7. **모든 추천은 설명 가능해야 한다.** 응답에 항목별 점수와 제외 사유를 포함한다.

| 채택 요소 | 보완 내용 |
| --- | --- |
| 파생 관계 기반 알레르기 추적 | 가공품은 "포함 가능"으로 보수적 처리 |
| 행 단위 선호 저장 구조 | 항목 추가 시 스키마 변경 불필요 |
| 식재료 이름 정규화(별칭 테이블) | 미매칭 로그로 주기 보강 |
| 기본 양념 보유 간주 | 기본 양념은 커버리지 계산에서 제외 |
| 구체성 우선 규칙 | is_a 계층을 따라 가장 가까운 선호 적용 |
| 3단계 파이프라인(필터, 지식 랭킹, 개인화) | 개인화는 Phase 3부터 |
| 대체재 안내 | 조리 맥락이 있는 조건부 대체 |
| LLM 자연어 해석과 설명 | 엔진 결과만 근거로 설명 |
| 맛 비교 방식 | 코사인 유사도 대신 차이 거리, 매운맛 허용 한도와 선호 분리 |

## 2. 시스템 아키텍처와 기술 스택

추천 요청은 6단계를 거친다. LLM은 처음과 끝에만 있고, 추천 판단은 엔진이 한다.

```
[1. 입력 해석]  →  [2. 후보 생성]  →  [3. 제약 필터]
   (LLM, Phase 2)                         │ 여기서 제외된 레시피는
                                          │ 이후 어떤 단계에서도 복귀 불가
                                          ▼
[6. 설명 생성]  ←  [5. 개인화 재정렬]  ←  [4. 지식 기반 점수]
   (LLM, Phase 2)     (Phase 3부터)
```

추천 엔진은 API와 분리된 순수 Python 패키지로 만든다. 그래야 단위 테스트가 쉽고, 나중에 프론트나 DB를 바꿔도 엔진은 그대로 쓸 수 있다. 디렉터리 구조, 패키지 관리, 데이터 주입 방식은 부록 A를 따른다.

### 지식 원본과 실행의 분리

식재료 지식은 온톨로지 방식으로 설계하되, 실행은 관계형으로 한다.

```
knowledge/*.yaml  ──(scripts/compile_knowledge.py)──▶  DB 테이블 + allergen_closure
 (지식 원본, 사람이 편집)        그래프 탐색은 여기서만              (요청 시에는 조회만)
```

- `knowledge/*.yaml`이 식재료, 관계, 알레르기의 원본이다.
- 그래프 탐색(is_a 상속, derived_from 추적)은 컴파일 시점에만 한다.
- 요청 처리 중에는 미리 계산된 테이블만 조회한다.
- DB의 관계 테이블은 직접 수정하지 않는다.

| 계층 | 선택 | 이유 |
| --- | --- | --- |
| DB | PostgreSQL (Supabase) | 재귀 CTE로 그래프 탐색 가능, 운영 부담 적음 |
| 로컬 개발 DB | Docker PostgreSQL 또는 Supabase CLI | 운영과 같은 SQL 문법 유지 |
| 백엔드 | Python 3.11+, FastAPI | 엔진과 같은 언어, 자동 API 문서 |
| 추천 엔진 | 순수 Python 패키지 | API와 분리해 테스트와 교체가 쉬움 |
| 프론트 | Streamlit(MVP) 이후 React | MVP는 화면 구현 비용 최소화 |
| LLM | Claude API (Phase 2부터) | 자연어 입력 해석, 설명 생성, 데이터 태깅 |
| 테스트 | pytest | 알레르기 회귀 테스트를 CI에서 강제 |
| 그래프 DB | Neo4j, 보류 | 대체·궁합 탐색이 많아지면 식재료 그래프만 분리 |

## 3. 데이터 모델

테이블은 식재료 그래프, 레시피, 사용자의 세 묶음으로 나눈다. 지식그래프는 `ingredient_relation` 한 테이블에 관계 유형을 두는 방식으로 구현한다. 지식·레시피 ID는 YAML과 같은 영문 snake_case 문자열(text)을 쓴다. 전체 DDL은 부록 B에 있다.

### 3-1. 식재료 그래프

| 테이블 | 주요 컬럼 | 역할 |
| --- | --- | --- |
| ingredient | id, name, kind(ingredient·concept), category, is_pantry_staple, is_processed, status, confidence | 정규 식재료 마스터. concept는 분류 전용 노드 |
| ingredient_alias | alias_norm, alias, ingredient_id, form, is_primary | "깐마늘", "다진 마늘"을 마늘로 매핑. 대표 이름도 한 행으로 저장 |
| ingredient_relation | from_id, to_id, type, certainty, context, ratio, note | is_a, derived_from, substitute, pairs_with. certainty는 derived_from 엣지 단위 |
| allergen_group | id, display_name, kind(base·bundle), official, source(law_annex2·custom) | 알레르기 분류. official은 법정 표시 대상 여부 |
| allergen_group_member | bundle_id, member_id | 묶음 그룹 → 기본 그룹 |
| ingredient_allergen | ingredient_id, allergen_group_id, certainty | 원천 재료에만 지정, 하위·파생은 계산으로 상속 |
| allergen_closure | allergen_group_id, ingredient_id, certainty, via | 상속 결과 캐시(컴파일 시 생성). 묶음 그룹도 펼쳐 저장. via는 설명용 경로 |
| ingredient_ancestor | ingredient_id, ancestor_id, depth | is_a 전이 폐포(컴파일 시 생성). 구체성 우선, 상위 개념 매칭에 사용 |
| ingredient_contains | ingredient_id, contained_id, certainty, via | "이 재료는 저 재료를 포함(가능)"(컴파일 시 생성). 절대 불선호 판정에 사용 |
| knowledge_build | id, source_hash, compiled_at, stats | 컴파일 이력 |

컴파일 산출물(`allergen_closure`, `ingredient_ancestor`, `ingredient_contains`)은 컴파일러만 쓴다. 계산 규칙은 부록 C를 따른다.

관계 유형별 규칙:

- **is_a**: 삼겹살 → 돼지고기 → 육류. 알레르기와 불선호는 아래로 상속되고, 선호는 가장 가까운 것이 적용된다.
- **derived_from**: 새우젓 → 새우, 마요네즈 → 계란. 알레르기 상속의 핵심 경로다.
- **substitute**: context 컬럼에 조리 맥락을 둔다. 예: 버터 → 식용유는 "볶음"에서만 가능.
- **pairs_with**: Phase 2부터 추가한다. 추천 사유와 "함께 쓰면 좋은 재료" 안내에 쓴다.
- **certainty**: 가공품처럼 제품마다 성분이 다른 경우 "포함 가능"으로 표시하고, 알레르기 판정에서는 포함으로 간주한다. derived_from 엣지마다 따로 둔다(된장 → 대두는 definite, 된장 → 밀은 possible).
- **concept 노드**: 육류, 해산물 같은 분류 전용 노드는 레시피 재료와 보유 재료로 쓸 수 없다(검증 오류). "젓갈류"처럼 레시피에 쓰일 수 있는 중간 노드는 하위 개념의 알레르기를 "포함 가능"으로 함께 가진다.

### 3-2. 레시피

| 테이블 | 주요 컬럼 | 역할 |
| --- | --- | --- |
| recipe | id, title, cuisine, difficulty(1~3), cook_time_min, servings, source, status(draft·published), confidence | 레시피 기본 정보, 검수 상태 |
| recipe_ingredient | recipe_id, line_no, ingredient_id(NULL = 미매칭), role, optional, amount, unit, raw_text | role은 main, sub, seasoning, garnish |
| recipe_taste | recipe_id, spicy, salty, sweet, sour, umami, savory | 각 0~5 강도 |
| recipe_equipment | recipe_id, equipment, required | 오븐, 에어프라이어 등 |
| recipe_step | recipe_id, step_no, text, technique | 조리 단계와 기법. technique은 대체재 context와 같은 어휘 |

`raw_text`에는 원문 표기("마늘 2쪽")를 남긴다. recipe의 difficulty·cook_time_min은 NULL(모름)을 허용한다(마이그레이션 0003, ar-1). 매핑 오류를 추적할 때 필요하다. cuisine, equipment, technique 어휘는 `knowledge/vocab.yaml`에 둔다. cuisine은 Phase 1에서 국가별 평면 어휘(한식, 일식, 중식, 양식 등)다.

엔진은 `config/engine.yaml`의 `serve_draft_recipes`가 false면 published 레시피만 쓴다. ar-1(2026-10-17 사람 결정)부터 true로 두고 draft도 추천한다(설명에 "검수 전 레시피입니다"). 골든셋은 이 설정과 무관하게 published만으로 평가한다. 엔진·DB가 읽는 레시피 폴더는 `recipe_dirs`(data/recipes, data/recipes_foodsafety)다. draft는 cuisine 미분류, 난이도·조리시간·맛 없음을 허용하고 엔진이 '모름'으로 다룬다(4-2~4-4).

### 3-3. 사용자

| 테이블 | 주요 컬럼 | 역할 |
| --- | --- | --- |
| user_profile | id, display_name, skill_level(1~3), household_size | 기본 정보. 로그인 없이 프로필 전환(D1) |
| user_preference | user_id, target_type, target_id, polarity(−1·1), strength(0~1), is_hard | 음식 종류, 식재료, 알레르기 등 모든 선호. 알레르기는 항상 is_hard |
| user_taste | user_id, dimension, preferred_level, max_level | 맛 선호 강도와 허용 한도 분리 |
| user_pantry | user_id, ingredient_id, expires_on | 보유 재료, expires_on은 nullable로만 두고 Phase 4에서 사용 |
| user_equipment | user_id, equipment | 보유 조리기구 |
| user_event | user_id, recipe_id, event_type, value, created_at | 클릭, 저장, 조리, 평점. Phase 3 마이그레이션에서 추가 |
| unmapped_term | term_norm, raw_example, source, seen_count | 미매칭 입력 로그(별칭 보강용) |

`user_preference`의 `target_type`에 새 값을 추가하는 것만으로 항목을 확장한다. Phase 1의 target_type은 ingredient, cuisine, allergen_group이다. 매운맛은 `user_taste`에서 `preferred_level`(좋아하는 정도)과 `max_level`(먹을 수 있는 한도)로 나눈다.

희망 조리시간은 프로필이 아니라 요청 파라미터(`max_time_min`, `time_is_hard`)로 받는다. 보유 재료도 요청에 담을 수 있고, 없으면 `user_pantry`를 쓴다.

## 4. 추천 로직

제약 필터로 먹을 수 없는 레시피를 먼저 제거하고, 남은 후보를 6개 항목 가중합으로 정렬한다. 알레르기는 어떤 점수로도 되살아나지 않는다.

### 4-1. 입력 정규화

- 폼 입력은 자동완성으로 정규 식재료 ID를 직접 고르게 한다.
- 자유 입력은 별칭 테이블로 매핑한다. 실패하면 Phase 2부터 LLM이 후보를 제시하고 사용자가 확인한다.
- 매핑되지 않은 입력은 로그로 남겨 별칭 테이블 보강에 쓴다.

### 4-2. 후보 생성

- main 재료를 하나 이상 보유한 레시피를 후보로 잡는다(직접 보유, 하위 개념 보유, 대체재 포함). sub 재료만 보유한 레시피는 후보가 아니다. 단, 주재료 표시(main)가 하나도 없는 레시피(식품안전나라 원본은 역할 구분이 없어 모두 sub)는 sub 재료를 후보 근거로 삼는다(ar-1, 역할을 지어내지 않음). 기본 양념은 점수·부족 재료 계산에서는 보유로 간주하지만 후보 생성 근거로는 쓰지 않는다(1-4 골든셋에서 변경).
- 동의어와 is_a 상위 개념으로도 매칭한다. 삼겹살을 가진 사용자는 "돼지고기"가 필요한 레시피에 매칭된다. 반대 방향(돼지고기 보유 → "삼겹살" 레시피)은 매칭하지 않고 부족 재료로 표시한다.
- 대체재로만 매칭된 재료는 따로 표시해 설명 단계에 넘긴다.
- 대체 관계는 `knowledge/substitutes.yaml`을 쓴다. context가 비어 있으면 항상 성립하고, 비어 있지 않으면 레시피 조리 단계의 technique 집합과 겹칠 때만 성립한다(Phase 1). 더 정교한 조건부 대체는 Phase 2에서 확장한다.

### 4-3. 제약 필터

- **알레르기**: 사용자 알레르기 그룹의 원천 재료에서 is_a 하위와 derived_from 파생을 모두 모은 집합(`allergen_closure`)에 걸리는 재료가 하나라도 있으면 제외한다. 선택(optional) 재료와 고명도 제외 대상이다(D2).
- **절대 불선호**: is_hard 재료는 `ingredient_contains`(부록 C)로 판정한다. 레시피 재료가 불선호 재료 자신이거나, 그 재료를 포함(가능)하면 제외한다. 포함에는 불선호 재료의 is_a 하위와 derived_from 파생("새우 못 먹음"이면 새우젓, 김치도 제외)뿐 아니라, 불선호 재료를 is_a 하위로 가진 넓은 재료도 possible로 들어간다("순두부 못 먹음"이면 순두부가 두부의 하위이므로 두부를 쓰는 레시피도 제외, 2026-10-04 확인). is_hard 음식 종류는 해당 cuisine을 제외한다.
- **매운맛 한도**: 레시피 spicy가 사용자 max_level을 넘으면 제외한다. 레시피 맛을 모르면(taste 없음) max_level이 5 미만인 사용자에게 제외한다(매운지 알 수 없으므로 보수적으로, ar-1). 5는 제한이 아니다.
- **조리기구, 시간**: 필수 조리기구가 없거나, 사용자가 시간을 절대 조건(`time_is_hard`)으로 두고 초과한 경우 제외한다. 조리시간을 모르면 시간 필터로 빼지 않는다(ar-1). 식단 조건은 Phase 2에서 추가한다.
- **미매칭 재료**: 정규 ID로 매핑되지 않은 재료가 있는 레시피는 알레르기가 있는 사용자에게 제외한다.
- 제외할 때마다 사유를 기록한다. 엔진은 제외 목록(recipe_id, 사유 코드, 상세)을 반환하고, API가 `logs/exclusions.jsonl`에 남긴다. 응답에는 사유별 개수 요약만 담는다.

### 4-4. 지식 기반 점수

레시피 정보를 모를 때(ar-1): 난이도 → D = `difficulty.unknown`, 희망 시간이 있는데 조리시간 → M = `time.unknown`, 맛 선호가 있는데 맛 → T = `taste.unknown`(모두 config/weights.yaml, 0.5). 음식 종류 미분류는 K 중립값. 설명에 "…정보가 없는 레시피입니다"를 붙인다.

```
S = 0.30·I + 0.20·K + 0.15·T + 0.15·P + 0.10·D + 0.10·M
```

| 기호 | 항목 | 계산(0~1) |
| --- | --- | --- |
| I | 재료 커버리지 | 보유 재료 가중합 ÷ 필요 재료 가중합. main 3, sub 2, 기본 양념이 아닌 seasoning(춘장, 쯔유, 굴소스 등) 1. 기본 양념(role 무관)·선택 재료·garnish는 계산에서 뺀다. 대체재로 충족 시 80%(또는 관계의 ratio) 인정 (1-4 골든셋에서 변경) |
| K | 음식 종류 | 선호 1.0, 중립 0.5, 불선호 0.1 |
| T | 맛 적합도 | 1 − (맛별 \|preferred_level − 레시피 강도\|의 가중 평균 ÷ 5). 사용자가 입력하지 않은 맛은 평균에서 빼고, 전부 미입력이면 0.5 |
| P | 재료 선호 | 재료별 값 = 0.5 + 0.5 × polarity × strength(선호 없으면 0.5). 재료마다 가장 구체적인 선호를 적용하고, 역할 가중 평균을 낸다. 역할 가중치는 main 1.0, sub 0.6, garnish·optional 0.2 |
| D | 난이도 적합도 | 실력과 같으면 1.0, 한 단계 쉬우면 0.9, 두 단계 쉬우면 0.8, 한 단계 어려우면 0.4, 두 단계 어려우면 0.1. 실력과 난이도는 모두 1~3 |
| M | 시간 적합도 | 희망 시간 w 이내 1.0, 초과하면 max(0, 1 − (t − w) ÷ w). 희망 시간이 없으면 1.0 |

`missing`(부족 재료)에는 선택 재료가 아니면서 보유하지 않은 재료를 모두 표시한다. 기본 양념이 아닌 seasoning(굴소스 등)도 포함한다.

정렬은 점수 내림차순이다. 점수가 같으면(응답 표기와 같은 소수 셋째 자리 기준) I 높은 순 → 부족 재료 적은 순 → 조리시간 짧은 순 → recipe_id 순으로 정한다(1-4 골든셋에서 추가).

가중치와 계수는 모두 `config/weights.yaml`에 둔다. 위 값은 초기값이며 골든셋으로 조정한다. 조리기구는 필터에서만 다루고 점수에는 넣지 않는다(이중 반영 방지).

### 4-5. 구체성 우선 규칙

레시피의 각 재료에서 is_a를 위로 올라가며 처음 만나는 선호를 적용한다. "해산물 +0.6, 새우 −0.9"인 사용자라면 새우는 −0.9, 오징어는 해산물의 +0.6이 적용된다. 같은 깊이에 선호가 여러 개면 가장 낮은 값을 쓴다. 이 soft 선호는 is_a만 따르고 derived_from은 따르지 않는다(절대 불선호는 4-3).

### 4-6. 다양성 보정과 개인화

- 상위 10개 안에 같은 음식 종류는 5개, 같은 주재료는 3개를 넘지 않게 조정한다(1-4 골든셋에서 음식 종류 한도 3 → 5). main 재료가 여러 개면 각각을 센다. 순서는 **점수 차가 0.1 이하인 레시피끼리만** 바꾼다(1-6, `config/weights.yaml diversity.max_score_gap`): 자리마다 남은 최고점 레시피가 한도를 넘으면 그보다 0.1 이하로 낮으면서 한도를 지키는 첫 레시피를 대신 올리고, 그런 레시피가 없으면 한도를 넘더라도 최고점 레시피를 올린다.
- Phase 3부터 상위 50개를 행동 데이터로 재정렬한다. 최근 7일 안에 먹은 메뉴는 감점하고, 저장하거나 실제 조리한 유형은 가산한다.

### 4-7. 설명 생성

응답에는 항목별 점수, 부족한 재료, 대체 안내("쪽파 대신 대파를 쓰세요"), 주요 제외 사유를 담는다. Phase 1은 템플릿 문장으로, Phase 2부터는 LLM이 이 데이터만 근거로 문장을 다듬는다.

대체 안내의 후보도 사용자의 알레르기 closure와 절대 불선호로 거른다. 예를 들어 우유 알레르기 사용자에게 "식용유 대신 버터"를 안내하지 않는다.

```json
{
  "recipe_id": "kimchi_jjigae_pork",
  "title": "돼지고기 김치찌개",
  "score": 0.84,
  "breakdown": {"I": 0.92, "K": 1.0, "T": 0.88, "P": 0.71, "D": 1.0, "M": 0.9},
  "missing": ["두부"],
  "substitutions": [{"need": "쪽파", "use": "대파"}],
  "notes": ["당근은 선택 재료라 빼고 조리할 수 있습니다"]
}
```

## 5. 데이터 구축 전략

추천 품질의 대부분은 식재료 마스터와 관계 데이터가 결정한다. 식재료 200~300개로 작게 시작하고, 레시피는 LLM으로 초안을 만든 뒤 사람이 검수해 넣는다.

### 5-1. 식재료 마스터

- 카테고리 계층은 3단계 이내로 둔다(예: 육류 > 돼지고기 > 삼겹살).
- 알레르기 그룹 기준은 `docs/decisions.md`를 따른다.
- 향, 식감, 궁합 같은 풍부한 속성은 Phase 2 이후 필요한 것부터 넣는다.

### 5-2. 숨은 알레르기 체크리스트

아래 가공품은 derived_from 관계를 반드시 넣는다. 제품마다 성분이 다르면 certainty를 "포함 가능"으로 둔다.

| 가공품 | 원천 재료 | 비고 |
| --- | --- | --- |
| 새우젓 | 새우 | |
| 액젓 | 멸치 등 생선 | 제품별 원료 상이 |
| 김치 | 젓갈(새우, 생선) | 제품별 상이, 포함 가능 |
| 굴소스 | 굴 | |
| 마요네즈 | 계란 | |
| 땅콩버터 | 땅콩 | |
| 간장 | 대두, 밀 | |
| 된장, 고추장 | 대두, 밀 | 고추장은 밀 포함 제품 많음 |
| 버터, 치즈, 생크림 | 우유 | |
| 부침가루, 빵가루, 카레가루 | 밀 | |

### 5-3. 레시피 수집과 검수

1. 출처는 `docs/decisions.md`를 따른다. 외부 레시피 본문은 복제하지 않는다. 예외: 식품안전나라 조리식품 레시피 DB(D3 보완 2, 개인용 범위·출처 표시).
2. 재료, 양, 역할, 맛 프로필, 난이도, 조리기구를 구조화한다.
3. 재료를 별칭 테이블로 정규 ID에 매핑한다. 실패한 재료는 검수 큐로 보낸다.
4. 사람이 검수표를 확인하고 승인하면 status를 published로 바꾼다.

#### 5-3-1. 식품안전나라 레시피 가져오기 (D3 보완 2)

1. `scripts/fetch_foodsafety.py`가 Open API(COOKRCP01)에서 원본을 내려받아 `data/external/foodsafety/raw/`에 저장한다. 인증키는 `.env`의 `FOODSAFETY_API_KEY`. 원본은 커밋한다(D3 보완 3).
2. `scripts/convert_foodsafety.py`가 원본을 레시피 YAML(`data/recipes_foodsafety/fs_<일련번호>.yaml`, 커밋)로 바꾼다. 로더(`data/recipes/`)와 골든셋에는 들어가지 않는다.
   - `source: foodsafety`, `status: draft`, `confidence: low`, note에 출처(식품의약품안전처 식품안전나라, 일련번호)와 요리종류·조리방법 원문.
   - 재료: 재료정보(RCP_PARTS_DTLS)를 줄·쉼표(괄호 밖)로 나눠 `raw_text`에 원문을 두고, 양 앞까지의 이름이 별칭 색인과 정확히 일치할 때만 `ingredient`를 채운다. 나머지는 `null`(미매칭). `role`은 모두 `sub`(검수 때 정함).
   - 줄 나누기: HTML 태그(`<br>`), 줄 중간 대괄호(`[소스소개]`), 공백 사이 하이픈(` - `), `>`는 줄바꿈·머리말 구분으로 본다. 버리는 것은 머리말(고정 단어, 레시피 이름, 분량 "2인분 기준", "…재료")과 이름이 정확히 "물"인 항목(시드 규칙)뿐이다. 머리말이 아닌 소제목("두부구이 : 두부 70g"의 "두부구이")은 버리지 않고 따로 한 항목(미매칭)으로 남긴다. 머리말 단어가 공백으로만 붙은 항목("재료 닭가슴살 100g", "양념 다진 마늘")은 머리말을 떼되, 뒤가 양 표기로 시작하면("소스 1큰술") 그대로 둔다. '장식'은 머리말 단어다(um-2 사람 결정 2026-10-17).
   - `cuisine: 미분류`, `cook_time_min`·`difficulty`·`taste` 없음(API에 없음, 검수 때 채움). 조리 단계는 MANUAL01~20 원문.
   - 재료정보가 없는 레시피는 만들지 않고 보고한다.
3. 미매칭 재료 빈도와 레시피별 미매칭 수를 `docs/review/foodsafety_unmatched.md`로 만든다. 별칭·재료 보강은 knowledge에 draft로 추가한 뒤 다시 변환한다.
4. published로 바꾸려면 미매칭 0, cuisine·cook_time_min·난이도·맛 채움, 사람 검수가 필요하다(검증 규칙).
5. 엔진·DB 적재(ar-1, 2026-10-17 사람 결정, 개인용 범위 D3): `config/engine.yaml` `recipe_dirs`로 data/recipes와 함께 읽는다. 값이 없는 칸은 엔진이 '모름'으로 다룬다(4-2~4-4). 이전(int-2)에는 그래프 표시 전용이었다.
5. 열람용 정적 HTML 뷰어: `scripts/make_foodsafety_viewer.py`(템플릿 `scripts/foodsafety_viewer_template.html`)가 원본과 같은 변환 규칙으로 `data/recipes_foodsafety/viewer.html`(gitignore)을 만든다. 사진·영양 정보·저감 조리 팁, 재료별 매칭 여부를 보여 준다. 개인용 열람 전용, 외부 게시 금지.

#### 5-3-2. YouTube 레시피 데이터셋 변환과 원본 이름 보정표 (D3 예외, um-2)

1. `scripts/convert_simplecooking.py`(자취요리신)·`scripts/convert_sallimpop.py`(살림팝)가 `kb/youtube_seed.py`로 원본(`data/<name>_recipe_dataset/recipes/<name>/*.yaml`, 읽기만)을 `data/recipes/`(draft)로 바꾼다. 재료는 이름·별칭 정확 일치로만 매핑한다.
2. **원본 이름 보정표**(`data/recipe_name_overrides.yaml`, um-2 사람 승인 2026-10-17): 원본 재료 이름에 자막 문구·크기·오타가 붙은 경우("맛을 위해 참기름", "고추장 크게", "진강장")를 knowledge 별칭으로 넣지 않고 변환 단계에서 고친다. 항목마다 `id`(이 재료로 매핑) · `drop`(재료에서 뺌) · `split`(한 줄을 여러 재료로) 중 하나.
   - `drop`은 물(`water`)과, 같은 레시피에 그 재료 줄이 이미 있는 중복(`duplicate:<재료 id>`)에만 쓴다. 변환기는 중복 재료 줄이 실제로 없으면 멈춘다(한 줄 안에 두 표기가 적힌 경우를 중복으로 오판해 알레르기 성분이 빠지지 않게).
   - 바뀐 내용은 레시피 note와 데이터셋 `CONVERSION.md` "레시피별로 달라진 것"에 남는다. 표에 없는 재료·concept·사유는 오류다.
3. 미매칭 보강 결정의 근거: `docs/review/unmapped_review.md`(검수표, 기록), `docs/review/unmapped_decisions.json`(사람 결정), `docs/review/unmapped_proposal.yaml`(항목별 decision).

### 5-4. 데이터 검증 스크립트

- 모든 recipe_ingredient가 정규 ID에 매핑되어 있다. 단, draft 레시피는 미매칭(NULL)을 허용하고 검수표에 표시한다. published는 예외 없음(2026-10-16 승인, 자취요리신 데이터 연결). 미매칭 레시피는 알레르기 사용자에게 제외된다(4-3 제약 필터).
- is_processed 재료는 derived_from 관계가 1개 이상 있다.
- 모든 published 레시피에 맛 프로필과 난이도가 있다.
- is_a, derived_from, 그리고 두 그래프의 합집합에 순환 관계가 없다.
- concept 노드가 레시피 재료나 보유 재료로 쓰이지 않는다.
- 레시피의 cuisine, equipment, technique이 `knowledge/vocab.yaml` 어휘에 있다. 예외: draft 레시피는 cuisine `미분류`를 쓸 수 있다(vocab에는 넣지 않는다).
- cook_time_min은 published 레시피에 필수이고, draft는 비워 둘 수 있다. 다만 엔진·DB에 적재(`kb.recipes.load_recipe_specs`)할 때는 cuisine `미분류`이거나 cook_time_min이 없는 레시피를 거부한다(DB 컬럼은 NOT NULL 유지).
- user_preference의 target_id가 실제로 존재한다.

## 6. 단계별 로드맵

| 단계 | 내용 | 다음 단계로 가는 관문 |
| --- | --- | --- |
| Phase 0 · 기반 설계 | 스키마 확정, 지식 컴파일러, 식재료 200개와 관계·알레르기 데이터, 알레르기 회귀 테스트 시나리오 | 알레르기 테스트 시나리오 승인, 식재료 검수 완료 |
| Phase 1 · MVP | 제약 필터(조리기구 포함)와 점수 엔진, 기본 대체재(substitutes.yaml + technique 맥락), FastAPI, Streamlit 화면, 레시피 50~100개, 템플릿 설명 | 알레르기 테스트 100% 통과, 골든셋 기준 충족, 엔진 p95 200ms 이하 |
| Phase 2 · 지능화 | LLM 자연어 입력 해석과 설명 생성, 조건부 대체재 확장, 식단 조건, 궁합 관계, 레시피 300개 이상 | 사용자 행동 로그 수집 시작 |
| Phase 3 · 개인화 | user_event 테이블 추가, 클릭·저장·조리 로그로 상위 후보 재정렬, 최근 먹은 메뉴 감점, 가중치 학습 | |
| Phase 4 · 확장 | 장보기 목록, 주간 식단, 유통기한 임박 재료 우선 소비, 가족 구성원 취향과 알레르기 통합 | |

**이번 구축 범위는 Phase 0과 Phase 1(MVP)까지다.** Phase 1 관문(알레르기 테스트 100% 통과)은 일정과 관계없이 지킨다.

부가 트랙 ui(사람 요청·승인 2026-10-16): 재료 ↔ 레시피 양방향 조회. 판정·점수는 바꾸지 않는 표시 기능이다.
- `GET /recipes/{id}?profile_id=&pantry=`: 역할별 전체 재료(원문, 이름, 선택·기본 양념·미매칭 표시)와 조리 단계. 보유 기준(pantry 우선, 없으면 프로필 보유 재료)을 주면 줄마다 `have`를 붙인다. 보유 판정은 엔진 후보 단계와 같은 `owned_ingredients`(보유 재료·기본 양념과 그 is_a 조상, 컴파일 결과 조회만). 대체재는 사용자 안전 확인이 필요해 보지 않는다(추천 카드의 대체 안내를 따른다). 알레르기 설정이 있는 프로필이면 성분표 확인 표시(1-6 결정)를 붙인다. 시판 제품(`config/display.yaml` `commercial_product_notice`의 재료)이 든 레시피는 알레르기 설정과 무관하게 `commercial_notice`("시판 제품으로 제품 성분을 확인해 알레르기 유무를 확인하시기 바랍니다.")를 붙이고 화면은 재료 목록 위에 보여 준다(um-2 사람 결정 2026-10-17, 판정은 그대로 제외). 없는 레시피·프로필 404, 모르는 재료·concept 400.
- Streamlit 추천 탭: "이번만 재료 직접 고르기"로 고른 재료를 `POST /recommend`의 `pantry`로 보낸다(프로필에 저장하지 않음). 추천 카드마다 "전체 재료·조리 순서 보기"(위 API, 같은 보유 기준).
- **재료로 레시피 찾기**(ui-2, 사람 결정 2026-10-16): 추천과 별개인 조회 기능. 점수·선호로 순위를 매기지 않는다. `engine/browse.py`(`Recommender.browse`).
  - 보유로 보는 재료 = 고른 재료 + 기본 양념 + 그 is_a 조상(`owned_ingredients`). 대상 레시피 = 고른 재료(기본 양념 제외)로 main 줄 하나 이상이 채워지는 레시피(추천 후보 기준과 같음). 대체재는 쓰지 않는다.
  - 꼭 필요한 재료 = 선택이 아닌 main·sub·seasoning 줄(미매칭 줄은 채울 수 없으므로 부족). 부족 0개 = 조리 가능, 1~`browse_max_missing`개(config/engine.yaml, 기본 2) = 거의 가능.
  - **알레르기는 제외하지 않고 주의 표시**(사람 결정 2026-10-16, 이 조회 기능 한정). 판정은 추천 필터와 같은 `UserConstraints.check`(possible·선택·고명·기본 양념 포함, 미매칭 = 안전 보장 불가)를 쓰고 알레르기·미매칭 사유만 경고로 돌려준다. 경고가 있는 레시피는 같은 묶음 안에서 뒤로 정렬하고, 결과 위에 안내 문구(`config/display.yaml` `browse_allergy_notice`)를 둔다. 추천(`/recommend`)의 제외 규칙과 tests/allergy는 바뀌지 않는다.
  - `GET /browse?ingredients=..&profile_id=|persona_id=|allergen_groups=..&max_missing=`: 알레르기 기준은 최대 하나. 응답: `selected`, `cookable`, `near`(레시피별 쓴 고른 재료, 부족 줄, 없어도 되는 줄, `allergy_warnings`, 그래프 강조용 노드·링크 id), `allergy_notice`. 모르는 재료·concept·알레르기 그룹 400, 없는 프로필·페르소나 404.
  - 화면: Streamlit "재료로 레시피 찾기" 탭(프로필 알레르기로 주의 표시 선택), `/viz` "재료로 레시피 찾기" 카드(검색 또는 그래프 재료 노드 클릭으로 고르기, 알레르기 기준 페르소나·프로필 선택, 결과를 그래프에 강조: 고른 재료 초록, 조리 가능 레시피 연두, 거의 가능 노랑, 알레르기 주의 빨강, 모자란 재료 주황).

부가 트랙 viz(mvp-v1 이후, 사람 요청·승인 2026-10-03): 지식그래프와 추천 과정 3D 시각화. Phase 2 기능(LLM·개인화·장보기)과 무관한 읽기 전용 화면이다. 상세는 부록 D.

부가 트랙 adhoc(사람 요청·승인 2026-10-16): DB에 없는 레시피(AI가 만든 레시피 등)를 붙여 넣으면 재료·알레르기 구조를 분석해 온톨로지 그래프 위에 겹쳐 보여 준다. 저장하지 않는 일회성 분석이고 LLM을 쓰지 않는다. 상세는 부록 E.

## 7. 테스트와 검증

알레르기 회귀 테스트는 통과율 100%가 배포 조건이다. 추천 품질은 페르소나 골든셋으로 측정한다.

### 7-1. 알레르기 회귀 테스트 (`tests/allergy/`, 실패 시 배포 차단)

- 새우 알레르기 사용자에게 새우젓이 들어간 레시피가 나오지 않는다.
- 견과류 알레르기 사용자에게 땅콩버터, 호두가 들어간 레시피가 나오지 않는다.
- 난류 알레르기 사용자에게 마요네즈가 들어간 레시피가 나오지 않는다.
- 밀 알레르기 사용자에게 간장, 부침가루가 들어간 레시피가 나오지 않는다.
- 알레르기 재료가 선택(optional) 재료일 때도 제외된다.
- 미매칭 재료가 있는 레시피는 알레르기 사용자에게 나오지 않는다.

### 7-2. 로직 단위 테스트 (`tests/logic/`)

- 구체성 우선: "해산물 좋음, 새우 싫음" 사용자에게 새우 요리는 감점, 오징어 요리는 가산된다.
- 매운맛: max_level 2 사용자에게 spicy 3 이상은 제외되고, preferred_level만 낮은 사용자에게는 감점만 된다.
- 동의어: "달걀" 입력이 "계란" 레시피와 매칭된다.
- 상위 개념 매칭: 삼겹살 보유 시 "돼지고기" 레시피가 후보에 들어간다.
- 기본 양념: 소금, 간장을 입력하지 않아도 재료 커버리지가 깎이지 않는다.
- 난이도: 초급 사용자에게 같은 조건이면 difficulty 1이 3보다 위에 온다.
- 모든 응답에 breakdown이 포함된다.

### 7-3. 골든셋 평가 (`tests/golden/`)

- 페르소나 8명을 만들고, 각각 보유 재료와 "상위에 나와야 할 레시피"를 사람이 정한다.
- 상위 3개 안에 기대 레시피가 들어가는 비율을 측정하고, 가중치를 바꿀 때마다 다시 돌린다.
- Phase 3부터는 클릭률, 저장률, 실제 조리율을 함께 본다.

### 7-4. 성능 기준

- LLM 호출을 제외한 엔진 응답 p95 200ms 이하를 Phase 1 관문에 포함한다.
- 레시피 1만 개 합성 데이터로 벤치마크 스크립트(`scripts/bench.py`)를 만들어 측정한다.
- LLM 설명은 엔진 결과를 먼저 보여준 뒤 이어서 채운다.

## 8. 리스크와 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| 식재료 이름 미매칭 | 후보 누락, 알레르기 판정 누락 | 별칭 테이블, 미매칭 로그 주기 보강, 미매칭 레시피는 알레르기 사용자에게 제외 |
| 가공품 성분 차이 | 숨은 알레르기 노출 | "포함 가능"으로 보수적 제외, 화면에 제품 성분 확인 안내와 면책 문구 |
| 데이터 구축 비용 | 일정 지연 | 속성은 단계적으로 추가, 초안 생성 후 검수 |
| 감에 의존한 가중치 | 추천 품질 편차 | 설정 파일 분리, 골든셋 튜닝, 점수 내역 노출 |
| 잘못된 대체재 | 조리 실패 | 조리 맥락이 있는 조건부 대체, 확신 낮으면 안내만 |
| 콜드스타트 | 첫 추천 품질 저하 | 온보딩 질문 5개 이내, 미입력 항목은 중립값 |
| 레시피 저작권 | 법적 분쟁 | 직접 작성과 공공데이터 위주, 외부 레시피는 링크만 |

---

## 부록 A. 디렉터리 구조, 패키지 관리, 데이터 주입 (Phase 0-1 확정)

### 패키지 관리: uv

- `pyproject.toml` + `uv.lock`으로 의존성을 고정하고, `.python-version`(3.12)으로 파이썬 버전도 uv가 설치한다. Windows에서 venv 활성화 없이 `uv run ...`으로 실행한다.
- 설치(Windows): `winget install astral-sh.uv` 또는 `pip install uv` → `uv sync` → `uv run pytest`.
- 의존성: pyyaml, pydantic 2(지식 검증), sqlalchemy 2, psycopg 3(binary), alembic, fastapi, uvicorn, streamlit, httpx. dev 그룹: pytest.
- `engine/`은 표준 라이브러리와 pyyaml(설정 로드)만 import한다. `tests/logic/test_engine_purity.py`로 sqlalchemy, fastapi, psycopg, streamlit import를 금지한다.

### 디렉터리 구조

```
pyproject.toml  uv.lock  .python-version  .env.example  docker-compose.yml  alembic.ini
engine/          순수 Python. DB·FastAPI와 무관
  model.py       frozen dataclass: KnowledgeSnapshot, Recipe, UserContext, RecommendRequest, RecommendResult, Exclusion
  ports.py       Protocol: KnowledgeRepository, RecipeRepository
  memory.py      InMemoryKnowledgeRepository, InMemoryRecipeRepository(재료 → 레시피 역색인)
  config.py      weights.yaml, pantry_staples.yaml, engine.yaml → EngineConfig
  normalize.py  candidates.py  filters.py  scoring.py  explain.py
  recommend.py   파이프라인 조립(후보 → 필터 → 점수 → 다양성 → 설명)
kb/              지식 컴파일러의 순수 로직(DB와 무관). 테스트, 벤치, 엔진 fixture가 공유
  load.py  schema.py  validate.py  graph.py  compiled.py
storage/         SQLAlchemy 테이블, 엔진 입력 변환·조립(engine_source.py: 파일·DB 공급원 공용), 사용자 저장소(users.py), 컴파일 결과 writer
api/             FastAPI (main.py, schemas.py, present.py: 이름·안내 문구 표시 계층)
app/             Streamlit (API를 HTTP로 호출)
knowledge/       allergens.yaml, vocab.yaml, ingredients.yaml 또는 ingredients/*.yaml, substitutes.yaml, README.md
data/recipes/    레시피 시드 YAML(레시피당 1파일)
data/recipes_foodsafety/  식품안전나라 변환 결과 draft YAML. 적재 대상 아님, 그래프 표시 전용(5-3-1, 부록 D-8)
data/external/foodsafety/raw/  식품안전나라 API 원본 JSON
config/          weights.yaml, pantry_staples.yaml, engine.yaml(serve_draft_recipes 등 가중치 외 설정), display.yaml(화면 안내·면책 문구, 표시 전용)
scripts/         compile_knowledge.py, validate_data.py, load_recipes.py, bench.py (얇은 CLI, 로직은 kb/·storage/)
migrations/      Alembic
tests/           allergy/  logic/  golden/  kb/(컴파일러)  storage/(DB 통합, DATABASE_URL이 있을 때만)  support/(fixture 빌더)
docs/            plan.md  decisions.md  progress.md  review/
logs/            (gitignore) 제외 사유 JSONL
```

- 의존 방향: `api → storage → kb, engine.model`, `api → engine`, `app → api(HTTP)`. engine은 다른 패키지를 import하지 않는다.
- PostgreSQL 16은 docker compose로 띄우고 포트는 `.env`로 바꿀 수 있게 한다(로컬 PostgreSQL이 5432를 쓰는 경우 대비).

### 데이터 주입

```
engine/ports.py
  KnowledgeRepository.snapshot() -> KnowledgeSnapshot
      (alias_index, ancestors, contains, allergen_closure, substitutes, pantry_staples, concept_ids)
  RecipeRepository.by_ingredients(ids) -> Iterable[Recipe]
  RecipeRepository.get(recipe_id) -> Recipe | None
engine/recommend.py
  Recommender(knowledge, recipes, config).recommend(user: UserContext, req: RecommendRequest)
      -> RecommendResult(items, exclusions)
```

- 사용자 데이터는 엔진이 조회하지 않는다. 호출자가 `UserContext`로 넘긴다(API는 storage에서 읽어 구성).
- 리포지토리 구현체는 in-memory 하나이고, 공급원만 다르다.
  - 테스트: `kb.compile(...)` 결과(실제 컴파일러 코드) + 레시피 dataclass
  - 골든셋: 실제 `knowledge/` + `data/recipes/` YAML
  - 벤치: 합성 레시피 1만 개
  - API: 시작 시 storage가 DB 전체를 읽어 생성. 재컴파일이나 레시피 적재 후에는 재시작하거나 reload 엔드포인트로 갱신
- `tests/allergy/` fixture는 closure를 손으로 만들지 않는다. 테스트 안의 작은 지식 dict를 `kb.compile`에 통과시켜 만든다. 실제 `knowledge/` 파일 대상 스모크 테스트도 1개 둔다.
- `tests/storage/`에 "DB에서 읽은 스냅샷 = YAML 컴파일 스냅샷" 동치 테스트를 둔다.

## 부록 B. PostgreSQL DDL 초안 (Phase 0-1 확정)

enum은 PostgreSQL ENUM 대신 CHECK로 둔다. 컴파일 산출물 테이블은 컴파일러만 쓴다.

```sql
-- 0. 컴파일 메타
CREATE TABLE knowledge_build (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_hash  text NOT NULL,
  compiled_at  timestamptz NOT NULL DEFAULT now(),
  stats        jsonb NOT NULL
);

-- 1. 식재료 그래프
CREATE TABLE ingredient (
  id               text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  name             text NOT NULL,
  kind             text NOT NULL DEFAULT 'ingredient' CHECK (kind IN ('ingredient','concept')),
  category         text,
  is_pantry_staple boolean NOT NULL DEFAULT false,
  is_processed     boolean NOT NULL DEFAULT false,
  status           text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence       text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note             text
);
CREATE TABLE ingredient_alias (
  alias_norm    text PRIMARY KEY,
  alias         text NOT NULL,
  ingredient_id text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  form          text,
  is_primary    boolean NOT NULL DEFAULT false
);
CREATE INDEX ingredient_alias_prefix_idx ON ingredient_alias (alias_norm text_pattern_ops);
CREATE INDEX ON ingredient_alias (ingredient_id);
CREATE TABLE ingredient_relation (
  from_id    text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  to_id      text NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
  type       text NOT NULL CHECK (type IN ('is_a','derived_from','substitute','pairs_with')),
  certainty  text CHECK (certainty IN ('definite','possible')),
  context    text[] NOT NULL DEFAULT '{}',
  ratio      numeric(3,2) CHECK (ratio > 0 AND ratio <= 1),
  status     text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note       text,
  PRIMARY KEY (from_id, to_id, type),
  CHECK (from_id <> to_id),
  CHECK ((type = 'derived_from') = (certainty IS NOT NULL))
);
CREATE INDEX ON ingredient_relation (to_id, type);
CREATE TABLE allergen_group (
  id           text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  display_name text NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('base','bundle')),
  status       text NOT NULL CHECK (status IN ('draft','reviewed')),
  confidence   text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note         text
);
CREATE TABLE allergen_group_member (
  bundle_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  member_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  PRIMARY KEY (bundle_id, member_id)
);
CREATE TABLE ingredient_allergen (
  ingredient_id     text REFERENCES ingredient(id) ON DELETE CASCADE,
  allergen_group_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  certainty         text NOT NULL CHECK (certainty IN ('definite','possible')),
  PRIMARY KEY (ingredient_id, allergen_group_id)
);

-- 1-b. 컴파일 산출물
CREATE TABLE ingredient_ancestor (
  ingredient_id text REFERENCES ingredient(id) ON DELETE CASCADE,
  ancestor_id   text REFERENCES ingredient(id) ON DELETE CASCADE,
  depth         smallint NOT NULL CHECK (depth >= 1),
  PRIMARY KEY (ingredient_id, ancestor_id)
);
CREATE TABLE ingredient_contains (
  ingredient_id text REFERENCES ingredient(id) ON DELETE CASCADE,
  contained_id  text REFERENCES ingredient(id) ON DELETE CASCADE,
  certainty     text NOT NULL CHECK (certainty IN ('definite','possible')),
  via           text[] NOT NULL,
  PRIMARY KEY (ingredient_id, contained_id)
);
CREATE TABLE allergen_closure (
  allergen_group_id text REFERENCES allergen_group(id) ON DELETE CASCADE,
  ingredient_id     text REFERENCES ingredient(id) ON DELETE CASCADE,
  certainty         text NOT NULL CHECK (certainty IN ('definite','possible')),
  via               text[] NOT NULL,
  PRIMARY KEY (allergen_group_id, ingredient_id)
);
CREATE INDEX ON allergen_closure (ingredient_id);

-- 2. 레시피
CREATE TABLE recipe (
  id            text PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9_]*$'),
  title         text NOT NULL,
  cuisine       text NOT NULL,
  difficulty    smallint NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
  cook_time_min integer NOT NULL CHECK (cook_time_min > 0),
  servings      smallint CHECK (servings > 0),
  source        text NOT NULL,
  status        text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
  confidence    text NOT NULL DEFAULT 'high' CHECK (confidence IN ('high','low')),
  note          text,
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE recipe_ingredient (
  recipe_id     text REFERENCES recipe(id) ON DELETE CASCADE,
  line_no       smallint,
  ingredient_id text REFERENCES ingredient(id) ON DELETE RESTRICT,  -- NULL = 미매칭
  role          text NOT NULL CHECK (role IN ('main','sub','seasoning','garnish')),
  optional      boolean NOT NULL DEFAULT false,
  amount        numeric(8,2),
  unit          text,
  raw_text      text NOT NULL,
  PRIMARY KEY (recipe_id, line_no)
);
CREATE INDEX ON recipe_ingredient (ingredient_id);
CREATE TABLE recipe_taste (
  recipe_id text PRIMARY KEY REFERENCES recipe(id) ON DELETE CASCADE,
  spicy  smallint NOT NULL CHECK (spicy  BETWEEN 0 AND 5),
  salty  smallint NOT NULL CHECK (salty  BETWEEN 0 AND 5),
  sweet  smallint NOT NULL CHECK (sweet  BETWEEN 0 AND 5),
  sour   smallint NOT NULL CHECK (sour   BETWEEN 0 AND 5),
  umami  smallint NOT NULL CHECK (umami  BETWEEN 0 AND 5),
  savory smallint NOT NULL CHECK (savory BETWEEN 0 AND 5)
);
CREATE TABLE recipe_equipment (
  recipe_id text REFERENCES recipe(id) ON DELETE CASCADE,
  equipment text NOT NULL,
  required  boolean NOT NULL DEFAULT true,
  PRIMARY KEY (recipe_id, equipment)
);
CREATE TABLE recipe_step (
  recipe_id text REFERENCES recipe(id) ON DELETE CASCADE,
  step_no   smallint,
  text      text NOT NULL,
  technique text,
  PRIMARY KEY (recipe_id, step_no)
);

-- 3. 사용자
CREATE TABLE user_profile (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  display_name   text NOT NULL UNIQUE,
  skill_level    smallint NOT NULL DEFAULT 1 CHECK (skill_level BETWEEN 1 AND 3),
  household_size smallint NOT NULL DEFAULT 1 CHECK (household_size > 0),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE user_preference (
  user_id     bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  target_type text NOT NULL CHECK (target_type IN ('ingredient','cuisine','allergen_group')),
  target_id   text NOT NULL,
  polarity    smallint NOT NULL CHECK (polarity IN (-1, 1)),
  strength    numeric(3,2) NOT NULL CHECK (strength BETWEEN 0 AND 1),
  is_hard     boolean NOT NULL DEFAULT false,
  PRIMARY KEY (user_id, target_type, target_id),
  CHECK (NOT is_hard OR polarity = -1),
  CHECK (target_type <> 'allergen_group' OR (is_hard AND polarity = -1))
);
CREATE TABLE user_taste (
  user_id         bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  dimension       text NOT NULL CHECK (dimension IN ('spicy','salty','sweet','sour','umami','savory')),
  preferred_level smallint CHECK (preferred_level BETWEEN 0 AND 5),
  max_level       smallint CHECK (max_level BETWEEN 0 AND 5),
  PRIMARY KEY (user_id, dimension),
  CHECK (preferred_level IS NULL OR max_level IS NULL OR preferred_level <= max_level)
);
CREATE TABLE user_pantry (
  user_id       bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  ingredient_id text REFERENCES ingredient(id) ON DELETE RESTRICT,
  expires_on    date,
  PRIMARY KEY (user_id, ingredient_id)
);
CREATE TABLE user_equipment (
  user_id   bigint REFERENCES user_profile(id) ON DELETE CASCADE,
  equipment text NOT NULL,
  PRIMARY KEY (user_id, equipment)
);

-- 4. 운영 로그
CREATE TABLE unmapped_term (
  term_norm   text PRIMARY KEY,
  raw_example text NOT NULL,
  source      text NOT NULL CHECK (source IN ('recipe','user_input')),
  seen_count  integer NOT NULL DEFAULT 1,
  first_seen  timestamptz NOT NULL DEFAULT now(),
  last_seen   timestamptz NOT NULL DEFAULT now()
);
-- user_event는 Phase 3 마이그레이션에서 추가한다.
```

0002(0-4 승인): 알레르기 그룹에 법정 표시 대상 여부와 출처를 둔다. 근거는 식품 등의 표시·광고에 관한 법률 시행규칙 별표 2(`knowledge/allergens.yaml`).

```sql
-- 0002
ALTER TABLE allergen_group
  ADD COLUMN official boolean NOT NULL DEFAULT false,
  ADD COLUMN source   text    NOT NULL DEFAULT 'custom' CHECK (source IN ('law_annex2','custom')),
  ADD CONSTRAINT allergen_group_official_source CHECK (official = (source = 'law_annex2'));
```

0003(ar-1 승인 2026-10-17): 레시피 난이도·조리시간을 비워 둘 수 있게 한다(모름). 식품안전나라 원본에는 이 값이 없어, 지어내지 않고 엔진이 '모름'으로 다룬다(4-3, 4-4). 값이 있으면 기존 CHECK가 그대로 적용된다.

```sql
-- 0003
ALTER TABLE recipe
  ALTER COLUMN difficulty DROP NOT NULL,
  ALTER COLUMN cook_time_min DROP NOT NULL;
```

## 부록 C. compile_knowledge.py 동작 순서 (Phase 0-1 확정)

`kb/`의 순수 함수 `compile(paths) -> CompiledKnowledge`와 `storage`의 DB writer로 나눈다. 실행: `uv run python scripts/compile_knowledge.py [--dry-run] [--dump build/knowledge.json]`.

1. **로드**: allergens.yaml, vocab.yaml, ingredients.yaml 또는 ingredients/*.yaml(정렬 순서), substitutes.yaml, config/pantry_staples.yaml을 `yaml.safe_load`로 읽는다. 항목마다 (파일, 순번)을 기록하고, 단축형(문자열 별칭, 문자열 derived_from)을 정식 객체로 펼친다.
2. **검증**: 오류를 모두 모아 한 번에 보고한다. 하나라도 있으면 exit 1이고 DB는 바꾸지 않는다.
   - 스키마: 필수 필드, enum, id 형식, 알 수 없는 키, id 중복
   - 참조: is_a, derived_from, substitute 대상 존재. allergens는 base 그룹만. bundle includes 존재. pantry staple id 존재. substitute context가 vocab.techniques에 있음
   - 의미: is_processed면 derived_from 1개 이상. concept 노드에 allergens 금지. 이름과 별칭이 정규화 후 전역 유일
   - 그래프: is_a, derived_from, 두 그래프의 합집합에 순환이 없음(순환 경로 출력)
   - 경고(실패 아님): is_a 깊이 3 초과, 재료가 0개인 알레르기 그룹, derived_from이 있는데 is_processed 미지정
3. **그래프 확장**(메모리)
   - `ingredient_ancestor`: is_a 전이 폐포와 최소 depth
   - `ingredient_contains`: 재료 x가 포함(가능)하는 재료 집합. is_a 조상과 derived_from 원천을 전이적으로 따라간다(certainty는 경로상 최솟값, via 기록). x 자신이나 x의 derived_from 원천에 is_a 하위 개념이 있으면 그 하위 개념도 possible로 포함한다(레시피의 "젓갈류" → 새우젓 → 새우). is_a 부모를 거쳐서는 하위로 내려가지 않는다(새우는 오징어를 포함하지 않음). 단조 증가 고정점 반복으로 계산한다.
   - `allergen_closure(g)`: x 또는 contains(x)의 원소 중 g를 직접 가진 것이 있으면 x를 포함한다. certainty와 via를 기록하고, bundle은 멤버 closure의 합집합으로 펼친다. possible도 포함한다.
   - substitute 엣지를 정리하고 pantry staple 플래그를 반영한다.
4. **산출물**: 정렬된 결정적 구조의 `CompiledKnowledge`. `--dump`면 JSON으로 쓴다(검수표 생성, diff용). `--dry-run`이면 리포트만 출력하고 끝낸다.
5. **DB 반영**(단일 트랜잭션)
   - `knowledge_build` 행을 추가한다.
   - ingredient와 allergen_group은 upsert한다. YAML에서 사라진 재료가 recipe_ingredient, user_pantry, user_preference(target_type ingredient)에서 참조 중이거나, 사라진 알레르기 그룹이 user_preference(target_type allergen_group)에서 참조 중이면 실패하고 참조 목록을 출력한다. 아니면 삭제한다. user_preference.target_id는 FK가 없어서, 막지 않으면 사용자의 알레르기·불선호 설정이 조용히 무효가 되기 때문이다(0-3에서 승인).
   - 나머지 지식 테이블(alias, relation, ingredient_allergen, group_member, ancestor, contains, closure)은 모두 지우고 다시 넣는다.
   - 같은 입력이면 같은 DB 상태가 된다(멱등).
6. **리포트**: 개수, 경고, confidence: low 항목 수, build id를 출력한다.

0-2 컴파일러 테스트에 넣을 불변식: 새우젓 ∈ closure(shrimp), 김치 ∈ closure(shrimp)(possible), 된장의 대두는 definite이고 밀은 possible, 새우 ∌ 오징어, 순환이 있으면 실패, 알 수 없는 키면 실패, 별칭이 충돌하면 실패.

---

## 부록 D. 시각화 부가 트랙 viz (2026-10-03 사람 승인)

목표: API 서버가 `/viz`로 제공하는 정적 3D 페이지(HTML+JS 한 벌, 3d-force-graph CDN, 빌드 도구 없음)에서 컴파일된 지식+레시피를 4층 그래프로 탐색하고, 프로필(골든셋 페르소나 + 저장 프로필) 하나의 추천 과정을 6단계로 재생한다. **화면은 판정하지 않는다.** 엔진이 계산한 값(trace)을 색과 위치로만 바꾼다. 엔진 판정 로직과 `tests/allergy/`는 바꾸지 않는다.

### D-1. 층 배치(서버가 `layer`로 내려줌)

아래 표는 "평면" 배치다. 기본 화면은 D-9의 "나무" 배치이고, 화면에서 평면으로 바꿀 수 있다(층 번호 `layer`는 그대로).

| 층 | 노드 | 규칙 |
| --- | --- | --- |
| 1 | 알레르기 그룹 | 기본 그룹 안쪽 원, 묶음 바깥 원. 법정/자체/묶음을 색·모양으로 구분 |
| 2 | 원천 재료·분류 | derived_from이 **없는** 재료(concept 포함) |
| 3 | 가공품 | derived_from이 **하나라도 있는** 재료(확정). `is_processed: false`인 재료(콩나물 등)는 툴팁에 "가공품 아님" |
| 4 | 레시피 | cuisine별 구역, main 재료 쪽으로 당김 |

y는 층으로 고정(`fy`), x·z만 force로 계산하고 warmup 뒤 시뮬레이션을 멈춘다. 초기 카메라는 위에서 35도 내려다보는 각도이고, 그 각도에서 층이 덜 겹치도록 층 간격을 360으로 둔다. 3층 가공품은 원천 재료 쪽 인력보다 분류 구역 배치를 우선한다. 층·구역·노드 라벨은 화면에서 일정한 픽셀 크기다(viz-3 보완).

### D-2. 간선

is_a(하위 → 상위), derived_from(가공품 → 원천, certainty), allergen(재료 → 기본 그룹, `ingredient_allergen` 직접 지정, certainty), bundle_member(묶음 → 기본 그룹), uses(레시피 → 재료, role·optional, 역할별 색). 링크 id는 `isa:a>b`, `der:a>b`, `alg:a>g`, `mem:b>g`, `use:recipe#line_no`. 노드 id는 `ing:`, `ag:`, `rcp:` 접두어.

### D-3. API(읽기 전용)

- `GET /graph?recipes=none|published|all&max_recipes=N`: 노드·간선. 데이터 reload 때 한 번 만들어 캐시, ETag(304). 재료 노드 `allergens`는 기본 그룹 closure 행(certainty, via, `path_links`: 재료 → 그룹 순서 링크 id), 레시피 노드 `allergens`는 재료 줄 × 기본 그룹 closure 조인(certainty, `optional_only`, hits). 둘 다 표시용이며 판정하지 않는다(viz-3 보완).
- `POST /recommend`: `profile_id` 또는 `persona_id` 중 정확히 하나(둘 다·없음 422, 모르는 persona 404). `trace: true`면 기존 응답 + `trace`(user 요약, pantry: input·staples·owned(상속 근거), candidates(후보 근거 줄), exclusions(사유, 재료, target, 묶음이면 실제 걸린 기본 그룹 `source_group`, certainty, via, `path_links`), excluded(레시피별 대표 사유), scored(통과 후보 전부: breakdown, weighted, score_rank, final_rank, moved_by_diversity), limit). `trace` 생략 시 응답은 기존과 같다.
- `GET /personas`: 골든셋 페르소나 목록. 로더는 `storage/personas.py`(데이터 파일은 `tests/golden/personas.yaml`).
- `GET /viz`: 정적 페이지.

### D-4. trace 생성 위치

`engine/recommend.py`의 파이프라인 본문을 하나의 내부 함수로 옮기고 `recommend()`(결과만)와 `trace()`(결과 + `engine/trace.py`의 `RecommendTrace`)가 같은 코드 경로를 쓴다. 판정·점수·정렬 코드는 이동만 한다. 추가 계산은 보유 재료의 `ancestors` 사전 조회뿐(재귀 탐색 없음). id 접두어·path_links·source_group·라벨은 `api/viz.py` 표시 계층이 컴파일 결과를 조회해 붙인다.

### D-5. 6단계 재생

1 보유 재료(상속 포함) 강조 → 2 후보 레시피 강조 → 3 제외: 알레르기는 그룹에서 via 경로를 따라 빛이 올라가고 레시피가 빨갛게 가라앉음, 절대 불선호는 주황, 매운맛·조리기구·시간·음식 종류는 회색 → 4 통과 레시피가 점수만큼 상승(hover: I·K·T·P·D·M) → 5 순위 표시(다양성 보정 이동 표시) → 6 추천 카드. 이전/다음/자동재생. 프로필 패널에서 보유 재료를 빼거나 더할 수 있고, 바꾸면 `POST /recommend`의 `pantry`(기존 필드)로 보낸다(후보가 아닌 레시피는 필터 대상이 아니므로, 특정 레시피의 제외 경로를 보려면 그 레시피가 후보가 되게 보유 재료를 바꾼다). 재생 중에는 관련 없는 노드·간선을 선택 강조보다 더 흐리게 한다. trace에는 4단계 표시용 `breakdown_labels`를 함께 싣는다(viz-4).

### D-6. 성능(목표: 레시피 1천 개)

레이아웃 고정, 레시피-재료 간선 기본 숨김, 강조는 재질만 변경(graphData 재설정 금지), 라벨은 hover·검색·상위 순위만, 입자는 현재 경로만, `/graph` 캐시·ETag. 측정: bench 합성 생성기로 레시피 1천 개 그래프 → 로딩 3초 이내, 회전 30fps 이상. 1만 개 대응(Points 렌더링 등)은 범위 밖.

viz-5 결과(2026-10-03, 사람 결정): 회전 111fps 통과, 로딩 3.1~4.9초로 3초 미달(원인: 첫 화면 전 force warmup 1.6~2.5초). 시각화는 추천 과정을 보여 주는 시연·설명용이고 실제 웹앱은 그래픽 없이 엔진 응답(p95 200ms)만 기준이므로, 로딩 3초는 통과 조건에서 빼고 측정값만 기록한다. 실제 시연 데이터(레시피 50개)는 1.2~1.4초. 개선(서버 배치 계산 등)은 progress.md "다음 단계 제안".

### D-7. 단계

viz-0 설계 기록 → viz-1 `/graph` → viz-2 trace·persona → viz-3 3D 온톨로지 화면 → viz-4 워크플로 재생 → viz-5 성능 측정·문서. 테스트는 `tests/viz/`: 그래프 개수·층 규칙·closure 경로 걷기(via 연속 쌍이 링크로 이어짐), trace 제외 결과 = 일반 `/recommend` 제외 결과, 후보 = 통과 ∪ 제외, 순위 = items 순서.

### D-8. 레시피 출처 구분과 표시 전용 레시피 (int-2, 2026-10-16 사람 승인)

- 레시피 노드에 `origin`(출처 id), `engine`(엔진 적재 여부), `lines`(재료 줄 수), `unmapped_lines`(미매칭 줄 번호·원문)를 싣는다. 출처 규칙은 `config/display.yaml` `graph_recipe_origins`(위에서부터 처음 맞는 것: `source` 값 일치, 또는 `dataset` 원본의 영상 URL 일치). 표시 전용이며 판정에 쓰지 않는다.
- `GET /graph?display=true`: `display_dir`가 있는 출처(식품안전나라)의 레시피를 `kb.recipes.load_display_specs`로 읽어(draft 검증만, 적재 거부 규칙 없음, 지식과 맞지 않는 파일만 건너뜀) 같은 컴파일 closure로 재료·알레르기에 연결해 함께 싣는다(`engine: false`). 처음 요청 때만 읽고 캐시한다. 응답에 출처별 레시피 수(`origins`)와 `stats.display_recipes`.
- 맛 정보가 없는 레시피는 `spicy: null`. 추천·trace·재료로 찾기는 적재된 레시피만 쓴다(표시 전용 레시피는 추천에 나오지 않음).
- 화면: 레시피 원기둥 색 = 출처, 상단 "출처" 토글(출처별 표시·숨김), "표시 전용 포함"(`?display=1`로 다시 불러옴). 정보 패널에 출처·추천 사용 여부·미매칭 줄 원문.

### D-9. 나무 배치 (int-3, 2026-10-16 사람 요청·승인)

레시피가 1천 개를 넘으면 평면 원판 한 장에 겹쳐 읽기 어렵다. 층 구조를 나무로 바꿔 보인다. 표시 전용이며 판정·데이터는 바뀌지 않는다.

| 부위 | 층 | 규칙(`viz/tree.js`, 결정적·force 없음) |
| --- | --- | --- |
| 뿌리 | 1 알레르기 그룹 | 줄기 밑에서 아래·바깥으로. 묶음 그룹은 더 깊고 넓게 |
| 줄기 | 2 원천 재료·분류 | 좁은 기둥. 분류(category)마다 같은 방향, 높이를 따라 쌓음. concept는 줄기 꼭대기 가운데 |
| 가지 | 3 가공품 | 줄기 꼭대기에서 분류 방향으로 위·바깥으로 뻗음(줄기와 같은 분류 각도) |
| 잎 | 4 레시피 | 반구(돔) 표면의 고른 점(해바라기 배치)에 방위각 순으로 배정 |

- 잎 배치 기준 두 가지(화면 "배치" 선택, `?layout=`): `tree-ingredient`(기본) 레시피가 매달린 재료(주재료 줄 중 번호가 가장 앞선 것, 없으면 매핑된 첫 줄)의 방향 순 → 같은 재료 레시피가 한 부채꼴. `tree-cuisine` 음식 종류별 부채꼴(폭은 레시피 수에 비례). 큰 잎 무리 이름(재료 이름·레시피 수)을 이웃끼리 높이를 엇갈려 표시. `flat` 기존 평면(D-1).
- 잔가지 = 레시피-재료 간선: "레시피-재료" 체크박스로 전부 보이기/숨기기, 숨겨도 노드를 고르면 그 노드의 간선은 보인다(기존 규칙 그대로).
- 전환은 좌표만 바꾼다(모든 노드 fx·fy·fz 고정, `d3ReheatSimulation`으로 한 번 동기화, graphData 재설정 없음). 평면은 처음 고를 때만 force warmup(비동기)을 돌리고, 평면에서 나갈 때 좌표를 저장해 다시 쓴다.
- 나무 배치는 warmup이 없어 첫 화면이 빠르다(D-6의 원인이던 warmup 1.6~2.5초가 없음). 외부 레시피 노드(부록 E)는 수관 꼭대기 위에 고정.

## 부록 E. 외부 레시피 일회성 분석 adhoc (2026-10-16 사람 승인)

목표: DB에 없는 레시피(AI가 만든 레시피, 웹에서 본 레시피 등)의 재료 목록을 붙여 넣으면, 이미 컴파일된 지식을 조회해 재료 매핑, is_a·derived_from 구조, 알레르기 경로를 보여 주고 `/viz` 그래프 위에 임시 노드로 겹쳐 그린다. 사람이 정한 범위(2026-10-16): 일회성 분석만(저장 안 함), 화면은 `/viz` 입력 카드, 사용자 판정은 선택 입력.

### E-1. 원칙

- **저장하지 않는다.** DB, `knowledge/`, `data/recipes/`, 그래프 캐시를 바꾸지 않는다. 등록하려면 기존 절차(draft YAML → 검수 → published)를 따른다.
- **결정적 규칙만 쓴다.** 재료 줄 분리는 식품안전나라 변환과 같은 `kb.foodsafety.ingredient_segments`(버리는 것은 고정 머리말 단어, 레시피 이름, 분량 표기, "…재료", 물뿐이고 버린 항목은 응답에 그대로 보여 준다). 매핑은 별칭 색인 정확 일치만. LLM·유사도 매핑 없음.
- **concept 노드에 맞은 줄은 미매칭과 같이 다룬다**(A1). 응답에는 어떤 분류에 맞았는지 보여 주고 더 구체적인 재료를 적도록 안내한다.
- **판정은 엔진의 기존 필터를 그대로 쓴다.** 사용자를 주면 임시 `Recipe`(모든 줄 role sub, 선택 아님)를 만들어 `UserConstraints.check`로 판정한다. 추천과 같은 기준이므로 possible도 제외, 미매칭 줄이 있으면 알레르기 사용자에게 제외. 매운맛·조리기구·조리시간·음식 종류는 입력에 정보가 없어 판정하지 않는다고 응답에 밝힌다. 제외되면 `logs/exclusions.jsonl`에 기록한다(recipe_id는 `adhoc_<해시>`).
- 구조 표시(줄별 알레르기 경로, is_a 조상, derived_from 원천)는 컴파일 결과 행을 조회만 한다(부록 D와 같은 표시 계층, 요청 중 그래프 탐색 없음).

### E-2. API

`POST /analyze-recipe`

- 입력: `title`(1~100자), `text`(재료 원문, 줄·쉼표 구분) 또는 `ingredients`(문자열 목록) 중 정확히 하나, 사용자는 `profile_id`·`persona_id`·`allergen_groups` 중 최대 하나(없으면 구조만). 모양 오류 422, 재료를 하나도 찾지 못함·모르는 알레르기 그룹 400, 없는 프로필·페르소나 404.
- 출력: `recipe_id`(`adhoc_<해시>`), `lines`(줄 번호, 원문, 이름, `status`: mapped·concept·unmapped, 재료 id·이름, is_a 조상, derived_from 원천, 기본 그룹 알레르기 행: certainty·via·path_links), `skipped`(버린 항목), `allergens`(레시피 단위 요약, `/graph` 레시피 노드와 같은 모양), `counts`(전체·매핑·미매칭·concept), `judgement`(사용자를 준 경우: `excluded`, 제외 사유 목록(부록 D-3 trace exclusions와 같은 모양), 판정한 항목·판정하지 않은 항목), `graph`(겹쳐 그릴 노드·간선), `notice`, `disclaimer`.
- 그래프 겹쳐 보기: 레시피 노드 `rcp:adhoc_<해시>`(kind recipe, `adhoc: true`), 매핑된 줄은 `uses` 간선(`use:adhoc_<해시>#줄번호`), 미매칭·concept 줄은 온톨로지에 연결되지 않은 노드 `raw:adhoc_<해시>#줄번호`(kind unmapped)와 `unmapped` 간선.

### E-3. 화면

`/viz` 오른쪽 패널의 "외부 레시피 분석" 카드: 제목, 재료 원문, 판정 기준(구조만 / 페르소나 / 저장 프로필) → 분석. 결과는 요약(매핑 수, 걸리는 알레르기), 판정, 줄별 표(매핑 재료·분류·알레르기 경로), 버린 항목. 그래프에는 레시피 층 위 가운데에 임시 레시피 노드를 고정 위치로 추가하고 선택해 알레르기 경로를 강조한다(기존 선택 강조 재사용). 다시 분석하거나 지우면 이전 임시 노드를 뺀다. 데이터가 바뀌는 경우라 `graphData`를 다시 넣되 warmup 없이 넣어 기존 배치는 움직이지 않는다.

### E-4. 테스트

`tests/api/test_analyze_recipe.py`: 매핑·concept·미매칭 구분, 버린 항목, 알레르기 행이 `/graph` 재료 노드와 같음, path_links가 실제 링크, 저장 안 함(`/graph` ETag·레시피 수 불변), 사용자 판정이 추천 필터와 같은 결과(possible 제외, 미매칭 제외, 알레르기 없는 사용자는 미매칭이어도 통과), 입력 검증, 제외 로그. `tests/allergy/`는 바꾸지 않는다.

### E-5. 범위 밖

저장(draft 등록), 미매칭 표기 누적(`unmapped_term`), 자유 문장(LLM) 해석, role·선택 재료 추론. 필요하면 progress.md "다음 단계 제안"에 적는다.
