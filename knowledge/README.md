# knowledge/ — 식재료 지식 원본

이 폴더의 YAML이 식재료 지식의 원본입니다(온톨로지 역할). DB의 식재료·관계·알레르기 테이블은 `scripts/compile_knowledge.py`가 이 파일들로부터 생성합니다. DB를 직접 고치지 말고 이 파일을 고친 뒤 다시 컴파일합니다.

아래 형식은 Phase 0-1에서 확정했습니다. `*.example.yaml`은 Phase 0-2에서 실제 파일로 옮기면서 이 형식에 맞춥니다. 형식을 바꾸려면 제안하고 승인받은 뒤 이 문서도 함께 고칩니다.

## 파일 구성

| 파일 | 내용 |
| --- | --- |
| `allergens.yaml` | 알레르기 그룹 정의와 묶음 그룹 |
| `vocab.yaml` | 고정 어휘: `cuisines`, `equipment`, `techniques`, `categories` |
| `ingredients.yaml` 또는 `ingredients/*.yaml` | 식재료, 별칭, 상위 개념(is_a), 파생 원천(derived_from), 알레르기 |
| `substitutes.yaml` | 조건부 대체 관계 |

컴파일러는 `ingredients.yaml` 하나와 `ingredients/` 폴더 아래 카테고리별 파일(meat.yaml, seafood.yaml 등)을 모두 읽습니다. 재료가 많아지면(Phase 0-4) 폴더로 나눕니다.

기본 양념 목록은 이 폴더가 아니라 `config/pantry_staples.yaml`이 단일 원천입니다. 재료 YAML에는 `is_pantry_staple`을 적지 않습니다.

## 공통 필드

- `id`: 영문 소문자 snake_case. 한 번 정하면 바꾸지 않습니다.
- `status`: `draft` | `reviewed`. 사람이 검수하면 `reviewed`로 바꿉니다.
- `confidence`: `high`(기본) | `low`. 성분이나 관계가 확실하지 않으면 `low`로 두고 검수표에 올립니다.
- `note`: 검수자에게 남길 메모.
- 정의되지 않은 키는 컴파일 오류입니다(오타가 조용히 무시되지 않도록).

## 식재료 필드 (`ingredients.yaml`)

| 필드 | 설명 |
| --- | --- |
| `name` | 대표 이름(화면 표시용) |
| `kind` | `ingredient`(기본) 또는 `concept`. concept는 육류, 해산물 같은 분류 전용 노드로 레시피 재료나 보유 재료로 쓸 수 없습니다 |
| `category` | 화면 그룹핑용. `vocab.yaml`의 `categories` 중 하나. 판정에는 쓰지 않습니다 |
| `aliases` | 같은 재료를 가리키는 다른 표기. 문자열 또는 `{text, form}` 객체 |
| `is_a` | 상위 개념 id 목록 |
| `derived_from` | 만들어진 원천 재료 목록. 문자열 id(= definite) 또는 `{id, certainty}` 객체 |
| `is_processed` | 가공품 여부. true면 derived_from 필수 |
| `allergens` | 원천 재료에만 적습니다. `{group, certainty}` 목록. concept 노드에는 적지 않습니다 |

`certainty`는 `definite` 또는 `possible`(포함 가능)입니다. 제품마다 성분이 다르면 그 **엣지에만** `possible`을 붙입니다.

```yaml
- id: doenjang
  name: 된장
  derived_from: [soybean, {id: wheat_flour, certainty: possible}]
  is_processed: true
  confidence: low
  note: 밀 포함 여부는 제품별 상이
  status: draft

- id: garlic
  name: 마늘
  aliases: [깐마늘, 통마늘, {text: 다진 마늘, form: minced}]
  status: draft
```

### 별칭 규칙

