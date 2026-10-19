# 추천 v2 로직 명세 (언어와 무관)

이 문서는 `engine/v2/`(Python)의 동작을 다른 언어로 그대로 옮길 수 있게 규칙 단위로 적은 것입니다. 옮긴 결과는 공용 시험 세트(`tests/shared/v2_cases.json`, 10장)를 모두 통과해야 합니다.

- 기준: 이 저장소 main(이 문서가 들어간 커밋). 코드와 문서가 다르면 **코드와 공용 시험 세트가 기준**입니다. 이 문서를 고쳐 주세요.
- 이 문서는 "무엇을 어떤 순서로 계산하는가"를 다룹니다. API 형식은 `docs/integration/recipe_v2_api.md`, 배경과 결정은 `docs/plan.md` 부록 G와 `docs/decisions.md` D7~D10에 있습니다.
- 표기: "목록 순서"는 배열의 원래 순서, "id 순"은 문자열의 **코드 포인트(바이트) 오름차순**입니다. 로케일 비교(`localeCompare` 등)를 쓰면 안 됩니다.

## 0. 전체 흐름

```
입력: 사용자 정보 6가지(profile) + 요청(request) + 데이터 묶음(knowledge·recipes·config)
 1. profile → 사용자 문맥(user) 변환·검증               (2장)
 2. 제외(규칙)  : 알레르기·미매칭·절대 안 먹음·매운맛…  (3장, 4장)
 3. 재료 충족   : 보유·기본 양념·상위 재료·대체재        (5장)
 4. 후보        : random / pantry / dish                (6장)
 5. 순위        : ranking.mode = jev  → Jev 항목별 판단 (8장)
                  실패·끔·Jev 없음  → 규칙 점수        (7장)
 6. 설명        : 부족 재료·대체 안내·안내 코드          (9장)
```

**안전 불변식(예외 없음)**: 2단계에서 제외된 레시피는 이후 어떤 단계에서도 결과에 들어오지 않습니다. Jev는 제외를 통과한 후보 안에서 순서만 정합니다.

## 1. 입력 데이터 (데이터 묶음)

`scripts/export_v2_bundle.py`가 실제 데이터를, `scripts/make_shared_cases.py`가 시험용 작은 데이터를 같은 형식으로 만듭니다. 형식의 정의는 `storage/v2_bundle.py`입니다.

| 파일·키 | 내용 |
|---|---|
| `knowledge.ingredient_names` | 재료 id → 대표 이름 |
| `knowledge.alias_index` | 정규화한 이름·별칭(2-3) → 재료 id |
| `knowledge.ancestors` | 재료 id → {is_a 조상 id: 깊이(1부터)}. 컴파일 시 계산됨. 요청 중 그래프 탐색 금지 |
| `knowledge.contains` | 재료 id → {포함하는 재료 id: {certainty: definite·possible, via}}. is_a 상위와 derived_from(파생) 원천을 컴파일한 것 |
| `knowledge.allergen_closure` | 알레르기 그룹 id(기본·묶음) → {재료 id: {certainty, via}} |
| `knowledge.allergen_groups` | [{id, name, kind: base·bundle, members}] |
| `knowledge.substitutes` | 레시피가 요구하는 재료 id → [{to, context(조리 기법 목록, 비면 항상), ratio(없으면 null)}] |
| `knowledge.pantry_staples` | 기본 양념 id 목록(보유로 간주) |
| `knowledge.concept_ids` | 분류 전용 노드(예: 해산물). 보유 재료로 쓸 수 없음 |
| `knowledge.ingredient_meta` | 재료 id → {category, is_processed, confidence}. 화면 안내(성분표 확인)용 |
| `recipes[]` | {id, title, cuisine(`한식`·`일식`·`중식`·`양식`·`미분류`), difficulty(1~3·null), cook_time_min(정수·null), status(published·draft), taste({spicy,salty,sweet,sour,umami,savory} 각 0~5 또는 null), required_equipment, techniques, ingredients[{line, ingredient(id·null=미매칭), role(main·sub·seasoning·garnish), optional, raw_text}]} |
| `config.weights` | `config/weights.yaml`(규칙 점수) |
| `config.engine` | `config/engine.yaml`(`serve_draft_recipes` 등) |
| `config.v2` | `config/v2.yaml`(형태·Jev·매운맛 추정·화면 문구) |
| `config.display` | `config/display.yaml`(면책·성분표 확인 등 화면 문구, 실제 데이터 묶음에만) |
| `derived.not_spicy_recipe_ids` | 4장의 결과. 옮긴 쪽이 다시 계산해 같은지 확인용 |

