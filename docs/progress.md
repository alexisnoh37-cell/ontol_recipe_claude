# 진행 상황

> 에이전트는 각 단계가 끝날 때마다 이 파일을 갱신합니다. 새 세션은 이 파일부터 읽습니다.

## 현재 단계

Phase 1-4 초안 완료(2026-10-03, 전체 284개 통과). **사람이 페르소나별 "상위 3개 안에 나와야 할 레시피"를 채울 차례**(docs/review/golden_draft.md, tests/golden/personas.yaml의 expected_top3). **tests/allergy/는 수정·삭제·skip 금지**(0-3 승인). 하나라도 실패하면 엔진 결함이다.

## 단계별 상태

| 단계 | 상태 | 완료일 | 사람 확인 | 비고 |
| --- | --- | --- | --- | --- |
| 0-1 설계 확정 | 완료 | 2026-10-03 | 완료 | docs/plan.md 부록 A~C, knowledge/README.md |
| 0-2 스키마와 지식 컴파일러 | 완료 | 2026-10-03 | 필요(아래 승인 필요 2건) | 테스트 72개 통과, Docker DB에 마이그레이션·컴파일 반영 확인 |
| 0-3 알레르기 테스트 작성 | 완료 | 2026-10-03 | 완료(승인) | 118개. 1-1 전까지 115개 실패가 정상 |
| 0-4 식재료 200개 확장 | 완료 | 2026-10-03 | 완료(검수) | 재료 252개 reviewed(confidence low 70개 유지), 알레르기 그룹 27개 reviewed |
| 1-1 필터 엔진 | 완료 | 2026-10-03 | 완료(승인) | 전체 226개 통과(tests/allergy 118, tests/allergy 무수정) |
| 1-2 점수 엔진 | 완료 | 2026-10-03 | 선택(아래 "사람 확인 필요") | 전체 262개 통과(tests/logic/test_scoring.py 36개 추가) |
| 1-3 레시피 시드 | 완료 | 2026-10-03 | 완료(검수) | 레시피 50개 published, DB 재적재 확인, 전체 275개 통과 |
| 1-4 골든셋 | 초안 완료 | 2026-10-03 | 필요(기대 결과 기입, 다양성 한도 결정) | 페르소나 8명, 평가 스크립트, 기대 결과 미기입 |
| 1-5 API, 화면, 성능 | 대기 | | | |
| 1-6 MVP 점검과 마무리 | 대기 | | 필요(직접 사용) | |

## 주요 결정 기록

0-1에서 확정(2026-10-03, 사람 승인). 상세는 docs/plan.md 본문과 부록 A~C.

- **패키지 관리**: uv(pyproject.toml + uv.lock, Python 3.12). 실행은 `uv run ...`.
- **구조**: `engine/`(순수 Python) 외에 `kb/`(컴파일러 순수 로직), `storage/`(SQLAlchemy, DB 로더·writer) 패키지 추가. `tests/kb/`, `tests/storage/`, `tests/support/` 추가.
- **데이터 주입**: 엔진은 Protocol 리포지토리 + 불변 스냅샷을 받는다. 구현체는 in-memory 하나이고 공급원(kb 컴파일 결과, YAML, DB, 합성 데이터)만 다르다. 사용자 데이터는 호출자가 `UserContext`로 넘긴다.
- **DDL**: ID는 text slug. 컴파일 산출물 `ingredient_ancestor`, `ingredient_contains`, `allergen_closure(certainty, via)` 추가. `allergen_group_member`, `knowledge_build`, `unmapped_term` 추가. user_event는 Phase 3에서 추가.
- **knowledge 형식(F1~F9)**: derived_from 엣지 단위 certainty, `kind: concept`, 별칭 `{text, form}`과 전역 유일, 기본 양념은 config 단일 원천, `vocab.yaml` 신설, 알 수 없는 키 오류, `ingredients/*.yaml` 분할 지원, 마늘은 `garlic` 하나, 콩기름 별도 재료.
- **안전(A1~A4)**: concept 노드는 레시피·보유 재료로 사용 금지, 중간 노드는 하위 개념 알레르기를 possible로 가짐. 대체 안내도 알레르기·절대 불선호로 거름. 절대 불선호는 derived_from까지 따름(`ingredient_contains`). soft 선호는 is_a만.
- **범위(B1~B3)**: 조리기구 필터는 Phase 1, 식단은 Phase 2. Phase 1 대체재는 substitutes.yaml + technique 맥락. user_event는 Phase 3, expires_on은 컬럼만.
- **세부(C1~C10)**: 상위 개념 매칭은 보유 하위 → 레시피 상위 방향만. cuisine은 국가별 평면 어휘. 희망 시간은 요청 파라미터, M = max(0, 1 − (t − w)/w). 실력 1~3. 커버리지는 main·sub만, 기본 양념은 role 무관하게 보유 간주, missing은 비선택 미보유 재료 전부. P 재료값 = 0.5 + 0.5·polarity·strength, 동률은 최솟값. T 미입력 차원 제외(전부 미입력이면 0.5). 레시피 status는 draft·published, 엔진은 기본 published만(`config/engine.yaml: serve_draft_recipes`). 다양성은 main 재료 각각 계산. recipe_id는 text slug.

