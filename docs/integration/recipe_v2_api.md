# 레시피 추천 v2 연동 명세

다른 앱이 이 추천 엔진을 붙일 때 필요한 내용을 정리한 문서입니다. 앱이 저장해야 할 사용자 정보 6가지, 재료 id 변환, API 요청·응답 예시, 오류 처리를 다룹니다.

- 대상: 연동하는 앱의 백엔드 개발자
- 기준: 브랜치 `feature/recommend-v2`(PR #13), 2026-10-19. 설계 근거는 `docs/plan.md` 부록 G, 결정은 `docs/decisions.md` D7~D10을 참고하세요.
- 이 문서의 요청 예시(` ```json request ` 블록)와 오류 예시는 `tests/v2/test_integration_doc.py`가 실제 API에 보내 응답 코드를 확인합니다. 코드가 바뀌어 예시가 틀리면 테스트가 실패합니다.

## 1. 한눈에 보기

```
[다른 앱 서버] ──(사용자 정보 6가지 + 요청)──▶ POST /v2/recommend ──▶ 추천 목록 + 이유 + 부족 재료 + 안내
```

1. **제외**: 알레르기, 절대 안 먹는 재료, 매운맛 한도를 넘는 레시피는 규칙으로 먼저 뺍니다. 결과에 다시 나오지 않습니다.
2. **후보**: 관련 있는 레시피를 고릅니다.
3. **순위**: Jev(TypeSafe AI, `jev-1.14.0`)가 항목별로 판단해 정합니다. Jev가 응답하지 않으면 규칙 점수로 대체합니다.

추천 형태는 세 가지입니다.

| `mode` | 설명 | 필요한 입력 |
|---|---|---|
| `random` | 먹을 수 있는 레시피 중 무작위 40개에서 취향에 맞게 고름 | 없음(`seed`를 주면 같은 결과) |
| `pantry` | 가진 재료로 **지금 바로** / **조금만 사면**(1~2개 부족) 만들 수 있는 레시피 | `pantry`(재료 id 목록) |
| `dish` | 요리 이름이나 느낌("오늘은 얼큰한 국물이 끌려")으로 찾기 | `query`(문장) |

## 2. 앱이 저장할 사용자 정보 6가지

요청할 때마다 `profile`에 그대로 담아 보냅니다. 엔진은 프로필을 저장하지 않습니다.

| 필드 | 형식 | 의미와 엔진 처리 | 비워 두면 |
|---|---|---|---|
| `allergens` | 알레르기 그룹 id 목록 | **들어 있을 수도 있는 재료까지 제외**합니다. 선택 재료·고명·기본 양념도 봅니다. 예: 새우 알레르기면 김치(새우젓)도 제외. 알레르기가 있으면 정체를 모르는 재료가 든 레시피도 제외합니다 | 알레르기 없음 |
| `never_eat` | 재료 id 목록 | **확실히 들어간** 레시피만 제외합니다. 들어 있을 수도 있는 가공품은 통과시키고 성분표 확인 안내를 붙입니다 | 없음 |
| `likes` | 재료 id 목록 | 좋아하는 재료입니다. 순위를 올립니다(제외와 무관) | 없음 |
| `dislikes` | 재료 id 목록 | 덜 좋아하는 재료입니다. 순위를 낮추고, **제외하지 않습니다** | 없음 |
| `spicy_level` | 정수 0~5 또는 `null` | 0~4: 이 값을 넘는 레시피는 제외하고, 같은 값을 매운맛 취향으로 씁니다. **5: 한도 없음**(제외도 취향도 없음). 맛 정보가 없는 레시피는 고추류 재료가 없으면 맵지 않다고 봅니다 | `null` = 매운맛 무관 |
| `cuisine_likes` / `cuisine_dislikes` | 음식 종류 목록(`한식`·`일식`·`중식`·`양식`) | 순위에만 반영합니다(제외하지 않음) | 없음 |
| `skill_level` | 정수 1~3(초보·보통·숙련) 또는 `null` | 난이도가 맞는 레시피를 위로 올립니다 | `null` = 보통(2) |

`cuisine_likes`와 `cuisine_dislikes`는 한 쌍으로 하나의 정보입니다.

### 꼭 지켜야 할 것

1. **알레르기와 "싫어함"을 섞지 마세요.** 알레르기를 `never_eat`나 `dislikes`에 넣으면 들어 있을 수도 있는 가공품이 걸러지지 않습니다. 알레르기는 반드시 `allergens`에 넣습니다. 종교 등으로 엄격히 피해야 하는 재료도 알레르기 그룹이 있으면 `allergens`에 넣으세요(예: 돼지고기 → `pork`).
2. **"모름"과 "0"을 구분하세요.** 매운맛을 묻지 않았으면 `0`이 아니라 `null`입니다. `0`은 "전혀 못 먹음"이라 매운 레시피가 모두 빠집니다.
3. **같은 재료를 `likes`와 `dislikes`에 동시에 넣지 마세요**(400 오류). 같은 음식 종류를 좋아함·싫어함에 동시에 넣어도 400입니다.
4. 알레르기와 좋아하는 재료가 겹치면 **제외가 이깁니다.** 예: 김치를 좋아해도 새우 알레르기면 김치 레시피는 나오지 않습니다. 오류는 아닙니다.
5. 조리기구는 받지 않습니다. 모두 있다고 봅니다.

### 저장 예시(앱 DB)

```json
{
  "user_id": "app-user-123",
  "allergens": ["shrimp", "egg"],
  "never_eat": ["cucumber"],
  "likes": ["pork_belly", "kimchi"],
  "dislikes": ["eggplant"],
  "spicy_level": 3,
  "cuisine_likes": ["한식"],
  "cuisine_dislikes": [],
  "skill_level": 2,
  "pantry": ["pork_belly", "tofu", "onion"]
}
```

`user_id`와 `pantry`는 앱이 관리합니다. 추천 엔진에는 `user_id`를 보내지 않습니다. `pantry`는 `mode: pantry`일 때 요청에 담습니다.

## 3. 재료·알레르기 id 변환

엔진은 **재료 이름이 아니라 재료 id**로 판단합니다. "계란"과 "달걀"은 같은 `egg`입니다.

### 3-1. 재료 검색: `GET /ingredients/search`

| 파라미터 | 설명 |
|---|---|
| `q` | 검색어(이름·별칭, 필수) |
| `limit` | 최대 결과 수(기본 20, 1~100) |

```
GET /ingredients/search?q=달걀&limit=3
```

```json
[
  {"id": "egg", "name": "계란", "matched": "달걀", "category": "알", "is_concept": false, "is_pantry_staple": false}
]
```

| 필드 | 의미 |
|---|---|
| `id` | 저장할 값 |
| `name` | 화면에 보여 줄 대표 이름 |
| `matched` | 검색어와 일치한 이름이나 별칭 |
| `is_pantry_staple` | 기본 양념(소금·간장 등). 보유로 간주하므로 `pantry`에 넣지 않아도 됩니다 |

**검색 결과를 사용자가 직접 고르게 하세요.** 비슷한 이름도 함께 나옵니다. 예: `q=김치`로 찾으면 다음이 나옵니다.

- `kimchi`(배추김치)
- `frozen_dumplings`(냉동만두, "김치만두"로 일치)
- `baek_kimchi`(백김치)
- …

첫 결과를 자동으로 저장하면 안 됩니다. `matched`를 함께 보여 주면 사용자가 고르기 쉽습니다.

검색되지 않는 재료는 저장하지 마세요. 엔진이 모르는 id를 받으면 요청 전체가 400 오류가 납니다. 사용자가 입력한 원문은 앱에 따로 보관하고, 추가가 필요하면 저희에게 알려 주세요(지식 데이터에 별칭을 추가하면 검색됩니다).

### 3-2. 알레르기 그룹: `GET /allergen-groups`

알레르기는 **자유 입력 대신 아래 목록에서 고르게** 하세요. 목록은 앱 시작 시 이 API로 받아 오는 것을 권장합니다(2026-10-19 기준 27개).

| 종류 | 그룹 id(이름) |
|---|---|
| 법정 표시 대상 등(`kind: base`) | `beef`(쇠고기), `buckwheat`(메밀), `chicken`(닭고기), `crab`(게), `egg`(알류), `mackerel`(고등어), `milk`(우유), `peach`(복숭아), `peanut`(땅콩), `pine_nut`(잣), `pork`(돼지고기), `shellfish`(조개류), `shrimp`(새우), `soybean`(대두), `squid`(오징어), `sulfites`(아황산류), `tomato`(토마토), `walnut`(호두), `wheat`(밀), `other_cephalopods`(기타 연체류), `other_fish`(기타 생선), `other_tree_nuts`(기타 견과류), `sesame`(참깨) |
| 묶음(`kind: bundle`) | `crustacean_bundle`(갑각류 = 게·새우), `fish_bundle`(생선 전체), `nuts_bundle`(견과류), `seafood_bundle`(해산물 전체) |

응답의 `notice`가 있으면 선택 화면에 함께 보여 주세요. 예: 고등어를 고르면 "다른 생선에도 반응하면 '생선 전체'를 선택하세요."가 나옵니다.

### 3-3. 음식 종류: `GET /vocab`

`cuisines`(`한식`·`일식`·`중식`·`양식`)를 받아 씁니다. 같은 응답의 `disclaimer`는 화면 하단에 그대로 보여 줘야 하는 면책 문구입니다(5장).

## 4. 추천 요청: `POST /v2/recommend`

### 4-1. 요청 필드

| 필드 | 형식 | 설명 |
|---|---|---|
| `profile` | 2장의 6가지 정보 | 사용자 정보. 아래 둘과 **정확히 하나만** 줍니다 |
| `profile_id` / `persona_id` | | 엔진 내부 저장 프로필, 테스트 페르소나용입니다. 연동 앱은 `profile`을 쓰세요 |
| `mode` | `random` · `pantry` · `dish` | 필수 |
| `query` | 문자열(최대 200자) | `dish`에 필수 |
| `pantry` | 재료 id 목록 | `pantry` 모드의 보유 재료 |
| `seed` | 0 이상 정수 | `random`에서 같은 결과를 다시 받고 싶을 때. 비우면 엔진이 정해 응답에 담습니다 |
| `rerank` | `true` · `false` · 비움 | `false`면 Jev 없이 규칙 점수만 씁니다(빠르고 비용 없음). 비우면 기본(Jev 사용) |
| `max_time_min` / `time_is_hard` | 정수 / 불리언 | 희망 조리시간. `time_is_hard: true`면 넘는 레시피를 제외합니다 |
| `limit` | 1~50 | 결과 수. 기본 10(`random`은 5) |

알 수 없는 필드를 보내면 422 오류입니다. 예: `profile.allergy`라는 오타.

### 4-2. 요청 예시

요리 찾기:

```json request
{
  "profile": {
    "allergens": ["shrimp"],
    "never_eat": ["cucumber"],
    "likes": ["pork_belly", "kimchi"],
    "dislikes": ["eggplant"],
    "spicy_level": 3,
    "cuisine_likes": ["한식"],
    "cuisine_dislikes": [],
    "skill_level": 2
  },
  "mode": "dish",
  "query": "오늘은 얼큰한 국물이 끌려",
  "limit": 3
}
```

내 재료로:

```json request
{
  "profile": {"allergens": ["shrimp"], "spicy_level": 3, "skill_level": 2},
  "mode": "pantry",
  "pantry": ["pork_belly", "tofu", "onion", "green_onion"],
  "limit": 5
}
```

랜덤(같은 결과를 다시 받으려면 응답의 `seed`를 다시 보냄):

```json request
{"profile": {"allergens": ["milk", "egg"], "cuisine_likes": ["양식"]}, "mode": "random", "seed": 42, "limit": 3}
```

Jev 없이 규칙 점수만(빠른 응답이 필요할 때):

```json request
{"profile": {"skill_level": 1}, "mode": "dish", "query": "계란 요리", "rerank": false}
```

### 4-3. 응답 예시

실제 응답(요리 찾기 예시, 첫 항목만, 일부 생략):

```json
{
  "mode": "dish",
  "query": "오늘은 얼큰한 국물이 끌려",
  "seed": null,
  "ranking": "jev",
  "rerank_used": true,
  "rerank_model": "jev-1.14.0",
  "notes": [],
  "items": [
    {
      "recipe_id": "mogsal_gocujangjjigae_e_som",
      "title": "목살 고추장찌개",
      "cuisine": "한식",
      "difficulty": 2,
      "cook_time_min": 10,
      "score": 0.814,
      "breakdown": [
        {"key": "J_request", "label": "요청과 맞음(Jev)", "value": 0.728},
        {"key": "J_taste", "label": "맛 취향(Jev)", "value": 0.968},
        {"key": "J_ingredients", "label": "재료 취향(Jev)", "value": 0.66},
        {"key": "J_cuisine", "label": "음식 종류(Jev)", "value": 0.905},
        {"key": "J_skill", "label": "실력에 맞는 난이도(Jev)", "value": 0.895},
        {"key": "J", "label": "Jev 적합도", "value": 0.814},
        {"key": "J_conf", "label": "Jev 확신도", "value": 0.57}
      ],
      "missing": [{"id": "pork_neck", "name": "돼지고기 목살"}, {"id": "onion", "name": "양파"}],
      "required_missing": [{"id": "pork_neck", "name": "돼지고기 목살"}, {"id": "onion", "name": "양파"}],
      "nice_to_have": [],
      "missing_text": "돼지고기 목살, 양파, 애호박, 멸치액젓이 없습니다",
      "nice_to_have_text": null,
      "substitutions": [],
      "notes": ["검수 전 레시피입니다"],
      "commercial_notice": null,
      "notices": ["제품의 기름 종류(콩기름 등)를 확인하세요."],
      "label_check": {
        "message": "제품 성분표를 확인하세요",
        "ingredients": [{"id": "gochujang", "name": "고추장"}, {"id": "soy_sauce", "name": "간장"}],
        "text": "제품 성분표를 확인하세요: 고추장, 간장"
      },
      "group": null,
      "group_label": null,
      "required_missing_count": 4
    }
  ],
  "exclusion_summary": [
    {"reason": "spicy_limit", "label": "매운맛 한도 초과", "count": 344, "examples": ["애호박삼겹짜글이", "애순이 오징어국", "불닭계란두부탕"]},
    {"reason": "allergen", "label": "알레르기 성분 포함(포함 가능 포함)", "count": 164, "examples": ["애순이 오징어국", "참치두부조림", "돼지김치나베"]}
  ],
  "excluded_total": 437,
  "disclaimer": "알레르기 판정은 등록된 식재료 정보와 일반적인 제품 구성에 근거한 참고용입니다. …"
}
```

### 4-4. 응답 필드

| 필드 | 설명 | 화면 처리 |
|---|---|---|
| `items[]` | 추천 목록(순서가 곧 순위) | 위에서부터 보여 줍니다 |
| `title`, `cuisine`, `difficulty`, `cook_time_min` | 레시피 기본 정보. 식품안전나라 레시피는 `difficulty`·`cook_time_min`이 `null`일 수 있습니다 | `null`이면 "-"로 표시 |
| `score` | 종합 점수 0~1 | 선택 표시 |
| `breakdown[]` | 추천 이유(항목별 점수 0~1). `label`이 화면용 이름입니다. Jev 경로는 `J_*`, 규칙 경로는 `I`(재료 보유)·`K`(음식 종류)·`T`(맛)·`P`(재료 선호)·`D`(난이도)·`M`(시간)·`S`(찾는 요리와 비슷함)입니다 | "왜 추천했나" 표시에 사용 |
| `required_missing` / `missing_text` | 꼭 필요한데 없는 재료 | 장보기 안내 |
| `nice_to_have` / `nice_to_have_text` | 없어도 되는 재료(고명·선택) | 선택 표시 |
| `substitutions[]` | 대체 안내. 예: "식용유 대신 버터를 쓸 수 있습니다" | 표시 권장 |
| `label_check` | **성분표 확인이 필요한 재료**(알레르기 사용자에게만 나옴) | **반드시 표시** |
| `notes[]`, `notices[]`, `commercial_notice` | 레시피별 안내. 예: 검수 전, 맵지 않은 요리로 추정, 들어 있을 수도 있는 재료 | 표시 권장 |
| `group` / `group_label` | `pantry` 모드: `ready`(지금 바로) / `near`(조금만 사면). 목록은 `ready`가 먼저 옵니다 | 묶음 제목으로 표시 |
| `required_missing_count` | 꼭 필요한데 없는 재료 수 | 선택 표시 |
| `ranking` | `jev`(Jev가 순위) / `rules`(규칙 점수) | 로그에 남기기를 권장 |
| `notes[]`(최상위) | 요청 전체 안내. 아래 표 참고 | 표시 권장 |
| `exclusion_summary`, `excluded_total` | 사유별 제외 수와 예시 | 선택("알레르기로 164개 제외" 등) |
| `disclaimer` | 면책 문구 | **반드시 표시** |
| `seed` | `random`에서 쓴 seed | 같은 결과를 다시 받을 때 사용 |

최상위 `notes[].code`:

| code | 의미 | 앱 처리 |
|---|---|---|
| `jev_unavailable` | Jev가 응답하지 않아 규칙 점수로 대체했습니다 | 결과는 정상입니다. 필요하면 로그만 남기세요 |
| `jev_screened` | 관련 레시피가 적어 Jev가 전체에서 찾았습니다 | 없음 |
| `dish_excluded` | 찾는 요리가 못 먹는 재료 때문에 빠졌습니다 | `text`를 보여 주세요 |
| `dish_no_match` | 비슷한 레시피를 찾지 못했습니다(결과 0개) | `text`를 보여 주고 다른 표현을 권하세요 |
| `rerank_off`, `rerank_unavailable` | 규칙 경로의 재정렬 상태 | 없음 |

결과가 0개일 수 있습니다. 알레르기가 많거나 보유 재료가 적거나, 규칙 경로(`rerank: false`)에서 찾는 요리가 제외된 경우입니다. 이때 `notes`의 `text`를 보여 주세요.

## 5. 화면에 반드시 보여 줄 것

1. 응답의 `disclaimer`(면책 문구). 알레르기 판정은 참고용이라 실제 제품 성분표 확인이 필요하다는 내용입니다.
2. `label_check.text`(있을 때). 고추장·간장처럼 제품마다 성분이 다른 재료의 성분표를 확인하라는 안내입니다.
3. `dish_excluded`·`dish_no_match`의 `text`(있을 때).

## 6. 오류 처리

| 코드 | 원인 | 응답 예 | 앱 처리 |
|---|---|---|---|
| 400 | 모르는 재료 id(`likes`·`dislikes`·`never_eat`·`pantry`) | `{"detail": "모르는 재료 id: no_such"}` | 저장된 id를 확인하고 다시 검색해 고치세요 |
| 400 | 모르는 알레르기 그룹 | `{"detail": "알 수 없는 알레르기 그룹: ['no_group']"}` | **요청을 버리지 말고** 알레르기 설정을 다시 받으세요. 알레르기를 빼고 다시 요청하면 안 됩니다 |
| 400 | 모르는 음식 종류 | `{"detail": "모르는 음식 종류: 태국식"}` | `GET /vocab` 목록으로 고치세요 |
| 400 | 같은 재료나 음식 종류를 좋아함·싫어함에 동시에 | `{"detail": "좋아하는 재료와 싫어하는 재료에 같은 재료가 있습니다: ['egg']"}` | 사용자에게 하나를 고르게 하세요 |
| 404 | 없는 `profile_id`·`persona_id` | `{"detail": "페르소나 x이(가) 없습니다"}` | 연동 앱은 `profile`을 쓰세요 |
| 422 | 형식 오류: `spicy_level` 범위 밖, `dish`인데 `query` 없음, `profile`·`profile_id`·`persona_id`를 둘 이상 줌, 알 수 없는 필드 | `{"detail": [{"loc": ["body", "profile", "spicy_level"], "msg": "Input should be less than or equal to 5", …}]}` | `detail[].loc`가 문제 필드입니다. 코드 결함이므로 수정하세요 |
| 5xx·시간 초과 | 서버 문제 | | 한 번 재시도한 뒤 오류 화면을 보여 주세요 |

모르는 값을 조용히 무시하면 알레르기 제외가 꺼질 수 있습니다. 그래서 엔진은 거부합니다. 앱에서도 400을 받았을 때 문제 값을 빼고 다시 보내는 자동 처리를 하지 마세요. 알레르기와 절대 안 먹는 재료는 특히 그렇습니다.

오류 예시(테스트가 이 요청들을 실제로 보내 응답 코드를 확인합니다):

```json error-400
{"profile": {"likes": ["no_such"]}, "mode": "random"}
```

```json error-400
{"profile": {"allergens": ["no_group"]}, "mode": "random"}
```

```json error-400
{"profile": {"likes": ["egg"], "dislikes": ["egg"]}, "mode": "random"}
```

```json error-422
{"profile": {"spicy_level": 9}, "mode": "random"}
```

```json error-422
{"profile": {}, "mode": "dish"}
```

```json error-422
{"profile": {"allergy": ["egg"]}, "mode": "random"}
```

## 7. 운영 참고

- **인증이 없습니다.** 추천 API는 앱 서버에서만 호출하세요(서버 간 통신). 사용자 기기에서 직접 호출하도록 공개하지 마세요. 공개가 필요하면 앞단에 인증 프록시를 두어야 합니다.
- **응답 시간**: Jev 경로는 보통 0.2~0.5초, 문장이 애매해 걸러내기 보충이 일어나면 0.8~1.3초입니다. Jev가 응답하지 않으면 걸러내기와 판단에 각각 최대 8초를 기다린 뒤 규칙 점수로 대체합니다. **클라이언트 타임아웃은 20초 이상**으로 두세요. 규칙 경로(`rerank: false`)는 수십 ms입니다.
- **비용**: Jev 경로는 요청 한 번에 Jev 1~1.5회 호출, 입력 약 3만 토큰을 씁니다(걸러내기 보충 시 7만~13만). 같은 화면에서 반복 요청이 많으면 `rerank: false`나 결과 캐시를 고려하세요.
- **결과 재현**: `random`은 `seed`가 같으면 같은 후보를 고르지만, Jev 판단은 모델 버전에 따라 달라질 수 있습니다. 모델은 `jev-1.14.0`으로 고정되어 있습니다(`GET /v2/info`의 `rerank_model`).
- **외부로 보내는 정보**: 순위를 정하려고 Jev(TypeSafe AI)로 보내는 정보는 아래와 같습니다. **알레르기, 절대 안 먹는 재료, 사용자 id, 레시피 id는 보내지 않습니다.** 개인정보 처리방침에 반영이 필요한지 확인하세요.
  - 요리 실력, 매운맛 취향, 좋아하는·싫어하는 재료 이름, 음식 종류 선호
  - 요청 문장, 보유 재료 이름(먹을 수 있는 것만)
  - 후보 레시피 요약
- **상태 확인**:
  - `GET /health`: 레시피·재료 수
  - `GET /v2/info`: 순위 방식, Jev 사용 가능 여부, 모델
- **데이터 출처**: 식품의약품안전처 식품안전나라 조리식품 레시피가 포함되어 있습니다(`notes`에 "검수 전 레시피입니다"가 붙는 레시피 상당수). 레시피 상세 화면에는 출처 표시를 권장합니다.

## 8. 실행(개발 환경)

레시피·지식을 DB 대신 파일에서 읽어 띄우는 방법입니다. `.env`에 `DATABASE_URL`은 설정되어 있어야 합니다(프로필 저장 API용). `profile` 직접 입력으로 추천만 쓸 때는 DB에 접속하지 않습니다.

PowerShell:

```powershell
$env:ENGINE_SOURCE = "files"
uv run uvicorn api.v2:default_app --factory --port 8000
```

`.env`에 `TYPESAFE_API_KEY`가 있으면 Jev 경로가 켜집니다. API 문서(Swagger)는 `http://localhost:8000/docs`에서 볼 수 있습니다.