**추천 대상 레시피(catalog)**: `status == published`이거나 `config.engine.serve_draft_recipes == true`인 레시피를 **id 순**으로 정렬한 목록입니다. 현재 설정은 draft 포함입니다.

## 2. 사용자 정보 변환과 검증

### 2-1. profile 6가지 → user

| profile | user |
|---|---|
| `allergens`(그룹 id) | `allergen_groups` |
| `never_eat`(재료 id) | 절대 안 먹음 목록(hard) |
| `likes` / `dislikes`(재료 id) | 재료 선호 +1 / −1(soft, 강도 1.0) |
| `cuisine_likes` / `cuisine_dislikes` | 음식 종류 선호 +1 / −1(soft) |
| `spicy_level` 0~4 | 매운맛 `preferred = max = spicy_level` |
| `spicy_level` 5 또는 null | 매운맛 정보 없음(한도도 선호도 없음) |
| `skill_level` 1~3, null | 그대로, null이면 2 |
| (요청) `pantry` | 보유 재료 id |
| (호출자) 조리기구 | 6가지 입력에 없으므로 **어휘의 모든 조리기구를 보유**로 둠 |

### 2-2. 입력 오류(요청 거부)

| 조건 | 결과 |
|---|---|
| 같은 재료가 likes와 dislikes에 동시에 | 오류 |
| 같은 음식 종류가 cuisine_likes와 cuisine_dislikes에 동시에 | 오류 |
| spicy_level이 0~5 밖, skill_level이 1~3 밖 | 오류 |
| 모르는 알레르기 그룹 id(`allergen_closure` 키에 없음) | 오류(무시하면 알레르기 제외가 꺼지므로) |
| 모르는 never_eat 재료 id | 오류 |
| 모르는 likes·dislikes 재료 id | 오류 |
| `mode == dish`인데 query가 비었음 | 오류 |

- **보유 재료 정리**: 지식에 없는 id와 분류 노드는 버립니다(오류 아님). API 계층은 모르는 pantry id를 400으로 거부합니다.
- likes·never_eat가 알레르기와 겹치는 것은 오류가 아닙니다. 제외가 이깁니다.

### 2-3. 이름 정규화 `normalize_term`

유니코드 NFC 정규화 → 모든 공백 문자 제거 → 라틴 문자 소문자화. 별칭 색인(`alias_index`) 키와 같은 규칙입니다.

## 3. 제외 규칙

레시피 하나에 대해 아래를 모두 검사하고, 사유가 하나라도 남으면 제외합니다. 사유는 `(사유 코드, 재료 id, 대상)`이 같으면 한 번만 기록합니다(미매칭은 줄마다 기록).

**재료 줄마다**(선택 재료·고명·기본 양념 줄 포함)

1. 재료 id가 null이거나 지식에 없음 → 사용자에게 알레르기가 하나라도 있으면 `unmapped_ingredient`. 이 줄의 나머지 검사는 건너뜀.
2. 사용자의 알레르기 그룹 g마다, `allergen_closure[g]`에 이 재료가 있으면 `allergen`(certainty와 관계없이 possible도 제외).
3. 절대 안 먹음 재료 t마다:
   - 이 재료가 t이면 `hard_dislike_ingredient`(definite)
   - 아니고 `contains[이 재료]`에 t가 있으면 그 certainty로 `hard_dislike_ingredient`
   - **v2 규칙(D8)**: certainty가 possible인 사유는 제외 사유에서 빼고, 레시피에 "포함 가능" 표시(`dislike_possible`)만 남깁니다.

**레시피 전체**

4. 음식 종류가 절대 비선호 음식 종류에 있음 → `hard_dislike_cuisine`. 6가지 입력에는 없고 API 내부 프로필에서만 생깁니다.
5. 매운맛 한도 L(사용자 매운맛 max 중 최솟값)이 있고 L < 5일 때:
   - 레시피 맛이 null → `spicy_limit`. 단 **4장의 "맵지 않음" 추정 레시피면 이 사유를 뺍니다(D9)**.
   - 레시피 `taste.spicy > L` → `spicy_limit`