0-2에서 정한 것(2026-10-03, "승인 필요" 항목은 사람 확인 전):

- **vocab 값**: 한국어 표기 문자열 그대로(`한식`, `볶음` 등). 별도 id 없음.
- **contains 탐색 규칙 구현**: 위(is_a 부모, definite)·원천(derived_from, 엣지 certainty)·아래(is_a 자식, possible) 이동. 아래 이동은 마지막 원천 이동(또는 시작) 이후 위로 이동한 적이 없을 때만 허용. 대상마다 (certainty, 경로 길이, 사전순)으로 가장 강한 경로를 via로 저장.
- **closure via**: 재료 → 알레르기를 직접 가진 원천 재료까지의 id 경로.
- **concept 사용 금지 범위 확대**(A1 연장): 기본 양념, 대체 관계 from/to에도 concept 금지.
- **DB 반영 시 참조 검사 확대**(승인 필요): 삭제될 재료·알레르기 그룹을 user_preference가 참조해도 실패(FK가 없어 조용히 알레르기 설정이 끊기는 것을 막기 위함). 부록 C-5는 recipe_ingredient, user_pantry만 명시.
- **레시피 시드 형식 잠정안**: `kb/datacheck.py`의 RecipeSpec. DDL 컬럼을 그대로 따른다(1-3에서 그대로 확정).
- **테스트 DB**: docker 초기화 시 `recipe_test` DB 생성, `TEST_DATABASE_URL`이 있을 때만 tests/storage 실행.
- **마이그레이션**: 0001_initial은 부록 B DDL을 문장 단위로 그대로 실행. `tests/logic/test_migration_matches_plan.py`가 일치를 검사.
- **alembic.ini는 ASCII만**: Windows에서 Alembic이 ini를 locale 인코딩(cp949)으로 읽어 한글 주석이 있으면 실행이 깨진다(실행 중 발견, 테스트로 고정).

0-2 실행 결과(Docker PostgreSQL 16): `alembic upgrade head`로 테이블 21개 생성. 컴파일 반영 결과 재료 32(concept 2), 별칭 70, 관계 22, allergen_closure 33, contains 35. 두 번 반영해도 지식 테이블 동일(멱등). DB에서 새우젓 shrimp definite, 김치 shrimp possible, 된장 대두 definite·밀 possible, squid closure 0행 확인. `validate_data.py --db` 통과.

0-3에서 정한 것(2026-10-03):

- **0-2 승인 반영**: user_preference 참조 검사 확대를 plan.md 부록 C-5에 반영. 레시피 시드 형식은 1-3에서 확정.
- **엔진 인터페이스**(engine/model.py, ports.py, memory.py, config.py, recommend.py): 부록 A대로 정의. `Recommender.recommend`는 NotImplementedError. 알레르기는 `UserContext.allergen_groups`(기본·묶음 그룹 id)로, 절대 불선호는 `Preference(is_hard=True)`로 받는다. 제외 기록 `Exclusion`은 사유 코드(`ExclusionReason`), 걸린 재료, 대상, certainty, 근거 경로(via), detail을 가진다. 한 레시피에 여러 행 가능.
- **테스트 연결부**: kb 컴파일 결과 → 엔진 스냅샷 변환은 `tests/support/engine_fixtures.py`에 둔다(engine은 kb를 import할 수 없음). 엔진 구성이 바뀌면 tests/allergy가 아니라 이 파일을 고친다. Phase 1에서 storage도 같은 변환이 필요하므로 그때 위치를 다시 정한다.
- **사람 승인**: 엔진 인터페이스 형태(allergen_groups, Preference is_hard, Exclusion 구성)와 변환 코드의 tests/support 배치 승인. 제안 시나리오 8개 추가(넓은 재료는 concept → 적재 거부, 중간 노드 → possible 제외로 분리).
- **추가 시나리오**: 중간 노드 젓갈류, 3단계 파생, 원천 재료 자체 possible, 상위 재료 지정 → is_a 하위 상속, 대체재로만 후보가 되는 레시피(위험한 대체재로 매칭·안내 금지), draft 제공 시에도 필터, 요청 보유 재료, 해산물 전체 묶음. concept 적재 거부는 `tests/support/engine_fixtures.recipe_load_issue_codes`(레시피 시드 형식 확정 시 여기만 수정)로 검사.
- **테스트 검증**: 임시 참조 구현(저장소 밖)으로 118개 모두 통과, 고의 결함 5종(전부 제외, 선택·고명 무시, possible 무시, 미매칭 허용, 위험한 대체재 사용)이 모두 실패로 잡히는 것을 확인.
- **엔진 구현 시 지킬 것(테스트가 요구)**: 대체재로 후보를 만들 때도 대체재를 알레르기 closure·절대 불선호로 거른다. draft 제공 여부와 관계없이 필터를 적용한다. `RecommendRequest.pantry`가 있으면 그것을 보유 재료로 쓴다.

