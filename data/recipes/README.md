# 레시피 시드 형식

파일 하나에 레시피 하나를 둔다. 파일 이름은 `<id>.yaml`이다. 검증 규칙의 원본은 `kb/datacheck.py`의 `RecipeSpec`이고,
DB 컬럼(docs/plan.md 부록 B의 recipe, recipe_ingredient, recipe_taste, recipe_equipment, recipe_step)을 그대로 따른다.

```yaml
id: kimchi_jjigae              # 소문자 slug, 파일 이름과 같게
title: 돼지고기 김치찌개
cuisine: 한식                  # knowledge/vocab.yaml cuisines
difficulty: 1                  # 1~3 (1 초급). published에는 필수
cook_time_min: 30
servings: 2                    # 선택
source: agent_draft            # 출처. 에이전트 초안은 agent_draft
status: draft                  # draft | published. 사람 검수 후에만 published
confidence: high               # high | low. 확신이 낮으면 low + note에 이유
note: ...                      # 선택. 검수자에게 남기는 메모
ingredients:
  - ingredient: kimchi         # knowledge 재료 id(concept 금지). 매핑 못 하면 null(미매칭, 알레르기 사용자에게 제외됨)
    raw_text: 배추김치 1/4포기   # 원문 표기(양 포함)
    role: main                 # main | sub | seasoning | garnish
    optional: false            # 선택 재료면 true. 선택 재료도 알레르기 판정 대상
    amount: null               # 선택(숫자)
    unit: null                 # 선택
taste: {spicy: 3, salty: 3, sweet: 1, sour: 2, umami: 3, savory: 3}   # 각 0~5. published에는 필수
equipment:
  - {name: 냄비, required: false}    # vocab.yaml equipment. required: true면 없을 때 제외
steps:
  - {text: 냄비에 돼지고기와 김치를 넣고 볶는다., technique: 볶음}   # technique은 vocab.yaml techniques(대체재 context 판정에 쓰임)
```

## 작성 원칙

- 외부 레시피 본문을 복제하지 않는다. 일반적인 가정식 조리법으로 직접 쓴다(docs/decisions.md D3).
- 재료는 knowledge의 id만 쓴다. 없는 재료는 knowledge에 `status: draft`로 먼저 추가하고 검수표에 올린다.
- 부위가 상관없는 고기는 넓은 재료(`pork`, `beef`)로 쓴다. 삼겹살 등 하위 재료를 가진 사용자도 매칭된다.
  특정 부위가 필요하면 하위 재료(`pork_loin`)를 쓴다(이때 다른 부위 보유로는 매칭되지 않음).
- 기본 양념(config/pantry_staples.yaml)도 빠짐없이 적는다. 커버리지에서는 보유로 간주되지만 알레르기 판정에는 쓰인다.
- 기본 조리도구(냄비, 프라이팬)는 `required: false`, 없으면 만들 수 없는 도구(오븐 등)만 `required: true`.
- 물은 재료로 적지 않는다.

## 명령

```powershell
uv run python scripts/validate_data.py         # 검증
uv run python scripts/load_recipes.py          # DB 반영
uv run python scripts/make_recipe_review.py    # 검수표 docs/review/recipes_review.md
```