6. `required_equipment − 보유 조리기구`가 비어 있지 않음 → `equipment`
7. `time_is_hard`이고 `cook_time_min > max_time_min`(조리시간이 null이면 검사 안 함) → `time`

**대체재 안전성**: 5장에서 쓰는 "위험한 재료"는 지식에 없는 재료, 알레르기 hit가 있는 재료, 절대 안 먹음 hit가 있는 재료(possible 포함)입니다. 대체 안내는 보수적으로 둡니다.

## 4. 매운맛 추정 (D9)

`config.v2.spicy_inference.enabled`일 때, catalog의 레시피 중 다음을 **모두** 만족하면 "맵지 않음(매운맛 0)"으로 봅니다. 레시피마다 한 번 계산해 두고 재사용합니다.

1. 맛이 null이다(맛을 아는 레시피는 추정하지 않음).
2. 재료 줄이 하나 이상 있다.
3. 제목에 `title_markers`의 어떤 문자열도 들어 있지 않다(부분 문자열 검사).
4. 모든 줄의 재료 id가 null이 아니고 지식에 있다.
5. 어떤 줄의 재료 id도 `markers`에 없고, 그 재료의 `ancestors` 키와 `contains` 키에도 `markers`가 없다.

추정 결과는 세 곳에 씁니다.
- 3장 5번(매운맛 한도)
- 7-4의 맛 점수 보정
- 6-3의 키워드 맛 조건과 8-6의 후보 요약 매운맛(0)

## 5. 재료 충족

- `from_pantry` = 보유 재료 ∪ 그 재료들의 `ancestors` 키.
  - 삼겹살을 보유하면 "돼지고기"를 충족합니다. 반대 방향은 충족이 아닙니다.
- `owned` = (보유 재료 ∪ 기본 양념) ∪ 그 재료들의 `ancestors` 키.
- 줄의 상태:
  - 재료 id가 null → `missing`
  - id ∈ owned → `owned`
  - 그 밖: `substitutes[id]` 중에서 아래를 모두 만족하는 대체를 찾습니다. 있으면 `substitute`, 없으면 `missing`입니다.
    - `to`가 **보유 재료 원본**에 있다(상위 재료 확장 없음).
    - `context`가 비었거나 레시피 `techniques`와 겹친다.
    - `to`가 위험한 재료가 아니다(3장).
    - 여럿이면 `ratio`(null이면 `weights.coverage.substitute_credit`)가 큰 것, 같으면 `to`의 id 순으로 첫 번째를 고릅니다.
- **꼭 필요한 부족 수** `required_missing` = 상태가 missing이고, 역할이 main·sub·seasoning이고, 선택이 아닌 줄의 수입니다(미매칭 줄 포함, 고명·선택 줄 제외).

## 6. 후보

### 6-1. random

1. catalog를 `seed`로 섞습니다. seed가 없으면 엔진이 정해 결과에 담습니다.
2. 섞은 순서대로 3장을 검사해, 통과한 레시피를 필요한 수만큼 모읍니다.
   - 규칙 경로: `limit`개
   - Jev 경로: `max(ranking.pool_size, limit)`개
3. 제외 기록은 검사한 레시피에 대해서만 남습니다.

섞는 방법(난수 생성기)은 언어마다 달라도 됩니다. 같은 구현 안에서 같은 seed면 같은 결과면 충분합니다. 공용 시험 세트는 이 부분을 순서가 아닌 집합으로 비교합니다.

### 6-2. pantry (지금 바로 / 조금만 사면)

1. **후보 근거 역할**: 레시피에 main 줄이 하나라도 있으면 main, 없으면 sub입니다.
2. 아래 조건을 만족하면 후보입니다.
   - 레시피가 catalog에 있다.
   - 근거 역할의 줄 중 하나라도 ① 상태가 substitute이거나 ② 상태가 owned이면서 재료 id ∈ from_pantry다(기본 양념만으로는 후보가 되지 않음).
3. 후보를 id 순으로 3장 검사합니다(제외 기록은 모든 후보에 대해 남김).
4. `required_missing` = 0이면 `ready`, 1 ~ `v2.pantry.near_max_missing`(2)이면 `near`, 그보다 많으면 버립니다.

### 6-3. dish (요리명·느낌)