0-4에서 정한 것(2026-10-03):

- **D4 확정**(사람): 법정 19개 + 자체 2개(other_fish, sesame) + 묶음 4개. 이전 `fish` 그룹은 `mackerel`·`other_fish`로 나뉘어 삭제.
- **allergens.yaml 형식 추가**: `official`, `source`(law_annex2·custom). 스키마 기본값은 false·custom(승인된 tests/allergy fixture가 이 필드 없이 작성되어 필수로 둘 수 없음). 실제 파일은 명시 여부를 tests/kb로 강제. DB 컬럼은 아직 없음(writer가 DB에 없는 필드는 건너뜀).
- **재료 파일 분할**: `knowledge/ingredients/` 8개 파일(meat, seafood, vegetables, fruits_nuts, grains, dairy_egg_soy, seasonings, kimchi_processed). 기존 id 32개 유지.
- **알레르기 배치**: 돼지고기·쇠고기·닭고기·조개류는 중간 노드(pork, beef, chicken, clam)에 적고 하위는 is_a로 상속. 아황산류는 첨가물 노드 `sulfite`를 두고 와인·건과일이 derived_from. 어묵·게맛살은 분류 노드 `fish`에서 파생 → 모든 생선 그룹 possible. 액젓은 넓은 재료(멸치액젓·까나리액젓의 상위).
- **참기름 변경**: derived_from 참깨(definite). 기본 양념이라 참깨 알레르기 사용자에게 참기름 레시피가 모두 제외됨.
- **김치 변경**: 액젓(possible) 원천 추가 → 기타 생선 possible.
- **검수표 생성기**: `scripts/make_review.py`. 검수표가 최신인지 tests/kb가 검사.
- **YAML 문법 오류**: traceback 대신 `yaml_syntax` 오류로 보고하도록 수정(0-4 작업 중 발견).
- **0-4 검수 반영**(사람): 자체 그룹 `other_cephalopods`(문어·낙지·주꾸미, 해산물 전체에 포함), `other_tree_nuts`(아몬드 definite, 밤 possible, 견과류 묶음에 포함, 묶음 이름 "견과류"). 젓갈류 하위에 어리굴젓(굴)·조개젓(조개) 추가 → 젓갈류가 조개류 possible. 배추김치·깍두기에 밀가루·굴 possible 추가.
- **유지 결정**(사람): 참기름 참깨 definite, 한치 = 오징어 별칭, 국간장 밀 definite, 식용유·콩기름 분리, 삼치 = 기타 생선, 재료 250여 개 유지, 콩나물 경고 허용.
- **official·source DB 저장**(사람 승인): 마이그레이션 0002, plan.md 부록 B·3-1 수정. 기존 DB는 `uv run alembic upgrade head` 후 재컴파일 필요.
- **검수 완료 처리**: 모든 재료·알레르기 그룹 status: reviewed(confidence는 그대로). substitutes.yaml은 이번 검수 범위가 아니어서 draft 유지.

1-1에서 정한 것(2026-10-03):

