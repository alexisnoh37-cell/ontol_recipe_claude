# knowledge/ — 식재료 지식 원본

이 폴더의 YAML이 식재료 지식의 원본입니다(온톨로지 역할). DB의 식재료·관계·알레르기 테이블은 `scripts/compile_knowledge.py`가 이 파일들로부터 생성합니다. DB를 직접 고치지 말고 이 파일을 고친 뒤 다시 컴파일합니다.

아래 형식과 `*.example.yaml`은 출발점입니다. Phase 0-1에서 에이전트가 개선안을 제안할 수 있고, 승인되면 이 문서도 함께 고칩니다.

## 파일 구성

| 파일 | 내용 |
| --- | --- |
| `allergens.yaml` | 알레르기 그룹 정의와 묶음 그룹 |
| `ingredients.yaml` | 식재료, 별칭, 상위 개념(is_a), 파생 원천(derived_from), 알레르기 |
| `substitutes.yaml` | 조건부 대체 관계 |

규모가 커지면 `ingredients/` 폴더 아래 카테고리별 파일(meat.yaml, seafood.yaml 등)로 나눠도 됩니다.

## 공통 필드

- `id`: 영문 소문자 snake_case. 한 번 정하면 바꾸지 않습니다.
- `status`: `draft` | `reviewed`. 사람이 검수하면 `reviewed`로 바꿉니다.
- `confidence`: `high` | `low`. 성분이나 관계가 확실하지 않으면 `low`로 두고 검수표에 올립니다.
- `note`: 검수자에게 남길 메모.

## 식재료 필드 (`ingredients.yaml`)

| 필드 | 설명 |
| --- | --- |
| `name` | 대표 이름(화면 표시용) |
| `aliases` | 같은 재료를 가리키는 다른 표기. 입력 정규화에 사용 |
| `category` | 분류. 분류 전용 노드는 `분류` |
| `is_a` | 상위 개념 id 목록 |
| `derived_from` | 만들어진 원천 재료 id 목록(가공품) |
| `derived_certainty` | `definite`(기본) 또는 `possible`. possible이면 이 재료의 derived_from 연결을 "포함 가능"으로 표시 |
| `is_processed` | 가공품 여부. true면 derived_from 필수 |
| `is_pantry_staple` | 기본 양념 여부(config/pantry_staples.yaml과 일치시킨다) |
| `allergens` | 원천 재료에만 적는다. `{group, certainty}` 목록 |

## 컴파일 규칙

1. `is_a`와 `derived_from`은 방향 그래프입니다. 순환이 있으면 컴파일을 실패시킵니다.
2. 알레르기는 **원천 재료에만** 적습니다(예: 새우에만 `shrimp`). 새우젓처럼 파생된 재료는 `derived_from: [shrimp]`만 적으면 컴파일러가 알레르기를 상속합니다.
3. `is_a` 하위 재료도 상위 재료의 알레르기를 상속합니다(예: 대하 is_a 새우).
4. 묶음 그룹(`includes`)은 포함된 그룹의 재료를 모두 합칩니다.
5. 결과는 `allergen_closure(allergen_group_id, ingredient_id)`로 저장합니다. 요청 처리 시에는 이 테이블만 조회합니다.
6. `certainty: possible`(포함 가능)인 연결도 closure에 포함합니다.
7. `is_processed: true`인데 `derived_from`이 없으면 검증 오류입니다.