**질의 해석**(`min_len = v2.dish.min_term_len` = 2)
- `norm` = normalize_term(질의 전체)
- `terms` = 질의를 공백으로 나눈 각 낱말을 정규화해 길이 ≥ min_len인 것(중복 제거, 처음 나온 순서)
- `ingredient_ids` = `alias_index`에서 키 길이 ≥ min_len이고 `norm`에 부분 문자열로 들어 있는 재료(분류 노드 제외)
- `rules` = `v2.dish.keywords` 중 `match`의 어떤 낱말(정규화)이 `norm`에 들어 있는 규칙
- `anchors` = catalog 중 정규화한 제목이 `norm`과 같은 레시피

**유사도 항목**(레시피 r마다, 0~1)
- `title`
  - 정규화 제목 t == norm → 1
  - (len(norm) ≥ min_len이고 norm ⊂ t) 또는 (len(t) ≥ min_len이고 t ⊂ norm) → 0.8
  - 그 밖: terms가 비면 0, 아니면 0.6 × (t에 들어 있는 terms 수 / terms 수)
- `ingredient`(ingredient_ids가 있을 때): |ingredient_ids ∩ (r의 재료 id ∪ 그 ancestors)| / |ingredient_ids|
- `keyword`(rules가 있을 때): 걸린 규칙의 조건마다 점수를 매겨 평균합니다.
  - 맛 조건(차원 d, min, max): 레시피 맛이 있으면 범위 안 1·밖 0. 맛이 null이면 d가 spicy이고 "맵지 않음" 추정 레시피일 때 (min이 없거나 ≤ 0이면 1, 아니면 0), 그 밖에는 0.5.
  - 음식 종류 조건: 같으면 1, 아니면 0
  - `title_any`: 제목(원문)에 하나라도 들어 있으면 1, 아니면 0
- `anchor`(anchors가 있을 때): anchors 각각과의 유사도 중 최댓값.
  - 같은 레시피면 1.
  - 아니면 (맛 유사도 + 주재료 자카드 + 음식 종류 일치) / 3.
  - 맛 유사도는 둘 다 맛이 있으면 1 − (6차원 차이 절댓값 평균)/5, 아니면 0.5입니다. 주재료는 role이 main인 줄의 재료 id 집합입니다.

**결합**
- 켜진 항목(`active`) = [title(catalog 중 title > 0인 레시피가 하나라도 있을 때)] + ingredient·keyword·anchor 중 질의에서 생긴 것
- active가 비면 결과 없음(`dish_no_match`)
- S = Σ(w_k × 항목_k) / Σ w_k (k ∈ active, 가중치 `v2.dish.similarity`)

**관련 후보(pool)**
- S > 0인 레시피를 (S 내림차순, id 순)으로 보면서 3장을 검사하고, 통과한 것을 `v2.dish.pool_size`(40)개까지 모읍니다.
- 검사 중 제외된 레시피의 S 최댓값을 `best_excluded`로 기억합니다.
- pool이 비면: `best_excluded`가 있으면 `dish_excluded`, 아니면 `dish_no_match`로 결과 0개입니다. Jev 경로는 8-4에서 보충을 시도합니다.
- pool의 첫 S보다 `best_excluded`가 크면, 결과 안내에 `dish_excluded`를 붙입니다(찾는 요리가 못 먹는 재료 때문에 빠졌음).

## 7. 규칙 점수 경로 (Jev 실패·끔·Jev 없음일 때)

### 7-1. 항목(모두 0~1, 설정 `config.weights`)