- **엔진 모듈**: `engine/normalize.py`(별칭 정규화, concept·미매칭 분리), `candidates.py`(후보·재료별 충족 상태), `filters.py`(`UserConstraints`: 제약 판정과 Exclusion 생성), `explain.py`(missing, 대체 안내, 템플릿 notes), `recommend.py`(조립). 0-3 임시 참조 엔진은 쓰지 않고 새로 작성.
- **조회만**: 알레르기는 `allergen_closure`, 절대 불선호는 `contains`, 상위 개념 매칭은 `ancestors`만 조회한다. 요청 중 재귀 탐색 없음.
- **보유 간주**: 보유 재료 + 기본 양념 + 그 is_a 조상. 후보는 main·sub 재료 중 하나라도 보유 또는 대체로 충족되는 레시피.
- **대체재 사용 조건**: 대체 재료(to)를 **직접** 보유하고(하위 재료 보유로는 인정 안 함), context가 비었거나 레시피 technique과 겹치고, 알레르기 closure·절대 불선호에 걸리지 않을 때. 같은 재료에 여러 대체가 가능하면 id 순 첫 번째(1-2에서 ratio 반영 검토).
- **보수적 입력 처리**: 모르는 알레르기 그룹·절대 불선호 재료 id가 오면 `ValueError`(필터가 조용히 꺼지는 것 방지). `user_preference`의 allergen_group(is_hard)도 알레르기로 합친다. 레시피 재료 id가 지식에 없으면 미매칭으로 보고 알레르기 사용자에게 제외. 보유 재료의 concept·모르는 id는 버린다.
- **missing 표기**: 재료 id 튜플(이름 변환은 API·화면). 미매칭 재료는 id가 없어 notes에 원문으로 적는다. 선택 재료 미보유는 notes("선택 재료라 빼고 조리 가능"). draft 레시피는 notes에 "검수 전".
- **제외 기록**: 사유마다 행을 남긴다(한 레시피에 여러 행). 같은 (사유, 재료, 대상)은 한 번만. 조리시간 필터(time_is_hard)도 plan 4-3대로 함께 구현.
- **임시 정렬**: 레시피 id 순, score 0.0, breakdown 빈 값. 1-2에서 점수로 교체.
- **tests/logic 추가**(29개): 매운맛 한도(hard 제외·soft 통과), 필수 조리기구, 시간, 음식 종류, 상위 개념 매칭 방향(삼겹살 → 돼지고기 레시피 매칭, 반대는 missing), 대체재 context, 동의어(달걀=계란), 엔진·컴파일러 정규화 일치, 실제 knowledge 스모크(새우 알레르기 → 김치 possible·새우젓 definite 제외). 고의 결함(매운맛 한도 무시, 대체재 안전·context 무시)으로 테스트가 실패하는 것 확인.

### 1-1 확인 결과(사람 승인, 2026-10-03)

- 대체재는 대체 재료를 직접 보유할 때만 인정(하위 재료 보유 불인정): **승인**.
- 모르는 알레르기 그룹·절대 불선호 재료 id는 `ValueError`(API에서 400): **승인**.
- missing은 재료 id로 출력, 이름 표기는 1-5(API·화면)에서: **승인**.
- 그 밖에 1-1에서 정한 내용(보유 간주, 제외 기록, 시간 필터 등): **모두 승인**.

1-2에서 정한 것(2026-10-03):