- 이름과 별칭은 정규화(NFC, 공백 제거, 라틴 문자 소문자) 후 **모든 재료를 통틀어 유일**해야 합니다. 겹치면 컴파일 오류입니다.
- "파"처럼 여러 재료를 가리킬 수 있는 표기는 별칭으로 쓰지 않습니다.
- 별칭은 같은 재료의 다른 표기입니다. 알레르기 성분이 다를 수 있는 재료(예: 콩기름과 다른 식용유)는 별칭이 아니라 별도 재료로 둡니다.
- 크기·품종만 다른 같은 재료(예: 대하, 흰다리새우 → 새우)는 별칭으로 둡니다. 따로 다뤄야 할 이유가 생기면 별도 재료로 만들고 `is_a`로 연결합니다.

## 대체 관계 필드 (`substitutes.yaml`)

| 필드 | 설명 |
| --- | --- |
| `from` | 레시피가 요구하는 재료 id |
| `to` | 대신 쓸 수 있는 재료 id |
| `context` | 대체가 성립하는 조리 맥락. `vocab.yaml`의 `techniques` 중에서 고릅니다. 비어 있으면 모든 맥락에서 성립 |
| `ratio` | 선택. 재료 커버리지 인정 비율. 없으면 `config/weights.yaml`의 기본값 |

양방향 대체는 두 줄로 따로 적습니다(방향마다 맥락이 다를 수 있음). 대체재는 점수와 안내에만 쓰고 알레르기 판정에는 영향을 주지 않습니다. 단, 대체 안내 자체는 사용자의 알레르기와 절대 불선호로 거릅니다.

## 컴파일 규칙

1. `is_a`, `derived_from`, 그리고 두 그래프의 합집합은 방향 그래프입니다. 순환이 있으면 컴파일을 실패시킵니다.
2. 알레르기는 **원천 재료에만** 적습니다(예: 새우에만 `shrimp`). 새우젓처럼 파생된 재료는 `derived_from: [shrimp_raw]`만 적으면 컴파일러가 알레르기를 상속합니다.
3. `is_a` 하위 재료도 상위 재료의 알레르기를 상속합니다(예: `saeujeot` is_a `jeotgal`이면 젓갈류의 알레르기를 상속).
4. 하위 개념이 있는 재료(예: 젓갈류)는 하위 개념들의 알레르기를 `possible`로 함께 가집니다. 레시피가 "젓갈류"처럼 넓은 재료를 쓸 때 알레르기가 새지 않게 하기 위해서입니다. is_a 부모를 거쳐 형제 재료로 퍼지지는 않습니다(새우가 해산물의 하위라고 오징어 알레르기를 갖지 않음).
5. 묶음 그룹(`includes`)은 포함된 그룹의 재료를 모두 합칩니다.
6. 결과는 `allergen_closure(allergen_group_id, ingredient_id, certainty, via)`로 저장합니다. 요청 처리 시에는 이 테이블만 조회합니다.
7. `certainty: possible`(포함 가능)인 연결도 closure에 포함합니다. 판정에서는 포함으로 간주합니다.
8. `is_processed: true`인데 `derived_from`이 없으면 검증 오류입니다.
9. `config/pantry_staples.yaml`의 id는 모두 존재해야 합니다.

상세 동작 순서와 산출 테이블은 `docs/plan.md` 부록 C를 따릅니다.

## example 파일에서 바뀌는 점 (Phase 0-2에서 반영)

| 항목 | example | 확정 형식 |
| --- | --- | --- |
| 분류 노드 | `category: 분류` | `kind: concept` |
| 가공품 성분 확실성 | 재료 단위 `derived_certainty` | derived_from 엣지 단위 `certainty` |
| 기본 양념 | 재료마다 `is_pantry_staple: true` | `config/pantry_staples.yaml`만 사용 |
| 마늘 | `garlic_minced`(별칭에 마늘) | `garlic` 하나, `다진 마늘`은 `form: minced` 별칭 |
| 콩기름 | `cooking_oil`의 별칭 | 별도 재료 `soybean_oil`(derived_from soybean, possible, confidence: low) |
| 별칭 "파" | `green_onion`의 별칭 | 삭제(모호) |
| 어휘 | 없음 | `vocab.yaml` 신설 |

`allergens.yaml`의 그룹 목록은 example 그대로 옮기고 `status: draft`로 둡니다. 표시 대상 목록 확정은 사람이 Phase 0-4 시작 전에 합니다(docs/decisions.md D4).