| 항목 | 계산 |
|---|---|
| I 재료 보유 | 역할 가중치(`coverage.role_weight`: main 3, sub 2, seasoning 1, garnish는 없음 → 제외)가 있는 줄 중 선택 줄 제외(`exclude_optional`), 기본 양념 재료 줄 제외(`exclude_pantry_staples`). need += w. owned면 have += w, substitute면 have += w × ratio(null이면 `substitute_credit`). 미매칭 줄은 need에만 들어감. need가 0이면 1 |
| K 음식 종류 | soft 음식 종류 선호: 좋아함 `cuisine.like`(1.0), 싫어함 `cuisine.dislike`(0.1), 같은 종류에 둘 다 있으면 작은 값. 없으면 `cuisine.neutral`(0.5) |
| T 맛 | 선호 정도가 있는 맛 차원이 없으면 0.5. 레시피 맛이 null이면 `taste.unknown`(0.5). 그 밖: 1 − (Σ w_d × |선호_d − 레시피_d| / Σ w_d) / 5, 최소 0 |
| P 재료 선호 | soft 재료 선호 값 = 0.5 + 0.5 × 극성 × 강도(같은 재료에 여럿이면 최솟값). 줄 가중치 = 선택 줄이면 `ingredient_preference.role_weight.optional`(0.2), 아니면 역할 가중치(main 1.0, sub 0.6, garnish 0.2, seasoning 없음 → 제외). 미매칭 줄 제외. 줄의 값 = 그 재료에 대한 선호, 없으면 ancestors 중 가장 얕은 깊이의 조상 선호(같은 깊이면 최솟값), 없으면 0.5. 선호가 하나도 없으면 0.5. 가중 평균, 가중치 합이 0이면 0.5 |
| D 난이도 | 레시피 난이도 null → `difficulty.unknown`(0.5). 아니면 clamp(난이도 − 실력, −2, 2)의 표값(−2: 0.8, −1: 0.9, 0: 1.0, 1: 0.4, 2: 0.1) |
| M 시간 | 희망 시간 w 없음 → 1. 조리시간 null → `time.unknown`(0.5). t ≤ w → 1. w ≤ 0 → 0. 그 밖 max(0, 1 − (t − w)/w) |

**규칙 점수** = Σ 가중치 × 항목. 가중치는 `weights.weights`(I 0.30, K 0.20, T 0.15, P 0.15, D 0.10, M 0.10)입니다.

**맛 보정(v2, D9)**: "맵지 않음" 추정 레시피이고, 사용자의 선호 정도가 있는 맛 차원이 매운맛 하나뿐이면, T = max(0, 1 − 선호/5)로 바꾸고 점수도 그만큼 다시 계산합니다.

### 7-2. 정렬과 다양성(pantry 규칙 경로)

**정렬 키**
1. −round(점수, 3)
2. −round(I, 3)
3. 부족 재료 수(missing이면서 선택 아닌 줄의 서로 다른 재료 id 수, null 제외)
4. (조리시간이 null인가, 조리시간 또는 0)
5. id 순

**다양성**(`diversity`: top_n 10, max_same_cuisine 5, max_same_main_ingredient 3, max_score_gap 0.1)
- 앞에서부터 top_n개를 고릅니다. 남은 것 중 맨 앞(head)이 한도를 넘으면, head와 점수 차가 gap 이하이면서 한도를 넘지 않는 첫 레시피를 대신 고릅니다. 그런 레시피가 없으면 head를 고릅니다.
- 한도는 같은 음식 종류 수, 같은 main 재료 수(main 재료가 여럿이면 각각)입니다.
- top_n 이후는 원래 순서입니다.

### 7-3. 형태별 규칙 경로 결과

- **random**: 6-1의 순서 그대로. 항목별 점수는 7-1로 계산해 붙입니다.
- **pantry**: ready 묶음, near 묶음 각각 7-1 → 7-2. 결과는 ready 전체 다음 near 전체, `limit`개까지입니다.
- **dish**: pool 각 레시피의 최종 점수 = `v2.dish.s_weight`(0.7) × S + (1 − 0.7) × 규칙 점수. breakdown에 S를 더합니다. (−round(최종, 6), id 순)으로 정렬하고 `limit`개입니다.
- pantry·dish 규칙 경로 결과의 안내 코드에는 `rerank_off`가 붙습니다(random에는 붙지 않음). 이전 재정렬 기능이 꺼졌다는 뜻이고, 운영 구성에서는 항상 꺼져 있습니다.

## 8. Jev 경로 (`config.v2.ranking.mode == jev`)

다음을 모두 만족하면 Jev 경로를 씁니다. 하나라도 아니면 7장입니다.
- Jev 판단기가 있다(인증키가 있음).
- 요청의 `rerank`가 false가 아니다.

Jev 경로가 **실패**하면, 7장으로 처음부터 다시 계산하고 안내 코드 맨 앞에 `jev_unavailable`을 붙입니다. 실패는 판단 호출 오류·시간 초과, 쓸 수 있는 답이 하나도 없음, 요리 찾기에서 pool도 보충도 없음을 뜻합니다.

### 8-1. 판단 항목(사용자 정보가 있는 것만, 이 순서)