- **모듈**: `engine/scoring.py`(UserScorer: I·K·T·P·D·M, `rank`, `diversify`), `engine/config.py`(`load_engine_config`, `ScoringConfig.from_mapping`). `config/engine.yaml` 신설(`serve_draft_recipes: false`).
- **설정 로딩**: 가중치·계수는 `config/weights.yaml`만 원천. 키가 빠지면 `Recommender` 생성 시 `ValueError`(조용히 기본값으로 동작하지 않게). `tests/support/engine_fixtures.build_recommender`가 실제 config/를 읽도록 바꿈(tests/allergy는 무수정).
- **I**: main·sub(비선택)만, role_weight(main 3, sub 2). 대체재 충족은 관계의 `ratio`, 없으면 `substitute_credit`(0.8). 계산할 재료가 하나도 없으면 1.0. 미매칭 재료(main·sub)는 미보유로 계산.
- **대체재 선택**: 같은 재료에 쓸 수 있는 대체가 여럿이면 인정 비율이 높은 것, 같으면 id 순(1-1의 id 순에서 변경).
- **K**: soft cuisine 선호. polarity만 보고 like 1.0 / dislike 0.1 / 없으면 0.5. strength는 쓰지 않는다(plan 4-4 표 그대로). 같은 음식 종류에 상충 선호가 있으면 낮은 값.
- **T**: preferred_level을 입력한 맛만 가중 평균. max_level만 있는 맛은 T에서 뺀다(필터 전용). 같은 차원이 여러 번 오면 첫 값.
- **P(C7·4-5)**: 재료 자신 → is_a 조상 depth 순으로 처음 만나는 soft 선호. 같은 깊이 여러 개, 같은 재료 여러 개면 최솟값. 선택 재료는 optional 가중치(0.2), seasoning은 role_weight에 없어 P에서 제외. concept(해산물 등)도 선호 대상 가능. 모르는 선호 재료 id는 `ValueError`(1-1 규칙을 soft 선호에도 적용).
- **D·M**: config 표 그대로. 난이도 차이는 −2~2로 자름. M은 희망 시간이 없으면 1.0.
- **정렬**: 점수 내림차순, 동점은 recipe_id 순. 응답의 score·breakdown은 소수 셋째 자리 반올림(정렬은 반올림 전).
- **다양성(4-6)**: 상위 top_n(10) 안에 같은 cuisine·같은 main 재료(각각 셈)가 한도(3)를 넘으면 뒤로 미룬다. 한도를 지켜 top_n을 못 채우면 미룬 항목을 점수 순으로 채운다. 제외된 레시피는 다양성 단계에도 들어오지 않는다.
- **설명(4-7)**: 템플릿 notes 추가 — "필요한 주재료와 부재료를 모두 갖고 있습니다"(I = 1이고 대체 없음), "희망 시간보다 오래 걸립니다(약 N분)". `RecommendResult.exclusion_summary`(사유 코드별 제외 레시피 수) 추가.
- **tests/logic/test_scoring.py**(36개): 구체성 우선(해산물 좋음·새우 싫음, 같은 깊이 최솟값, 가까운 조상 우선), 역할 가중, 매운맛 preferred_level 감점·비제외, T 미입력 0.5, 동의어 입력 매칭, 상위 개념 커버리지, 기본 양념 커버리지 무감점, 비기본 seasoning은 missing이지만 I 제외, 선택 재료 I 제외, 대체 인정 비율(기본·ratio·최고 ratio 선택), 난이도 표·초급자 정렬, K 3단계, M 공식, breakdown 6항목과 가중합 일치, 가중치를 config에서 읽음, 설정 누락 오류, 다양성(음식 종류 한도, main 재료 각각, 제외 레시피 비복귀).

1-3에서 정한 것(2026-10-03):

- **시드 형식 확정**: `data/recipes/<id>.yaml` 파일 하나에 레시피 하나. 형식은 `kb/datacheck.py RecipeSpec`(0-2 잠정안 그대로) + 설명 `data/recipes/README.md`. 공통 읽기 함수 `kb/recipes.py`(`read_recipe_dir`, `load_recipe_specs`: 오류가 하나라도 있으면 `RecipeSeedError`, 일부만 적재 안 함). `scripts/validate_data.py`도 이 함수를 쓴다.
- **레시피 50개**(한식 30, 일식 7, 중식 7, 양식 6): 모두 `status: draft`, `source: agent_draft`, 2인분. confidence low 4개(부대찌개, 일본식 카레, 마파두부, 연어덮밥 — 이유는 note). 외부 레시피 복제 없이 일반 가정식 절차로 작성.
- **새 재료 추가 없음**: 기존 252개 재료로 모두 매핑(미매칭 0). 그래서 `test_all_knowledge_is_reviewed`(모든 재료 reviewed)도 그대로 통과.
- **작성 규칙**: 부위 무관한 고기는 넓은 재료(`pork`, `beef`, `chicken`)로 적어 하위 부위 보유자도 매칭. 특정 부위가 필요하면 하위 재료(돈가스·탕수육 `pork_loin`, 스테이크 `beef_sirloin`). 기본 양념도 모두 적음. 물은 재료로 적지 않음. 고형 카레는 `curry_powder`, 쯔유는 `tsuyu`로 매핑.
- **조리기구 required 정책**: 냄비·프라이팬은 `required: false`(대부분 사용자가 조리기구를 등록하지 않으면 거의 모든 레시피가 제외되기 때문). 오븐(감자 그라탕)만 `required: true`.
- **DB 적재**: `storage/recipe_writer.py`(시드에 있는 레시피는 하위 행까지 지우고 다시 넣음, `--prune`일 때만 시드에 없는 레시피 삭제), `scripts/load_recipes.py`(`--dry-run`, 한 트랜잭션). `storage/tables.py`에 recipe, recipe_taste, recipe_equipment, recipe_step 추가. 로컬 Docker DB에 지식 재컴파일 후 50개 적재, 두 번 실행해도 동일(recipe_ingredient 413행, recipe_step 151행).
- **검수표**: `scripts/make_recipe_review.py` → `docs/review/recipes_review.md`. 열: 제목(id), 종류, 난이도, 맛(매움/짠맛/단맛), 주재료, 선택재료, 걸리는 알레르기 그룹(기본 그룹, `그룹: 원인 재료`, possible은 "(가능)"), confidence. low를 맨 위에, 아래 부록에 레시피 상세(전체 재료와 매핑, 조리기구, 단계).
- **엔진 변환**: `tests/support/engine_fixtures.recipe_from_spec`(RecipeSpec → engine Recipe). 1-5에서 API가 같은 변환을 쓰게 되면 위치를 옮긴다.
- **테스트 추가**(12개): `tests/kb/test_recipe_seed.py`(검증 오류 0, 파일 이름 = id, 한식 30·기타 20, 전부 draft, 필수 주재료·맛·난이도·단계 존재, 잘못된 시드 거부, 검수표 최신, 새우 알레르기 → 김치 레시피 3개·계란찜(새우젓)·해물파전(선택 새우) 제외, 우유 알레르기 → 선택 치즈 레시피 제외, draft는 기본 비제공), `tests/storage/test_recipe_writer.py`(개수 일치, 멱등, prune).