1. `request`: mode가 dish일 때
2. `taste`: 매운맛 선호(0~4)가 있을 때. **5나 없음이면 묻지 않음**
3. `ingredients`: 좋아하는·싫어하는 재료가 하나라도 있을 때
4. `cuisine`: 좋아하는·싫어하는 음식 종류가 하나라도 있을 때
5. `skill`: 항상
6. `pantry`: mode가 pantry일 때

### 8-2. 판단(judged)

- 후보 목록에 요청 안에서만 쓰는 key `c0, c1, …`를 목록 순서대로 붙여 한 번에 판단을 요청합니다.
- 받은 답 중 보낸 key·항목만 씁니다.
- 후보마다:
  - 답이 있는 항목의 점수 s_a(0~1)와 확신도로 J = Σ w_a s_a / Σ w_a를 계산합니다. 가중치는 `ranking.aspect_weights`(request 2, 나머지 1)입니다.
  - 답이 하나도 없으면 J = 0, 확신도 0입니다.
  - breakdown = {`J_<항목>`: s_a …, `J`: J, `J_conf`: 답이 있는 항목 확신도의 최솟값(없으면 0)}. 점수 = J입니다.
- 모든 후보에 답이 하나도 없으면 실패입니다.
- (−round(J, 6), 목록 순서)로 정렬합니다.

### 8-3. 형태별 후보 → 판단

- **random**: 6-1의 후보를 판단 → 정렬 → `limit`개.
- **pantry**:
  1. 6-2의 각 묶음을 (−가진 재료로 채운 줄 수, id 순)으로 정렬합니다. "가진 재료로 채운 줄 수"는 상태가 owned이고 재료 id ∈ from_pantry인 줄의 수입니다.
  2. ready 앞에서 `ranking.pool_size`개, near 앞에서 max(0, min(pool_size, limit) − ready 개수)개를 고릅니다.
  3. 둘을 합쳐 **한 번**에 판단합니다.
  4. 결과는 ready(판단 순서) 다음 near(판단 순서), `limit`개입니다.
- **dish**: 8-4 → pool 앞에서 `ranking.pool_size`개를 판단 → `limit`개입니다.

### 8-4. 요리 찾기 보충(걸러내기)

pool이 `ranking.min_pool`(10)보다 적으면 다음을 합니다.
1. catalog 중 pool에 없는 레시피를 id 순으로 3장 검사합니다(이 경우 모두 검사하므로 제외 기록도 모두 남음). 통과한 것을 `ranking.screen_max`(1200)개까지 모읍니다.
2. 걸러내기(screen)로 후보마다 점수 0~1을 받습니다.
3. (점수 내림차순, **원래 순서**)로 정렬해 `pool_size − pool 개수`만큼 pool 뒤에 붙이고(S = 0), 하나라도 붙였으면 안내 코드 `jev_screened`를 붙입니다.
4. 걸러내기가 실패하거나 빈 답이면 기존 pool로 진행하고, pool도 비었으면 실패(8장 맨 앞)입니다.

### 8-5. Jev에 보내는 사용자 정보(JudgeProfile)

| 필드 | 값 |
|---|---|
| 요리 실력 | skill_level |
| 매운맛 선호 | 0~4면 그 값, 5·없음이면 보내지 않음 |
| 좋아하는·싫어하는 재료 | soft 재료 선호의 **이름**(id 순이 아니라 이름 정렬) |
| 좋아하는·싫어하는 음식 종류 | 정렬된 목록 |
| 요청 문장 | dish일 때만 |
| 보유 재료 | pantry일 때만, **위험한 재료(3장)를 뺀** 보유 재료 이름 정렬 |

**보내지 않는 것**: 알레르기, 절대 안 먹는 재료, 사용자·프로필 id, 레시피 id.

### 8-6. 후보 요약(JudgeCandidate)

| 필드 | 값 |
|---|---|
| key | c0, c1, … |
| 제목 | title |
| 음식 종류 | `미분류`면 보내지 않음 |
| 매운맛 | 맛이 있으면 taste.spicy, 없고 "맵지 않음" 추정이면 0, 그 밖에는 보내지 않음 |
| 난이도 | 있을 때 |
| 주재료 | 후보 근거 역할(6-2) 줄의 재료 이름, 중복 제거, 8개까지 |
| 부족 재료 | pantry일 때 꼭 필요한데 missing인 줄의 이름(미매칭이면 원문), 중복 제거 |

### 8-7. Jev(TypeSafe System One) 호출

`integrations/jev/judge.py`가 기준입니다.

- **연결**: `POST https://api.typesafe.ai/v1/systemone`, 헤더 `Authorization: Bearer <TYPESAFE_API_KEY>`, 본문 `{model, state, questions}`. 모델은 `v2.rerank.model`(현재 `jev-1.14.0` 고정)입니다.
- **state**(있는 것만 넣음):
  - `user_request`
  - `cooking_skill`(`beginner cook`·`intermediate cook`·`experienced cook`)
  - `spiciness_preference_0_to_5`
  - `liked_ingredients`, `disliked_ingredients`, `liked_cuisines`, `disliked_cuisines`, `ingredients_on_hand`
- **판단 질문**: 후보 × 항목마다 key `"<후보 key>__<항목>"`, `type: score`, `criteria`는 5단계 `["not at all", "weakly", "somewhat", "well", "perfectly"]`, `instructions`는 `{question: 항목별 영어 질문, recipe: 후보 요약}`입니다. 질문 문구는 코드의 `ASPECT_QUESTIONS`를 그대로 씁니다.
- **걸러내기 질문**: 후보마다 key = 후보 key, 같은 5단계, recipe는 제목과 주재료 4개입니다. `ranking.screen_chunk`(250)개씩 나눠 병렬로 요청합니다.
- **답 해석**: `type == score`인 답의 `score`(0~4, 단계 확률 가중값)를 4로 나눠 0~1로 바꾸고, `confidence`는 그대로(0~1로 자름) 씁니다. 형식이 틀린 답은 버립니다.
- **시간 한도와 재시도**: 판단과 걸러내기 각각 `ranking.timeout_ms`(8000)입니다. 429·529는 남은 시간 안에서 한 번 더 시도합니다. 인증키는 로그·오류 문구에 넣지 않습니다.

## 9. 결과와 설명

- **항목**:
  - `recipe_id`, `title`
  - `score`(소수 셋째 자리 반올림)
  - `breakdown`(각 값 셋째 자리)
  - `group`(pantry: ready·near)
  - `required_missing`(5장)
  - `missing`: missing이면서 선택이 아닌 줄의 재료 id. 줄 순서, 중복 제거, 미매칭 제외
  - `substitutions`: [필요 재료, 대신 쓸 재료], 줄 순서, 중복 제거
  - `optional_missing`
  - 레시피 안내 코드: `dislike_possible`(3장), `spicy_inferred`(사용자에게 매운맛 정보가 있고 "맵지 않음" 추정 레시피일 때)
- **요청 전체 안내 코드**(중복 제거, 생긴 순서):
  - `jev_unavailable`
  - `dish_excluded`, `dish_no_match`
  - `jev_screened`
  - `rerank_off`, `rerank_unavailable`(규칙 경로)
- **제외 요약**: 사유 코드별 레시피 수. 한 레시피가 사유 여럿이면 사유마다 셉니다. 검사한 레시피 기준입니다(6장).
- **화면 표시 계층**(판정과 무관, `api/present.py`, `config.display`):
  - **성분표 확인**: 레시피 재료 중 `ingredient_meta.is_processed`이고 `confidence == low`인 재료입니다. **알레르기가 있는 사용자에게만** 보여 줍니다.
  - **면책 문구**(`display.disclaimer`): 항상 보여 줍니다.
  - **안내 코드별 문구**: `v2.display.notes`에 있습니다.

## 10. 공용 시험 세트 (`tests/shared/v2_cases.json`)

### 10-1. 구조

```json
{
  "format_version": 1,
  "equipment": ["냄비", "프라이팬"],
  "knowledge": { ... 1장 형식 ... },
  "recipes": [ ... ],
  "config": { "weights": {...}, "engine": {...}, "v2": {...} },
  "cases": [
    {
      "id": "safety_shrimp_pantry",
      "description": "…",
      "profile": { "allergens": ["shrimp"] },
      "request": { "mode": "pantry", "pantry": ["..."], "limit": 50, "rerank": false },
      "judge": null,
      "expect": {
        "compare": "ordered",
        "ranking": "rules",
        "notes": ["rerank_off"],
        "items": [ { "id": "...", "group": "ready", "score": 0.83, "breakdown": {"I": 1.0, "...": 0}, "missing": [], "substitutions": [], "notes": [] } ],
        "must_exclude": ["shrimp_stirfry", "..."],
        "aspects": ["request", "skill"]
      }
    }
  ]
}
```