1-3 검수 결과(사람, 2026-10-03):

- **승인**: 조리기구 required:false 정책, 고기 `pork`(아무 부위) 표기, 고형 카레 → 카레가루, 계란 흰자 → 계란.
- **선택 재료로 변경**: 계란찜 새우젓, 계란말이 당근·대파, 된장찌개 애호박·감자, 김치찌개 두부. 새우젓은 선택 재료여도 새우 알레르기 사용자에게 여전히 제외된다(D2).
- **연어덮밥**: 화면 안내 문구 "횟감용 생연어 사용"(아래 1-5 화면 요구사항).
- **다양성 한도**: 1-4 골든셋 결과를 보고 결정.
- 반영 후 검수표 재생성, DB 재적재, 테스트 통과 확인 → 레시피 50개 `status: published`. confidence는 그대로 둠(low 4개). `tests/kb/test_recipe_seed.py`는 published 기준으로 갱신(검수 수정 사항 고정 테스트 추가).

1-4(초안)에서 정한 것(2026-10-03):

- **페르소나 8명**(`tests/golden/personas.yaml`): 한식파 직장인(korean_lover), 요리 초보 자취생(beginner, 실력 1), 알레르기 많은 아이 부모(multi_allergy: 계란·우유·갑각류 묶음), 매운 것 못 먹는 사람(low_spice: 한도 1), 양식 좋아하는 사람(western_lover, 한식 약한 불선호, 오븐 보유), 일식 좋아하는 사람(japanese_lover), 냉장고가 빈 사람(few_ingredients: 재료 5개), 해산물 좋아하는 숙련자(seafood_expert: 실력 3, 해산물 +0.8, 돼지고기 −0.6). 보유 재료 5~8개. `expected_top3`는 모두 비워 둠.
- **평가**: `tests/golden/golden.py`(페르소나 로딩, 실제 knowledge·config·시드로 엔진 구성, 적중률), `scripts/eval_golden.py`(적중률 출력, `--draft`로 `docs/review/golden_draft.md` 생성). 페르소나별 적중률 = 상위 3개에 든 기대 레시피 수 ÷ min(3, 기대 수). 전체는 기입된 페르소나 평균, 미기입은 따로 셈. 지금은 "미기입 0/8".
- **초안 표에 비교 열 추가**: 다양성 한도 결정을 돕기 위해 "다양성 보정 없을 때 상위 5개"를 함께 보여 준다(설정은 바꾸지 않음, 비교용 엔진만 따로 구성).
- **테스트**(`tests/golden/test_golden.py`, 9개): 페르소나 8명·필수 유형 포함, 데이터 유효성(재료·그룹·조리기구·음식 종류), 기입된 기대 레시피가 시드에 존재, 모두 결과 5개 이상, 결과가 알레르기·매운맛 한도를 지킴, 적중률 계산, 미기입 처리, 초안 렌더링. 적중률 기준(합격선)은 두지 않음.
- **위치 메모**: 골든셋 모듈이 `tests/support/engine_fixtures`(kb → 엔진 변환)를 쓴다. 1-5에서 변환 위치를 옮길 때 함께 바꾼다.

1-4 초안에서 본 것(판단은 사람이):

- **다양성 보정이 8명 중 7명의 상위 5개를 바꾼다.** 예: 양식파는 파스타 3개가 양식 한도(3)를 채워 스테이크(0.809)·그라탕(0.662)이 밀리고 장조림(0.650)·청경채볶음(0.590)이 4·5위. 한식파는 된장찌개(0.885)·계란말이(0.865) 대신 짜장덮밥(0.780)·계란볶음밥(0.755). 상위 3개는 모든 페르소나에서 보정 전후가 같다.
- **동점이 많다**: 한식파 1·2위(0.915), 매운맛 한도 페르소나 1~3위(0.825), 재료 적은 사람 1~3위(0.750). 동점은 recipe_id 순이다.
- **기본 양념·대체재로 후보가 되는 레시피**: 양식파 5위 청경채볶음은 부재료 마늘(기본 양념이라 보유 간주)만으로 후보가 되었다. 해산물 숙련자 5위 마파두부는 쪽파 보유 → 대파 대체로 후보(I 0.23). plan 4-2·C5 규칙대로 동작한 결과다.
- **해산물 숙련자**: 무생채(무만 있으면 I 1.0)가 해물파전보다 위. 매운맛 선호 3과 해물파전 매움 0의 차이(T 0.40)가 커서다.

### 1-2 응답 예시(실제 knowledge, 예시용 레시피 6개)

예시 레시피: 돼지고기 김치찌개, 삼겹살 구이, 김치볶음밥, 토마토 파스타(파르메산 선택), 크림 파스타, 카레라이스. 생성 스크립트는 저장소 밖(일회성).

예시 1 — 초급(1), 한식 선호, 매운맛 선호 3·한도 4, 보유: 김치·삼겹살·쪽파·밥, 희망 30분, limit 3:

```json
{
  "items": [
    {
      "recipe_id": "kimchi_fried_rice",
      "title": "김치볶음밥",
      "score": 0.895,
      "breakdown": {
        "I": 1.0,
        "K": 1.0,
        "T": 0.8,
        "P": 0.5,
        "D": 1.0,
        "M": 1.0
      },
      "missing": [],
      "substitutions": [],
      "notes": [
        "필요한 주재료와 부재료를 모두 갖고 있습니다",
        "계란은(는) 선택 재료라 빼고 조리할 수 있습니다"
      ]
    },
    {
      "recipe_id": "kimchi_jjigae_pork",
      "title": "돼지고기 김치찌개",
      "score": 0.85,
      "breakdown": {
        "I": 0.75,
        "K": 1.0,
        "T": 1.0,
        "P": 0.5,
        "D": 1.0,
        "M": 1.0
      },
      "missing": [
        "tofu"
      ],
      "substitutions": [
        {
          "need": "green_onion",
          "use": "scallion"
        }
      ],
      "notes": [
        "양파은(는) 선택 재료라 빼고 조리할 수 있습니다",
        "대파 대신 쪽파을(를) 쓸 수 있습니다"
      ]
    },
    {
      "recipe_id": "pork_belly_grill",
      "title": "삼겹살 구이",
      "score": 0.715,
      "breakdown": {
        "I": 0.6,
        "K": 1.0,
        "T": 0.4,
        "P": 0.5,
        "D": 1.0,
        "M": 1.0
      },
      "missing": [
        "lettuce",
        "ssamjang"
      ],
      "substitutions": [],
      "notes": []
    }
  ],
  "exclusion_summary": {}
}
```

예시 2 — 중급(2), 우유 알레르기, 돼지고기 약한 불선호(−0.5), 짠맛 선호 2, 보유: 파스타·토마토소스·양파·돼지 앞다리·감자, 희망 30분. 토마토 파스타는 선택 재료 파르메산 때문에, 크림 파스타는 생크림, 카레라이스는 카레가루(우유 포함 가능)로 제외되어 `allergen: 3`:

```json
{
  "items": [
    {
      "recipe_id": "kimchi_jjigae_pork",
      "title": "돼지고기 김치찌개",
      "score": 0.585,
      "breakdown": {
        "I": 0.375,
        "K": 0.5,
        "T": 0.8,
        "P": 0.417,
        "D": 0.9,
        "M": 1.0
      },
      "missing": [
        "kimchi",
        "tofu",
        "green_onion"
      ],
      "substitutions": [],
      "notes": []
    }
  ],
  "exclusion_summary": {
    "allergen": 3
  }
}
```