- 시험 데이터는 사람이 승인한 알레르기 시험 데이터(`tests/allergy/fixtures.py`)에 맛 정보 없는 레시피 3개를 더한 것입니다.
- 시험용 설정은 실제 `config/*.yaml`과 같고, 매운 재료 목록만 시험 지식에 있는 재료(`gochujang`, `kimchi`, 제목 `매콤`·`고추`)로 바꿨습니다.
- 사용자 조리기구는 `equipment`입니다(2-1).

### 10-2. 사례 종류

| 접두어 | 확인하는 것 |
|---|---|
| `safety_` | 알레르기(포함 가능·고명·선택·기본 양념), 미매칭, 묶음, 알레르기 > 좋아함, 절대 안 먹음은 확실한 것만 |
| `spicy_` | 매운맛 한도와 추정, 5 = 한도 없음 |
| `pantry_` | 묶음 분류, 대체재 |
| `dish_` | 요리명 유사도, 결과 없음 |
| `jev_` | 판단 항목 선택, 판단 순서, 묶음 경계, 걸러내기 보충, 실패 시 규칙 대체, 매운맛 5는 묻지 않음 |
| `invalid_` | 입력 오류 |
| `dislike_` | 싫어함은 제외가 아님 |

### 10-3. 가짜 Jev(`judge` 필드)

`judge`가 null이면 Jev 판단기가 없는 상태입니다(규칙 경로). 객체이면 다음 판단기를 만들어 넣습니다.

- `judge(…)`: 후보마다 요청된 **모든 항목**에 점수 `judge_scores[제목]`(없으면 `default`), 확신도 `confidence`
- `screen(…)`: 후보마다 `screen_scores[제목]`(없으면 0)
- `fails: true`면 judge와 screen 모두 오류

### 10-4. 비교 규칙

참고 구현은 `tests/v2/test_shared_cases.py`의 `compare_case`입니다.

1. `expect.error`가 있으면 입력 오류가 나야 합니다.
2. 결과의 어떤 레시피도 `must_exclude`에 있으면 안 됩니다. 시험 레시피 전체를 3장으로 판정한 결과이며, **가장 중요한 검사**입니다.
3. `ranking`이 같고, `notes`가 집합으로 같아야 합니다.
4. `compare == ordered`면 레시피 id 순서가 같아야 하고, `set`이면 집합이 같아야 합니다(규칙 경로 랜덤).
5. 같은 레시피끼리 다음이 같아야 합니다.
   - `group`
   - `score`, `breakdown` 각 값(허용 오차 0.001), breakdown 항목 이름 집합
   - `missing`, `substitutions`(순서 포함)
   - 레시피 안내 코드(집합)
6. `aspects`가 있으면 8-1의 항목 목록이 같아야 합니다. 판단기에 넘어간 항목으로 확인합니다.

### 10-5. 다시 만들기

엔진이나 설정을 바꾸면 아래 명령으로 다시 만들고 차이를 검토합니다.

```
uv run python scripts/make_shared_cases.py
```

`tests/v2/test_shared_cases.py`가 파일이 최신인지와, JSON만으로 다시 돌린 결과가 기대와 같은지를 확인합니다.

## 11. 숫자·문자열 처리에서 주의할 점

- **반올림**: 정렬 키의 `round`는 Python의 `round`(가장 가까운 짝수로 반올림, 이진 부동소수 값 기준)입니다. 점수가 정확히 경계에 걸리는 일은 드물지만, 다르게 구현하면 순서가 바뀔 수 있습니다. 공용 시험 세트로 확인하세요.
- **id 순**: 코드 포인트 순입니다(`"a10" < "a2"`). 숫자를 인식하는 비교를 쓰지 마세요.
- **부분 문자열 검사**(제목, 별칭, 키워드): 정규화 뒤 문자열 포함 여부입니다. 형태소 분석은 하지 않습니다.
- **집합 순회 순서에 기대지 마세요.** 이 명세에서 순서가 중요한 곳은 모두 정렬 기준을 적어 두었습니다.