## 사람 확인 필요

- **(1-4, 필수) 골든셋 기대 결과**: `tests/golden/personas.yaml`의 각 페르소나 `expected_top3`(최대 3개 recipe_id)를 채워 주세요. 표는 `docs/review/golden_draft.md`. 페르소나 구성(보유 재료, 선호, 알레르기)을 바꿔도 됩니다.

- (1-2) **다양성 한도와 음식 종류 수**(사람: 1-4 골든셋 결과를 보고 결정): cuisine이 4개뿐이라 상위 10개에 같은 종류 3개 한도면 한식 선호 사용자도 상위 10개 중 한식이 3개만 남는다(나머지는 한도를 못 채울 때만). plan 4-6 그대로 구현했으며, 골든셋(1-4) 결과를 보고 `config/weights.yaml diversity.max_same_cuisine` 조정을 판단해 주세요.
- (1-2, 선택) K에 선호 strength를 반영하지 않음(plan 표대로 1.0/0.5/0.1). 반영하려면 plan 4-4 수정이 필요하다.
- (1-2, 선택) 템플릿 조사 표기("양파은(는)")가 어색하다. 1-5에서 이름 표기와 함께 받침 처리를 정한다.

## 1-5 화면 요구사항

0-4 검수에서 사람이 정한 안내 문구(Phase 1-5 Streamlit 화면에 반영):

- 알레르기 선택에서 **고등어**를 고르면: "다른 생선에도 반응하면 '생선 전체'를 선택하세요."
- **식용유**가 들어간 레시피(또는 식용유 재료 표시)에: "제품의 기름 종류(콩기름 등)를 확인하세요."

1-3 레시피 검수에서 사람이 정한 안내 문구:

- **연어덮밥**(`salmon_don`) 카드에: "횟감용 생연어 사용"

## 알려진 문제

- **D4 알레르기 목록 미확정**: allergens.yaml은 0-2에서 example 그대로 `status: draft`로 옮긴다. 0-4 시작 전에 사람이 표시 대상 목록과 생선 그룹 단위를 확정해야 한다(액젓의 derived_from 대상도 이에 따라 정해짐).
- (해결) `garlic_minced` → `garlic` 변경을 `config/pantry_staples.yaml`에 반영함.
- 콩기름(soybean_oil)과 식용유(cooking_oil) 사이 is_a 관계는 두지 않았다. 두면 식용유(기본 양념)가 대두 possible이 되어 대두 알레르기 사용자에게 기름을 쓰는 레시피가 대부분 제외된다. 0-4 검수에서 정한다.
- (해결) 재료 없는 알레르기 그룹 경고는 0-4에서 모두 해소.
- 컴파일 경고 3건(의도): 콩나물 derived_from 대두이나 가공품 아님, 멸치액젓·까나리액젓 is_a 4단계(액젓 → 젓갈류 → 해산물).
- (해결) 아몬드·밤 → 기타 견과류, 낙지·문어·주꾸미 → 기타 연체류(0-4 검수).
- (해결) `allergen_group.official/source` DB 저장: 마이그레이션 0002.
- (해결) 1-1부터 `uv run pytest` 전체 통과.
- 샌드박스 환경에서는 pytest의 기본 임시 폴더 접근이 막혀 `--basetemp`를 지정해 실행했다(일반 환경에서는 불필요).
- 정제 식용유(콩기름 등)의 대두 알레르기 처리 기준은 0-4 검수표에서 사람이 판단한다.

## 다음 할 일

- 사람: `tests/golden/personas.yaml`의 `expected_top3`를 페르소나별로 채움(docs/review/golden_draft.md 참고). 다양성 한도 결정.
- 그다음 PROMPTS.md 1-4 후속: 골든셋 평가를 돌리고 적중률이 낮은 페르소나를 점수 내역으로 설명, 가중치 조정안은 제안만.
- 1-5 bench 전에 후보 생성의 대체 역색인을 스냅샷 단위로 캐시할지 측정 후 결정.
- 새 재료를 추가할 때는 status: draft로 넣고 검수표(`scripts/make_review.py`)로 사람 확인 후 reviewed.

## 다음 단계 제안 (범위 밖 아이디어)

- cuisine 외에 요리 유형(찌개, 볶음, 면 등) 선호 축 추가
- 식단 조건(채식 등) 필터 — Phase 2
- 자동완성 검색 품질을 위한 pg_trgm 인덱스
