# 진행 상황

> 에이전트는 각 단계가 끝날 때마다 이 파일을 갱신합니다. 새 세션은 이 파일부터 읽습니다.

## 현재 단계

**MVP 완료(Phase 1-6, 2026-10-03, 태그 `mvp-v1`).** 전체 테스트 323개 통과, 골든셋 상위 3개 적중률 0.88, bench p95 75.5ms(기준 200ms). Phase 2 이후 할 일은 "다음 단계 제안". 단계별 경과는 아래 기록. **tests/allergy/는 수정·삭제·skip 금지**(0-3 승인). 하나라도 실패하면 엔진 결함이다.

**부가 트랙 viz 완료**(2026-10-03, 태그 `viz-v1`, 3D 온톨로지 + 추천 워크플로 시각화, docs/plan.md 부록 D). 전체 테스트 390개 통과. 아래 "부가 트랙 viz" 참조.

**데이터 확장 트랙 data-1**(2026-10-04, 브랜치 `feature/recipe-expansion`, 기준점 태그 `checkpoint/before-recipe-expansion`): 레시피 1차 초안 50개를 draft로 추가(합계 100개, published 50 그대로). 사람 검수 대기. data-2(2026-10-04): soft_tofu is_a tofu, 골든셋 재검토 자료 `docs/review/golden_review.md`. 전체 테스트 398개(DB 통합 9개는 Docker 미실행으로 건너뜀). 아래 "데이터 확장 트랙" 참조.

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
| 1-4 골든셋 | 완료 | 2026-10-03 | 완료(기대 결과 기입, 조정안 결정) | 적중률 0.79 → 0.67 → 0.88, 엔진 규칙 A~D와 데이터 조정 반영, 전체 287개 통과 |
| 1-5 API, 화면, 성능 | 완료 | 2026-10-03 | 완료(1-6 점검에서 확인) | API·화면·bench, p95 ≈ 102ms, 테스트 결과는 아래 "1-5에서 정한 것" |
| 1-6 MVP 점검과 마무리 | 완료 | 2026-10-03 | 완료(사용자 점검 통과) | 1-5 결정 3건 반영, 323개 통과, 적중률 0.88, p95 75.5ms |

## 주요 결정 기록

0-1에서 확정(2026-10-03, 사람 승인). 상세는 docs/plan.md 본문과 부록 A~C.

- **패키지 관리**: uv(pyproject.toml + uv.lock, Python 3.12). 실행은 `uv run ...`.
- **구조**: `engine/`(순수 Python) 외에 `kb/`(컴파일러 순수 로직), `storage/`(SQLAlchemy, DB 로더·writer) 패키지 추가. `tests/kb/`, `tests/storage/`, `tests/support/` 추가.
- **데이터 주입**: 엔진은 Protocol 리포지토리 + 불변 스냅샷을 받는다. 구현체는 in-memory 하나이고 공급원(kb 컴파일 결과, YAML, DB, 합성 데이터)만 다르다. 사용자 데이터는 호출자가 `UserContext`로 넘긴다.
- **DDL**: ID는 text slug. 컴파일 산출물 `ingredient_ancestor`, `ingredient_contains`, `allergen_closure(certainty, via)` 추가. `allergen_group_member`, `knowledge_build`, `unmapped_term` 추가. user_event는 Phase 3에서 추가.
- **knowledge 형식(F1~F9)**: derived_from 엣지 단위 certainty, `kind: concept`, 별칭 `{text, form}`과 전역 유일, 기본 양념은 config 단일 원천, `vocab.yaml` 신설, 알 수 없는 키 오류, `ingredients/*.yaml` 분할 지원, 마늘은 `garlic` 하나, 콩기름 별도 재료.
- **안전(A1~A4)**: concept 노드는 레시피·보유 재료로 사용 금지, 중간 노드는 하위 개념 알레르기를 possible로 가짐. 대체 안내도 알레르기·절대 불선호로 거름. 절대 불선호는 derived_from까지 따름(`ingredient_contains`). soft 선호는 is_a만.
- **범위(B1~B3)**: 조리기구 필터는 Phase 1, 식단은 Phase 2. Phase 1 대체재는 substitutes.yaml + technique 맥락. user_event는 Phase 3, expires_on은 컬럼만.
- **세부(C1~C10)**: 상위 개념 매칭은 보유 하위 → 레시피 상위 방향만. cuisine은 국가별 평면 어휘. 희망 시간은 요청 파라미터, M = max(0, 1 − (t − w)/w). 실력 1~3. 커버리지는 main·sub만(1-4에서 비기본 seasoning 1 추가), 기본 양념은 role 무관하게 보유 간주(1-4에서 후보 근거 제외), missing은 비선택 미보유 재료 전부. P 재료값 = 0.5 + 0.5·polarity·strength, 동률은 최솟값. T 미입력 차원 제외(전부 미입력이면 0.5). 레시피 status는 draft·published, 엔진은 기본 published만(`config/engine.yaml: serve_draft_recipes`). 다양성은 main 재료 각각 계산. recipe_id는 text slug.

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
- **다양성 한도**: 1-4 골든셋 결과를 보고 결정 → 1-4 마무리에서 같은 음식 종류 최대 5개로 결정(사람).
- 반영 후 검수표 재생성, DB 재적재, 테스트 통과 확인 → 레시피 50개 `status: published`. confidence는 그대로 둠(low 4개). `tests/kb/test_recipe_seed.py`는 published 기준으로 갱신(검수 수정 사항 고정 테스트 추가).

1-4(초안)에서 정한 것(2026-10-03):

- **페르소나 8명**(`tests/golden/personas.yaml`): 한식파 직장인(korean_lover), 요리 초보 자취생(beginner, 실력 1), 알레르기 많은 아이 부모(multi_allergy: 계란·우유·갑각류 묶음), 매운 것 못 먹는 사람(low_spice: 한도 1), 양식 좋아하는 사람(western_lover, 한식 약한 불선호, 오븐 보유), 일식 좋아하는 사람(japanese_lover), 냉장고가 빈 사람(few_ingredients: 재료 5개), 해산물 좋아하는 숙련자(seafood_expert: 실력 3, 해산물 +0.8, 돼지고기 −0.6). 보유 재료 5~8개. `expected_top3`는 모두 비워 둠.
- **평가**: `tests/golden/golden.py`(페르소나 로딩, 실제 knowledge·config·시드로 엔진 구성, 적중률), `scripts/eval_golden.py`(적중률 출력, `--draft`로 `docs/review/golden_draft.md` 생성). 페르소나별 적중률 = 상위 3개에 든 기대 레시피 수 ÷ min(3, 기대 수). 전체는 기입된 페르소나 평균, 미기입은 따로 셈. 지금은 "미기입 0/8".
- **초안 표에 비교 열 추가**: 다양성 한도 결정을 돕기 위해 "다양성 보정 없을 때 상위 5개"를 함께 보여 준다(설정은 바꾸지 않음). 1-4 마무리에서 한도가 결정되어 이 열은 "수정 전 → 수정 후" 비교 표로 대체했다.
- **테스트**(`tests/golden/test_golden.py`, 9개): 페르소나 8명·필수 유형 포함, 데이터 유효성(재료·그룹·조리기구·음식 종류), 기입된 기대 레시피가 시드에 존재, 모두 결과 5개 이상, 결과가 알레르기·매운맛 한도를 지킴, 적중률 계산, 미기입 처리, 초안 렌더링. 적중률 기준(합격선)은 두지 않음.
- **위치 메모**: 골든셋 모듈이 `tests/support/engine_fixtures`(kb → 엔진 변환)를 쓴다. 1-5에서 변환 위치를 옮길 때 함께 바꾼다.

1-4 초안에서 본 것(판단은 사람이):

- **다양성 보정이 8명 중 7명의 상위 5개를 바꾼다.** 예: 양식파는 파스타 3개가 양식 한도(3)를 채워 스테이크(0.809)·그라탕(0.662)이 밀리고 장조림(0.650)·청경채볶음(0.590)이 4·5위. 한식파는 된장찌개(0.885)·계란말이(0.865) 대신 짜장덮밥(0.780)·계란볶음밥(0.755). 상위 3개는 모든 페르소나에서 보정 전후가 같다.
- **동점이 많다**: 한식파 1·2위(0.915), 매운맛 한도 페르소나 1~3위(0.825), 재료 적은 사람 1~3위(0.750). 동점은 recipe_id 순이다.
- **기본 양념·대체재로 후보가 되는 레시피**: 양식파 5위 청경채볶음은 부재료 마늘(기본 양념이라 보유 간주)만으로 후보가 되었다. 해산물 숙련자 5위 마파두부는 쪽파 보유 → 대파 대체로 후보(I 0.23). plan 4-2·C5 규칙대로 동작한 결과다.
- **해산물 숙련자**: 무생채(무만 있으면 I 1.0)가 해물파전보다 위. 매운맛 선호 3과 해물파전 매움 0의 차이(T 0.40)가 커서다.

1-4(마무리)에서 정한 것(2026-10-03):

- **기대 결과 기입**(사람): `tests/golden/personas.yaml`의 expected_top3 8명 모두.
- **수정 전 기록**: 기대 결과를 채운 직후 당시 엔진으로 평가해 `tests/golden/baseline.json`에 저장(전체 0.79). `scripts/eval_golden.py --save-baseline "설명"`으로 기준을 바꾸고, `--draft`는 기준이 있으면 "수정 전 → 수정 후" 비교 표를 만든다.
- **엔진 규칙 변경(사람 지시, plan.md 4-2·4-4·4-6 수정)**:
  - A. 커버리지 I: main 3, sub 2, 기본 양념이 아닌 seasoning 1. 기본 양념(role 무관)·optional·garnish 제외. `config/weights.yaml coverage.role_weight.seasoning: 1`, `exclude_pantry_staples: true`(사용하지 않던 `exclude_roles` 키 삭제).
  - B. 후보: main 재료를 하나 이상 보유(직접·하위 개념·대체재). 기본 양념은 후보 근거 아님. `CANDIDATE_ROLES = ("main",)`, 리포지토리 색인도 main만.
  - C. 다양성: 같은 음식 종류 최대 5개(같은 주재료 3개 유지).
  - D. 동점: 점수(소수 셋째 자리) → I 높은 순 → 부족 재료 적은 순 → 조리시간 짧은 순 → id 순.
- **테스트 갱신**(tests/logic, tests/kb. tests/allergy는 무수정·전부 통과): 옛 규칙을 고정하던 테스트 6개를 새 규칙으로 바꿈(기본 양념만으로 후보 → 후보 아님, sub만 보유 → 후보 아님, 비기본 seasoning I 포함). 기본 양념·garnish 제외, 동점 처리 테스트 추가.

**골든셋 결과: 0.79 → 0.67**(표: docs/review/golden_draft.md)

| 페르소나 | 전 | 후 | 상위 3개 밖 기대 레시피(후) |
| --- | --- | --- | --- |
| korean_lover | 1.00 | 1.00 | - |
| beginner | 0.67 | 0.33 | 계란볶음밥 4위, 감자조림 5위 |
| multi_allergy | 0.67 | 0.33 | 감자조림 4위, 불고기 6위 |
| low_spice | 0.67 | 0.67 | 감자조림 5위 |
| western_lover | 0.67 | 0.67 | 스테이크 4위 |
| japanese_lover | 1.00 | 1.00 | - |
| few_ingredients | 1.00 | 0.67 | 감자조림 5위 |
| seafood_expert | 0.67 | 0.67 | 오징어볶음 7위 |

원인(점수 내역 기준):

- **감자조림(기대 레시피인 4명 모두 하락)**: 물엿(`corn_syrup`)이 기본 양념이 아닌 seasoning이라 규칙 A로 I가 1.00 → 0.75(감자 3 ÷ (감자 3 + 물엿 1)), 점수가 0.075 내려감. 하락분은 전부 이 한 줄 때문이다. 메모리에서만 시뮬레이션해 보면(적용 안 함) 물엿을 감자조림의 선택 재료로 바꾸거나 기본 양념에 넣으면 전체가 0.83이 된다.
- **beginner 계란볶음밥 4위**: 대파(sub) 미보유로 I 0.75. 3위 김치전(I 0.60)은 매운맛 선호 2와 맛 강도가 같아 T 1.00(계란볶음밥 T 0.60)으로 앞선다.
- **multi_allergy 불고기 6위**: 대파(sub) 미보유로 I 0.71. 짜장덮밥·규동은 춘장·쯔유가 없어도 main 둘(고기·밥, 3+3)을 가져 I 0.80으로 위에 남는다. 비기본 seasoning 가중치 1로는 "핵심 양념이 없는" 레시피를 충분히 내리지 못한다.
- **western_lover 스테이크 4위**: 올리브유(비기본 seasoning)와 버터(sub)를 못 가져 I 0.50. 알리오 올리오(I 0.60)가 T(0.90 vs 0.80)도 높아 3위.
- **seafood_expert 오징어볶음 7위**: 양파·대파(sub) 미보유로 I 0.43. 무생채(무만 있으면 I 1.00)가 2위.
- 수정으로 좋아진 점: 기본 양념만으로 후보가 되던 레시피(양식파의 청경채볶음 등)와 대체재로만 후보가 되던 레시피(해산물 숙련자의 마파두부)가 사라짐. 양식파 상위 5개에 스테이크가 들어옴(다양성 한도 5).

조정 제안(아래 "1-4 조정 반영"에서 사람이 결정):

1. **(데이터) 감자조림의 물엿을 optional로**, 또는 물엿·올리고당을 `config/pantry_staples.yaml`에 추가. 시뮬레이션상 0.67 → 0.83.
2. **(데이터) 대파의 역할 검토**: 계란볶음밥·불고기의 대파(sub)를 optional 또는 garnish로 볼지. 대파는 자주 빠지는 재료라 sub 2가 무겁다.
3. **(가중치, 골든셋 재확인 후)** 핵심 양념(춘장·쯔유·카레가루)이 빠진 레시피를 더 내리고 싶다면 seasoning 가중치 1 → 2, 또는 레시피 데이터에서 해당 양념을 sub로 올리는 방안. 다만 올리브유처럼 덜 핵심적인 seasoning도 함께 무거워진다.
4. 가중치 자체(I 0.30 등)는 지금 결과만으로 바꿀 근거가 약하다. 1~2를 먼저 반영하고 다시 평가하는 것을 권한다.

1-4 조정 반영(2026-10-03, 사람 결정):

- **기본 양념 추가**: 물엿(`corn_syrup`)·올리고당(`oligosaccharide`)을 `config/pantry_staples.yaml`에 추가.
- **대파 optional**: 소불고기·계란볶음밥의 대파(role sub 유지, `optional: true`).
- **요리를 정의하는 양념 seasoning → sub**: 짜장덮밥 춘장, 규동·오야코동·가케우동 쯔유, 일본식 카레 카레가루, 마파두부 두반장, 청경채볶음·고추잡채 굴소스.
- **가중치 변경 없음.** 엔진 코드 변경 없음(데이터·설정만).
- 레시피는 사람이 지시한 수정이라 `status: published` 유지. 검수표 2개 재생성, 지식 재컴파일(knowledge_build 7), 레시피 50개 DB 재적재, 전체 287개 통과(tests/allergy 무수정).
- **비교 기준 교체**: `tests/golden/baseline.json`을 a8d33f8 결과(0.67)로 다시 저장하고 `docs/review/golden_draft.md`에 전후 비교.

| 페르소나 | 조정 전 | 조정 후 | 상위 3개 밖 기대 레시피(후) |
| --- | --- | --- | --- |
| korean_lover | 1.00 | 1.00 | - |
| beginner | 0.33 | 1.00 | - |
| multi_allergy | 0.33 | 1.00 | - |
| low_spice | 0.67 | 0.67 | 감자조림 4위(0.815, 3위 계란볶음밥과 동점 → I·부족 재료·시간 순에서 밀림) |
| western_lover | 0.67 | 0.67 | 스테이크 4위 |
| japanese_lover | 1.00 | 1.00 | - |
| few_ingredients | 0.67 | 1.00 | - |
| seafood_expert | 0.67 | 0.67 | 오징어볶음(상위 5개 밖) |

- **multi_allergy**: 춘장 없는 짜장덮밥 2위 → 4위(I 0.80 → 0.73), 쯔유 없는 규동 3위 → 6위(I 0.73). 감자조림·소불고기가 2·3위로 올라옴. 상위 3개에서 둘 다 빠짐(확인).
- 일식파 5위에 규동 진입(계란찜 대신). 나머지 페르소나 상위 5개 변화는 표 참조.

1-4 허용된 불일치(1-5에서 기록, 사람 결정: 더 다루지 않음, 가중치 그대로):

- **low_spice 감자조림**: 4위. 점수 0.815로 3위 계란볶음밥과 동점이고, 동점 규칙 D(I → 부족 재료 수 → 조리시간 → id)에서 밀린다. 점수 차이가 아니라 동점 처리 순서 때문이라 규칙을 바꿀 근거가 약하다.
- **western_lover 스테이크**: 4위. 올리브유(비기본 seasoning)·버터(sub)를 보유하지 않아 I 0.50. 보유 재료가 실제로 부족한 상황이라 낮게 나오는 것이 규칙대로다.
- **seafood_expert 오징어볶음**: 상위 5개 밖. 양파·대파(sub) 미보유로 I 0.43, 매운맛·해산물 선호로는 커버리지 차이를 넘지 못한다. 재료가 부족한 레시피를 올리려면 I 가중치를 낮춰야 하는데 다른 페르소나에 영향이 커서 보류.
- 위 3건을 반영한 전체 적중률 0.88을 기준으로, **0.85 미만이면 실패하는 회귀 테스트**(`tests/golden/test_golden.py::test_top3_hit_rate_regression`, `MIN_HIT_RATE = 0.85`)를 추가했다. 기준을 바꾸려면 사람 승인이 필요하다.

1-5에서 정한 것(2026-10-03):

- **변환 함수 정식 모듈화**: `tests/support/engine_fixtures`의 `snapshot_from_compiled`·`recipe_from_spec`·`build_recommender`를 `storage/engine_source.py`로 옮김. API·골든셋(`tests/golden/golden.py`)·bench·테스트가 같은 함수를 쓴다. `tests/support/engine_fixtures.py`는 이 함수를 다시 내보내는 얇은 연결부로 남김(tests/allergy가 import하므로. tests/allergy는 무수정).
- **엔진 공급원 2가지**(부록 A): `load_files()`(knowledge 컴파일 + 레시피 시드), `load_db(conn)`(DB의 컴파일 결과·레시피 테이블 → `CompiledKnowledge`·`RecipeSpec`으로 되돌린 뒤 같은 변환). DB 공급원도 요청 중 그래프 탐색 없음. `tests/storage/test_engine_source.py`가 "DB 스냅샷 = 파일 스냅샷"과 같은 추천 결과를 검사. 고정 어휘(vocab)는 DB에 없어 `knowledge/vocab.yaml`을 읽는다.
- **API**(`api/main.py`, `schemas.py`, `present.py`): `GET /health`, `GET /vocab`, `GET /allergen-groups`(category: official 법정 표시 대상 / custom 자체 그룹 / bundle 묶음, 묶음 구성원, 안내 문구), `GET /ingredients/search?q=`(이름·별칭, 정확 → 앞부분 → 포함 순, concept는 `include_concepts=true`일 때만), `GET/POST /profiles`, `GET/PATCH/DELETE /profiles/{id}`, `PUT /profiles/{id}/preferences`(선호·알레르기 통째 저장), `POST /recommend`, `POST /admin/reload`. 실행은 `uvicorn api.main:default_app --factory`(기본 DB 공급원, `ENGINE_SOURCE=files` 가능).
- **입력 검증**: 모르는 재료·알레르기 그룹·음식 종류·조리기구 → 400, concept를 보유 재료로 → 400, 모양 오류(실력 1~3, 맛 0~5, preferred ≤ max, 절대 선호는 불선호만) → 422. 알레르기 선호는 polarity −1·is_hard로 강제 저장. 엔진 `ValueError` → 400(1-1 승인).
- **사용자 저장소**(`storage/users.py`): `SqlUserStore`(PostgreSQL)와 `InMemoryUserStore`(API 테스트용)가 같은 동작. `storage/tables.py`에 user_taste, user_equipment 추가(DDL은 그대로, 마이그레이션 변경 없음).
- **추천 응답(표시 계층)**: 항목마다 breakdown(라벨 포함), missing(이름), `missing_text`("양파, 춘장이 없습니다"), substitutions(이름·문장), notes, notices(안내 문구), label_check("제품 성분표를 확인하세요" + 재료별 사유), `exclusion_summary`(사유 라벨·개수·예시 레시피 3개), disclaimer. 제외 사유는 `logs/exclusions.jsonl`에 행 단위로 기록.
- **안내 문구**(`config/display.yaml`, 표시 전용): 고등어 선택 시 생선 전체 안내, 식용유(또는 식용유로 만든 가공품, contains 조회) 레시피에 기름 종류 확인, 연어덮밥 "횟감용 생연어 사용", 면책 문구, 제외 사유·알레르기 구분·맛·점수 항목 라벨.
- **성분표 확인 표시 기준**: 레시피 재료(선택·고명 포함) 중 어느 기본 알레르기 그룹에든 possible로 걸리거나 `confidence: low`인 재료가 있으면 표시. 사용자 알레르기와 무관하게 표시한다(사용자 알레르기에 possible로 걸리면 이미 제외됨).
- **조사 처리**: `engine/korean.py`(`josa`: 받침에 따라 은/는, 이/가, 을/를, 과/와. 한글이 아니면 "을(를)" 형태 유지). 엔진 설명 문장(`engine/explain.py`) 두 곳의 "은(는)"·"을(를)"을 이 함수로 바꿈(문장 표시만 변경, 판정 무관). 1-2 "사람 확인 필요"의 조사 항목 해소.
- **화면**(`app/main.py`): 사이드바 프로필 선택·생성, 탭 3개(추천 / 프로필·선호 편집 / 알레르기). 보유 재료·선호 재료는 별칭 검색 → 추가 방식. 알레르기는 법정 표시 대상·자체 그룹·묶음을 나눠 선택, 고른 그룹에 안내가 있으면 표시. 추천 카드에 점수 내역(막대), 부족 재료, 대체 안내, 메모, 안내 문구, 성분표 확인, 아래에 제외 사유 요약, 화면 하단 면책 문구.
- **bench**(`scripts/bench.py`): 실제 knowledge + 합성 레시피 1만 개(main 1~2, sub, 기본 양념, 고명, 1% 미매칭, 5% 필수 조리기구), 합성 사용자 300명(알레르기 0~3개, 선호, 매운맛 한도, 시간). 측정은 `Recommender.recommend` 한 번. 결과(seed 42): **p50 27.0ms, p95 101.6ms, 최대 135.7ms**, 엔진 조립 610ms, 평균 제외 280개. 기준 통과라 대체 역색인 캐시는 하지 않음.
- **테스트 추가**: tests/api(11), tests/logic/test_korean.py(17), tests/storage/test_engine_source.py(1), tests/storage/test_users.py(1), tests/golden 회귀(1).

1-6 사용자 점검 통과(사람, 2026-10-03, 화면에서 직접 확인, 모두 정상):

- 새우 알레르기 + 김치·돼지고기 → 김치찌개·김치전·계란찜 제외
- 매운맛 한도 1 → 제육볶음·오징어볶음 제외
- 초급자 → 쉬운 요리 우선
- 견과류 알레르기 → 멸치볶음(아몬드) 제외
- 해산물 전체 알레르기 → 해물파전 제외
- 재료 하나(감자) → 감자전·감자조림 추천
- 알레르기 탭의 법정/자체 그룹 구분, 고등어 안내 문구

1-6에서 정한 것(2026-10-03, 1-5 "사람 확인 필요" 결정 반영):

- **성분표 확인 표시**: 사용자에게 알레르기 설정이 있을 때만, 레시피(선택·고명 포함)에 `is_processed`이면서 `confidence: low`인 재료가 있을 때만 "제품 성분표를 확인하세요: 재료1, 재료2"로 표시. 소금·설탕처럼 가공품이 아닌 단순 재료는 대상 아님. possible 알레르기 기준은 뺌(사용자 알레르기에 possible로 걸리면 어차피 제외됨). `api/present.py`, `config/display.yaml`.
- **부족 재료 표시 구분**(표시만, 판정·점수 무관): "꼭 필요한 재료" = 선택이 아닌 main·sub·seasoning 줄의 미보유 재료(기본 양념은 보유 간주라 나오지 않음), "있으면 좋은 재료" = 고명(garnish)과 선택(optional) 재료. 엔진 `RecommendItem`에 표시용 `optional_missing`을 추가(엔진 `missing`은 그대로). 선택 재료 안내 문장은 "있으면 좋은 재료(없어도 조리할 수 있습니다)"로 합쳐 표시. API 응답 `required_missing`, `nice_to_have`, `missing_text`, `nice_to_have_text`.
- **다양성 보정 점수 차 제한**(plan.md 4-6 수정): 점수 차가 0.1 이하인 레시피끼리만 순서를 바꾼다(`config/weights.yaml diversity.max_score_gap: 0.1`, 키 누락 시 ValueError). 자리마다 남은 최고점 레시피가 한도를 넘으면 0.1 이내이면서 한도를 지키는 첫 레시피를 대신 올리고, 없으면 한도를 넘더라도 최고점을 올린다. 1-5에서 보이던 "0.57 중식이 0.72 한식보다 위" 같은 역전이 없어짐.
- **테스트 추가**(5개 + 기존 1개 확장): 다양성 점수 차(넘으면 순서 유지, 이내면 교체, 모든 역전 쌍 ≤ 0.1), 실제 설정 0.1, optional_missing 표시 전용, API 성분표 표시 조건(알레르기 없으면 없음, 가공품·low만, 이름 문구), 부족 재료 구분. 기존 다양성 테스트는 점수 차 제한 없음(1.0)으로 한도 규칙만 계속 검사.
- **최종 측정**: 전체 테스트 **323개 통과**(`--basetemp`), `git diff --stat 733d445 HEAD -- tests/allergy` 출력 없음, 골든셋 상위 3개 적중률 **0.88**(1-5와 같음, 페르소나별 상위 3개 변화 없음, `docs/review/golden_draft.md` 재생성), bench(합성 1만 개, 요청 300회, seed 42) **p50 19.5ms · p95 75.5ms · 최대 101.1ms**.

## 부가 트랙 viz (mvp-v1 이후)

| 단계 | 상태 | 완료일 | 비고 |
| --- | --- | --- | --- |
| viz-0 설계 확정 | 완료 | 2026-10-03 | plan.md 부록 D |
| viz-1 GET /graph | 완료 | 2026-10-03 | tests/viz/test_graph.py 9개, 전체 332 통과 |
| viz-2 trace·persona | 완료 | 2026-10-03 | tests/viz 47개 + tests/logic 8개 추가, 전체 379 통과, 적중률 0.88 |
| viz-3 3D 온톨로지 화면 | 완료(사람 확인 완료, 보완 반영) | 2026-10-03 | tests/viz/test_page.py 2개, 전체 381 통과. 보완 후 tests/viz/test_graph.py 2개 추가, 전체 383 통과 |
| viz-4 워크플로 재생 | 완료(사람 확인 완료) | 2026-10-03 | tests/viz/test_trace.py 1개 추가, 전체 384 통과 |
| viz-5 성능·문서 | 완료 | 2026-10-03 | 보완 2건, bench --trace, README. 전체 390 통과. 1천 개 회전 111fps, 로딩 3.1~4.9초(3초 목표는 사람 결정으로 기록만) |

viz-0에서 정한 것(2026-10-03, 사람 승인):

- **층 기준**: derived_from 존재 여부. derived_from은 있지만 가공품이 아닌 재료(콩나물)는 3층 + 툴팁 "가공품 아님".
- **페르소나 로더**: `tests/golden/golden.py`의 `load_personas`를 `storage/personas.py`로 옮김(API가 tests를 import하지 않게). 데이터 파일 위치는 그대로.
- **RecommendIn 확장**: `persona_id`(profile_id와 정확히 하나), `trace`.
- **trace 위치**: 엔진 파이프라인 본문을 공용 내부 함수로 옮겨 `recommend()`와 `trace()`가 같은 경로를 쓴다(판정 코드 무변경).
- **규모 목표**: 레시피 1천 개. 2000개 초과 분기(Points 렌더링)는 구현하지 않음. 측정은 viz-5에서 합성 1천 개로 로딩 3초·30fps.
- **진행 범위**: viz-0~3까지 이어서, viz-3 후 멈추고 사람 확인.

viz-1에서 정한 것(2026-10-03):

- `api/viz.py` `GraphCatalog`: 데이터 reload 때 만들어 `State.graph`에 둠. `(recipes, max_recipes)`별로 처음 만든 응답과 ETag(본문 sha256)를 캐시, `If-None-Match`가 같으면 304.
- 재료 노드에 `allergens`(기본 그룹 closure: 그룹·certainty) 포함(클릭 시 정보 표시용, 묶음은 구성원의 합이라 뺌). 레시피 노드에 `has_unmapped`, `required_equipment`, `spicy`.
- uses 링크 `line_no`는 엔진 `recipe_from_spec`과 같은 1부터 번호(trace path_links가 같은 id를 가리킴).
- 테스트: 노드·간선 수가 컴파일 행 수와 같음, 층 규칙(콩나물 3층·is_processed false), 링크 끝점 존재·id 유일, **모든 기본 그룹 closure 경로의 연속 쌍이 is_a·derived_from 링크로 이어지고 마지막 재료에 allergen 링크가 있음**, recipes 범위·max_recipes, ETag 304.

viz-2에서 정한 것(2026-10-03):

- **엔진**: `engine/trace.py` `RecommendTrace`(정리된 보유 재료, 기본 양념, owned_from(is_a 조상 → 근거 재료, ancestors 조회만), 필터가 쓴 알레르기 그룹·절대 불선호·매운맛 한도·시간 제한, 후보, 점수 순 ranked, 다양성 후 ordered). `Recommender._run(collect)`에 기존 본문을 옮기고 `recommend()`·`trace()`가 같은 경로를 쓴다. 판정·점수·정렬 코드는 변경 없음(`rank`와 `diversify` 호출을 두 줄로 나눈 것뿐). `recommend()`는 trace를 만들지 않는다.
- **페르소나**: `storage/personas.py`(Persona, load_personas, PERSONAS 경로). `tests/golden/golden.py`는 다시 내보냄.
- **API**: `RecommendIn`에 `persona_id`(profile_id와 정확히 하나, 아니면 422, 모르면 404), `trace`. 페르소나는 `max_time_min`을 비우면 페르소나의 희망 시간, `time_is_hard`는 둘 중 하나라도 true면 true. 응답은 trace=false면 기존과 같은 키(페르소나일 때만 `persona_id` 추가). `GET /personas` 추가. 제외 로그에 페르소나 실행은 `profile_id: null, persona_id`.
- **trace 표시(`GraphCatalog.trace`)**: 판정 없이 id 접두어·링크 id·라벨만 붙임. 알레르기 행 `path_links` = [묶음 → 기본 그룹] + 지정 링크 + via 쌍(역순) + 레시피 사용 링크(그룹에서 레시피 쪽으로 빛이 올라가는 순서). 묶음 target은 closure 행 조회로 `source_group`(같은 via를 가진 구성원) 결정. 후보 줄의 `basis`는 엔진 `CANDIDATE_ROLES`와 보유 근거로 표시(테스트가 후보마다 근거 줄이 있음을 확인). `excluded`는 대표 사유(알레르기 > 미매칭 > 절대 불선호 > 음식 종류 > 매운맛 > 조리기구 > 시간).
- **테스트**: 페르소나 8 + 프로필 3(해산물 묶음·밀, 매운맛 한도·시간 절대, 돼지고기·일식 절대 불선호)으로 trace 결과 = 일반 응답(items, 요약, 제외 수), trace 제외 행 = 엔진 `recommend()` 제외 행, 후보 = 통과 ∪ 제외, 순위 = items, path_links가 /graph에 모두 있음, 묶음 경로(계란찜 새우젓), 상속 보유(삼겹살 → 돼지고기), 사유 6종 등장, 요청 검증, 로그.

viz-3에서 정한 것(2026-10-03):

- **파일**: `viz/index.html`, `viz/style.css`, `viz/palette.js`(층 y·색·라벨), `viz/scene.js`(배치·그리기·강조), `viz/app.js`(로딩·검색·토글·정보·범례·HUD). API가 `/viz`(index.html)와 `/viz/static/*`(StaticFiles)로 제공.
- **CDN**: jsDelivr ESM `3d-force-graph@1.80.1/+esm`, `three@0.186.1/+esm`. 3d-force-graph의 ESM이 같은 three 0.186.1을 가져오므로 메시·재질이 한 인스턴스를 쓴다(테스트로 버전 고정 확인). three-spritetext는 three 0.177을 가져와 쓰지 않고 캔버스 스프라이트를 직접 만듦.
- **배치**: 층 y = −360/−120/120/360(묶음 −35). 알레르기 그룹은 원 위에 고정(fx·fz), 재료는 category별·레시피는 cuisine별 각도 구역 중심으로 약하게 당기는 힘 + 링크 힘(층 차이를 뺀 수평 거리만 당기도록 거리 = √(Δy² + 18²)). warmup 후 `cooldownTicks(0)`.
- **표현**: 법정 그룹 빨간 정육면체, 자체 그룹 주황 테두리 정육면체, 묶음 보라 팔면체, 원천 재료 초록 구, concept 와이어프레임, 가공품 파란 이십면체, 레시피 상아 원기둥, confidence low 노란 고리. 간선 색은 부록 D-2, possible·선택 재료는 흐리게.
- **강조**: 클릭 → 노드 + 1단계 이웃만 밝게(나머지 투명도 0.07), 연결 간선만 밝게(레시피-재료 간선은 숨김 상태여도 강조 시 표시), 선택 노드 이름 스프라이트 1개. 노드 재질은 (종류, 색, 투명도)별 공유 캐시에서 바꿔 끼움. 정보 패널: 재료(층, 종류, 별칭, 알레르기 closure, is_a 위아래, 원천·가공품, 쓰는 레시피 수), 레시피(역할별 재료·선택 표시, 필수 조리기구, 미매칭), 그룹(구성원, 직접 지정 재료, 포함된 묶음). 칩 클릭 시 그 노드로 이동.
- **검색**: 이름·별칭 정규화(소문자·공백 제거), 정확 → 앞부분 → 포함 순, 12개, 방향키·Enter.
- **측정 표시(HUD)**: 노드·간선·레시피 수, 로딩 시간(페이지 이동 시작 → 첫 화면, CDN 모듈 포함), fps. `window.__vizMetrics`, `window.__vizTimings`로도 읽을 수 있음(viz-5 측정용). `?graph=<url>`, `?recipes=all|none` 지원.
- **브라우저 확인(에이전트, 내장 브라우저)**: 레시피 50개 기준 로딩 1.2~1.4초(CDN 캐시 후), 120~140fps. 검색(새우젓·계란찜) → 카메라 이동·강조·정보 패널, 레시피 강조 시 역할별 재료 간선, 층·간선 토글, Esc 해제 동작 확인. 창이 가려져 있으면 requestAnimationFrame이 멈춰 로딩 시간이 길게 나오므로 viz-5 측정은 창을 보이는 상태에서 한다.

viz-3 보완(2026-10-03, 사람 브라우저 확인 후 요청 7건):

- **간선 투명도**: 기본(아무것도 선택 안 함) derived_from·알레르기 지정 0.15(possible 0.09), is_a·묶음 0.2. 선택·검색·재생에서 관련 간선만 원래 진하기(`palette.js linkAlpha`, 기본은 `linkRestAlpha`).
- **카메라·크기**: 초기 카메라를 위에서 35도 내려다보는 각도(거리 2100, 측정값 pitch 35.0°). 35도에서 층 원판이 겹치지 않게 층 간격을 240 → 360(y = −540/−180/180/540)으로 넓힘. 레시피 원기둥 반지름 5.5 → 9, 높이 2.6 → 5.
- **3층 배치**: derived_from 링크 힘 0.3 → 0.015, 3층이 끼는 is_a 0.3 → 0.08, 3층 구역 중심 인력 0.09 → 0.3, 3층 구역 반지름 216 → 290. 가공품이 가운데로 뭉치지 않고 분류 구역에 놓임(브라우저 확인).
- **라벨**: 모든 글자 스프라이트를 `sizeAttenuation: false`로 바꿔 카메라 거리와 무관하게 화면 픽셀 크기로 고정(층 20px, 구역 15px, 선택 노드 16px, 이웃 12px, 창 크기 변경 시 다시 계산). 구역 라벨은 원판 바깥쪽으로 옮기고, 무엇이든 강조 중에는 구역 라벨을 흐리게(0.3) 해서 노드 라벨이 읽히게 함. 라벨은 깊이 검사를 끄고 노드 위쪽에 붙음.
- **선택 강조 확장**: 재료를 선택하면 1단계 이웃 + 그 재료의 기본 그룹 closure 경로 전체(via 링크 → 그룹 지정 링크 → 그 그룹을 포함한 묶음). 직접 연결된 노드와 경로 노드에 이름 라벨(최대 60개, 재료·그룹 먼저). 예: 새우젓 → 새우 → 새우 그룹 → 갑각류·해산물 전체.
- **`/graph` 추가 필드**(판정 없음, 컴파일 결과 그대로): 재료 노드 `allergens[]`에 `via`(재료 id 경로)와 `path_links`(재료 → 그룹 순서 링크 id). 레시피 노드에 `allergens[]`(기본 그룹별 `certainty`(줄 중 하나라도 definite면 definite), `optional_only`(선택 재료 줄로만 걸림), `hits`(재료, certainty, role, optional, line_no)).
- **레시피 정보 패널 "걸리는 알레르기"**: 그룹명, 포함/포함 가능, "선택 재료 때문" 표시와 원인 재료(가능)(선택) 목록. 재료 정보 패널의 알레르기 줄에도 via 경로(예: 배추김치 → 새우젓 → 새우)를 함께 표시.
- **검색 함수 공용화**: `attachSearch(input, list, index, onChoose)`(viz-4 보유 재료 추가에서 재사용).
- **테스트**(tests/viz/test_graph.py 2개): 재료 노드의 모든 경로가 via 순서대로 링크를 따라 걸어지고 마지막이 그룹 지정 링크(closure 행 수와 일치, 김치 → 새우젓 → 새우 possible), 레시피 `allergens`가 줄 × closure 조인과 같음(계란찜: 새우는 선택 재료 새우젓 때문, 알류는 주재료).

viz-3 보완 2(2026-10-03, 사람 요청 — viz-4 뒤에 반영):

- **레시피 선택 시 알레르기 경로**: 레시피의 재료 줄(uses 링크)마다 재료 노드 `allergens.path_links` → 기본 그룹 → 그 그룹을 포함한 묶음까지 강조. 재료 선택과 같은 함수(`scene.js selectionFocus`의 `addPaths`).
- **흐린 경로**: 포함 가능(possible) 또는 선택 재료 줄의 경로는 간선 투명도 0.28, 그 경로에만 있는 노드는 0.55. 같은 간선·노드가 진한 경로에도 있으면 진하게. 재료 선택에서도 possible 경로는 흐리게.
- **패널과 같은 기준**: 그룹이 진하게 그려지는 조건 = 포함(definite)이면서 선택 재료가 아닌 줄이 있음. 정보 패널 "걸리는 알레르기" 칩도 같은 기준으로 진한 칩/점선 칩을 정한다(이전에는 certainty·optional_only를 따로 봐서 "포함 + 선택 재료"와 "포함 가능 + 일반 줄"이 섞인 그룹에서 어긋날 수 있었음).
- **확인**: `tests/viz/test_graph.py::test_recipe_selection_paths_match_info_panel`(모든 레시피에서 그래프 규칙으로 그린 그룹·진하기 = 패널 목록·진하기, 경로 링크 존재, 돈가스 알류·밀 포함, 대두·토마토·아황산류 포함 가능). 브라우저에서 화면 코드 그대로 레시피 50개를 차례로 선택해 `__viz.selectedGroups`와 패널 칩을 비교 → 불일치 0. 돈가스: 돼지고기·밀·알류 진함, 우유·대두·아황산류·토마토 흐림(빵가루의 우유·대두 possible은 데이터에 있는 그대로).

viz-4에서 정한 것(2026-10-03):

- **파일**: `viz/playback.js`(프로필 패널, 6단계 보기, 추천 카드, hover 정보). `scene.js`에 재생용 `setView(view)`(노드 색·크기·투명도, 간선 색, 라벨, 경로 빛), `setOffsets(Map, ms)`(높이 이동 애니메이션) 추가. 선택(클릭)이 재생 보기보다 우선이고, Esc·빈 곳 클릭으로 선택을 풀면 현재 단계 보기로 돌아간다.
- **판정 없음**: 모든 단계는 `POST /recommend`(trace: true) 응답만 그린다. 서버 변경은 trace에 `breakdown_labels`(config/display.yaml) 추가뿐.
- **프로필 패널**: `GET /personas` + `GET /profiles`(저장 프로필) 선택, 요리 실력·알레르기·조리기구·희망 시간 표시. 보유 재료는 칩(×로 빼기)과 재료·별칭 검색으로 추가(concept 제외)할 수 있고, 원래와 다르면 기존 API 필드 `pantry`(보유 재료 덮어쓰기)로 보낸다. `?persona=<id>`로 처음 선택할 페르소나 지정.
- **재생**: 이전/다음, 단계 번호 버튼, 자동재생(4초 간격, 6단계에서 멈춤), 끝내기. 재생 중 강조 밖 노드 투명도 0.025, 간선 0.01(선택 강조 0.07·0.03보다 더 흐리게).
  1. 보유 재료: 입력(초록, 크게), is_a 상속(연초록 + 이름 "(상속)", 상속 is_a 간선), 기본 양념(흐린 초록). 패널에 "상위 ← 근거 재료" 목록.
  2. 후보: 후보 레시피(노랑)와 근거 줄(`basis`)의 레시피-재료 간선(역할 색), 대체로 충족한 재료. 후보가 아닌 레시피는 이후 단계에 나오지 않음을 안내.
  3. 제외: 레시피 색 = 대표 사유(알레르기 빨강, 미매칭 진한 빨강, 절대 불선호 재료 주황, 매운맛·조리기구·시간·음식 종류 회색), 80만큼 가라앉음. 알레르기·절대 불선호 행은 `path_links`를 사유 색으로 칠하고, 빛 입자가 그룹(묶음이면 묶음 → 기본 그룹) → via 역순 → 레시피 순서로 이동. 행을 클릭하면 그 레시피의 경로만 보기(다시 클릭하면 전체).
  4. 점수: 통과 레시피가 점수 × 150만큼 올라감, 상위 20개 "이름 점수" 라벨, 패널에 I·K·T·P·D·M 표. hover 툴팁에 항목별 값 × 가중치.
  5. 순위: 표시 범위(limit) 안 레시피에 "n위" 라벨, 다양성 보정으로 자리가 바뀐 레시피는 주황 + "(점수 m위)".
  6. 추천 카드: 최종 레시피와 주재료 간선 강조, 패널에 카드(점수, 항목별 막대, 꼭 필요한 부족 재료, 있으면 좋은 재료, 대체 안내, notes·notices, 성분표 확인). 카드·칩 클릭 시 그 노드로 이동.
- **위치 이동 방식**: `node.y`(= fy)만 바꾸고 `d3ReheatSimulation()`을 부른다. `cooldownTicks(0)`이라 force tick 없이 노드·간선 위치만 한 번 동기화된다(three-forcegraph `layoutTick` 확인). graphData 재설정 없음.
- **브라우저 확인(에이전트, 내장 브라우저, 1600×1000)**: multi_allergy에 계란을 추가하면 계란찜이 3단계에서 빨갛게 460(원래 540)까지 가라앉고 계란 → 알류, 새우젓 → 새우 → 새우 그룹 → 갑각류 묶음 경로가 빨갛게 보임. multi_allergy 기본 보유 재료로는 돼지고기 김치찌개 행에서 배추김치 → 새우젓 → 새우 → 새우 ⊂ 갑각류 경로. low_spice에서 닭볶음탕·비빔밥·두부조림·마파두부가 회색으로 가라앉음, 감자 그라탕은 조리기구(회색). 4~6단계 높이·라벨·카드 표시, 콘솔 오류 없음, 정지 상태 약 110fps.
- **알게 된 것**: multi_allergy 기본 보유 재료(불고기용 소고기·당근·양파·돼지고기·감자·쌀·두부)로는 계란찜이 **후보가 아니다**(주재료 계란·고명 대파 미보유). 엔진은 후보만 필터하므로 trace에 계란찜 제외 행이 없다. 판정 코드를 바꾸지 않고 확인할 수 있도록 보유 재료 편집을 넣었다(테스트 `test_trace_carries_breakdown_labels_and_pantry_override`가 계란 추가 시 계란 → 알류, 새우젓 → 갑각류 묶음 제외 행을 확인).
- **저장 프로필**: 로컬 DB에는 데모(계란 알레르기)·홍길동(알레르기 없음) 2개뿐이라 새우 알레르기 프로필은 없다. 새우 경로는 multi_allergy(갑각류 묶음)의 김치찌개 행이나 korean_lover에서 배추김치 노드 클릭으로 볼 수 있다.

viz-5(2026-10-03, 완료 — 로딩 3초 미달은 사람 결정으로 기록만):

- **보완 1 라벨 겹침**: `scene.js`에 화면 좌표 겹침 정리. 라벨에 `priority`가 있으면(4단계 점수 순위, 5단계 최종 순위) 매 프레임 화면 상자를 계산해 순위 순으로 놓고, 이미 놓인 라벨과 겹치면 숨긴다. 마우스를 올린 노드의 라벨은 항상 보인다(`onNodeHover`). 카메라 회전·확대·높이 이동을 따라 다시 계산. 점검용 `__viz.labelStates`. 브라우저 확인: 시연 새우 알레르기 5단계에서 한식 구역에 몰린 10개 중 겹치지 않는 1위·4위만 보이고, 두부조림(2위)에 마우스를 올리면 "2위 두부조림" 표시.
- **보완 2 시연 프로필**: `scripts/seed_demo_profiles.py`(같은 이름 있으면 건너뜀, `--dry-run`은 id 검증만). 로컬 DB에 #3 시연: 새우 알레르기, #4 시연: 매운 것 못 먹음, #5 시연: 견과류 알레르기 생성, 두 번째 실행은 모두 건너뜀 확인. 소고기는 `beef`(쇠고기), 견과류는 `nuts_bundle`, 조리기구는 냄비·프라이팬.
  - 새우: 후보 16, 3단계 제외 4개(계란찜 = 새우젓(선택) → 새우, 돼지고기 김치찌개·김치전 = 배추김치 → 새우젓 → 새우 포함 가능, 해물파전 = 새우(선택)).
  - 매운 것: 후보 9, 매운맛 한도 초과 5개 회색(제육볶음·돼지고기 김치찌개·오징어볶음·두부조림·마파두부).
  - 견과류: 후보 5, 멸치볶음 = 아몬드 → 기타 견과류 ⊂ 견과류(선택 재료), 감자 그라탕은 조리기구(오븐).
  - 테스트 `tests/viz/test_demo_profiles.py` 5개(id 존재, 재실행 건너뜀, 세 장면이 trace에 나옴).
- **bench**: `--trace`(같은 사용자로 recommend()와 trace(), trace + 표시 변환(GraphCatalog.trace)을 함께 측정, 추천 결과 일치 assert), `--graph-out`(합성 레시피로 `/graph?recipes=all`과 같은 JSON). 출력 위치 `viz/_bench/`는 .gitignore.
- **trace 영향**(합성 1만 개, 요청 300회, seed 42): recommend p50 22.8 · p95 41.7ms, trace() p50 22.6 · p95 39.8ms(평균 −8%, 측정 오차 범위 — 같은 코드 경로 + 중간 결과 보관뿐), trace() + 표시 변환 p50 38.0 · p95 87.2ms(평균 +62%). 엔진 기준 p95 200ms 안.
- **시각화 측정**(합성 1천 개: 노드 1279 · 간선 9635 · 3.1MB, 내장 브라우저 1024×768, AMD Radeon 890M / ANGLE D3D11):
  - 회전: 5초 동안 카메라를 한 바퀴 돌림 → **111fps**(최악 프레임 17ms). 목표 30fps **통과**.
  - 로딩(페이지 이동 → 첫 화면): **3.10초**(CDN 캐시, 다른 탭 없음, 최선), 3.86초, 4.92초, 7.08초(CDN 캐시 없음). 목표 3초 **미달**.
  - 구성: CDN 모듈 약 0.45초(캐시 시), 그래프 JSON 60~100ms, createScene 120~210ms, **첫 프레임까지 1.8~2.2초**(대부분 아래 warmup), 셰이더 8개 컴파일 약 0.2초.
- **원인**: 첫 프레임 전의 force 레이아웃 warmup(120틱)이 메인 스레드 한 번의 긴 작업(longtask 1.6~2.5초)이다. 틱당 약 22ms이고 간선 수에 비례한다(레시피 0개면 160틱 0.4초, 1천 개면 120틱 2.5초, 40틱 0.96초). 강도 0인 간선도 순회 비용이 같아 레시피-재료 간선 강도를 낮추는 것으로는 줄지 않는다(2.8 → 2.6초). 렌더링 자체는 빠르다(회전 111fps).
- **개선안**(사람 결정 필요, 부록 D-1 "x·z만 force로 계산" 변경이 걸림):
  1. **(추천) 서버에서 레이아웃 미리 계산**: `/graph` 생성 시(데이터 reload 때 한 번, 캐시·ETag와 함께) 같은 규칙(구역 중심 + 링크 인력)으로 x·z를 계산해 노드에 넣고, 화면은 `warmupTicks(0)`. 예상 로딩 ≈ 0.45 + 0.1 + 0.2 + 0.3 ≈ 1.1초. 재현 가능한 배치(같은 데이터 = 같은 위치)라는 장점도 있다. Python 쪽 force 구현(numpy 없이 단순 반복) 또는 결정적 배치(구역 각도 + 주재료 방향 가중 평균)가 필요.
  2. 브라우저에 레이아웃 캐시: ETag(knowledge_hash)별로 x·z를 localStorage에 저장 → 두 번째 로딩부터 warmup 0. 첫 로딩은 그대로 미달.
  3. warmup 틱을 그래프 크기에 따라 줄이기(1천 개 40틱 → 약 1초 절약, 로딩 약 2.1~2.9초 예상): 가장 작은 변경이지만 배치 품질(3층 구역 배치, 레시피가 주재료 쪽으로 당겨짐)이 떨어질 수 있어 화면 확인 필요.
  4. warmup을 Web Worker로 옮기고 먼저 구역 배치로 그린 뒤 결과가 오면 위치 갱신: 첫 화면은 빠르지만 노드가 움직이는 모습이 보이고 구현이 가장 크다.
- **README**: 6-1에 Windows 실행 순서, 재생 조작, 시연 순서 표(프로필·단계·클릭할 것), 7에 bench --trace·--graph-out 추가.
- **사람 결정(로딩 미달 처리)**: 시각화는 레시피 선택 과정을 보여 주는 시연용이고 실제 웹앱은 그래픽 없이 동작하므로 1천 개 로딩 시간은 중요하지 않다 → 개선을 적용하지 않고 측정값·원인·개선안만 기록, plan.md D-6에 결과 기록, 개선은 "다음 단계 제안" 8번. 실제 앱 기준(엔진 p95 200ms)은 충족.
- **최종**: 전체 테스트 390개 통과, `tests/allergy` 무변경, viz-5 커밋, 태그 `viz-v1`.

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

## 데이터 확장 트랙: 레시피 1차 확장 (브랜치 `feature/recipe-expansion`)

### data-1 레시피 1차 초안 50개 (2026-10-04, 검수 대기)

- **결정(사람, 2026-10-04)**: docs/decisions.md D3 보완. 1차로 50개를 추가해 합계 100개, 출처 `agent_draft` 유지(외부 본문 복제 금지), 신규 50개는 모두 `status: draft`이며 검수표 승인 전에는 published로 바꾸지 않는다.
- **근거**: 공백 분석(김치볶음밥 0개, 매운맛 1 이하 닭 요리 1개, 햄 main 레시피 없음, multi_allergy·western_lover 상위 10 미달, 대두·밀 알레르기 안전 레시피 12·9개).
- **구성**: 한식 30, 양식 8, 일식 6, 중식 6. 난이도 1: 33, 2: 15, 3: 2. 15분 이하 17개.
  - main 기준: 닭 2 → 13(신규 11), 가공육 1 → 6(신규 5: 통조림햄 구이, 소시지 채소볶음, 햄 감자볶음, 햄치즈 샌드위치, 까르보나라(베이컨)), 해산물 4 → 11(신규 7). 매운맛 1 이하 닭(main) 1 → 10.
  - 구성 조건(재료 목록·allergen_closure 기준, possible 포함): 계란·우유·갑각류 모두 없음 29개(조건 15 이상), 대두·밀 없음 14개(조건 5 이상), 매운맛 1 이하 44개(조건 40 이상).
- **새 재료**: `soft_tofu`(순두부, derived_from soybean 확실, draft). 이름이 겹치지 않도록 `tofu`의 별칭 '순두부'를 soft_tofu로 옮김(tofu의 is_a·derived_from은 그대로). tofu와 is_a로 잇지 않아 두부 보유로 순두부찌개가 매칭되지 않는다. 건고추는 홍고추·청양고추로 대체해 추가하지 않음.
- **검수표**: `docs/review/recipes_review.md`를 검수 대기(draft) → 검수 완료(published) 순으로 나누고, 각 묶음 안에서 confidence low를 맨 위에 두도록 `scripts/make_recipe_review.py` 수정. 재료 검수표(`ingredients_review.md`)도 재생성.
- **테스트 수정(tests/kb, tests/api만)**:
  - test_recipe_seed: 개수는 시드 폴더에서 셈. 1-3 검수 완료 50개 id 목록(`PUBLISHED_IDS`)이 그대로 published이고 한식 30·기타 20 구성 유지, published는 이 목록과 정확히 같고 필수 항목을 모두 갖춤, 목록 밖은 모두 draft. 김치 고정 3개 집합 → 김치류(배추김치·깍두기·열무김치)가 든 모든 레시피(published만 / draft 포함 두 경우)가 새우 알레르기로 제외되는지, 각 레시피가 실제로 후보가 되도록 main 재료를 보유로 넣고 제외 기록까지 확인. 기본 설정이 draft를 제공하지 않는지 추가.
  - test_real_knowledge: "전부 reviewed" → `DRAFT_INGREDIENTS`({soft_tofu})만 draft, 나머지 전부 reviewed. soft_tofu 대두 definite·별칭 '순두부' 검사 추가.
  - test_api: /health 레시피 수를 시드 파일 수(draft 포함)와 비교.
- **결과**: validate_data 통과(재료 253개, 경고 3건, 레시피 100개 오류 0건, 미매칭 0). 전체 394개 통과(tests/allergy 118개, 무수정). 기본 설정(published만)이라 골든셋 적중률은 0.88 그대로.
- **영향 미리보기**(draft 포함 가정, config 수정 없이 `serve_draft_recipes=True` 인자로만 계산, `.scratch/recipe_gap/preview.md`): 전체 적중률 0.88 → 0.58. beginner·few_ingredients 0.33, korean_lover·multi_allergy·japanese_lover 0.67. multi_allergy·western_lover 상위 10 미달 해소(9 → 18, 5 → 10 통과). 검수 후 published로 바꾸려면 골든셋 기대값 재검토 또는 회귀 기준(MIN_HIT_RATE 0.85) 결정이 먼저 필요하다.

### data-2 soft_tofu is_a tofu, 골든셋 재검토 자료 (2026-10-04)

- **결정(사람, 2026-10-04)**: `soft_tofu`에 `is_a: [tofu]` 추가(별칭·derived_from 그대로). 이유: 독립일 때 "두부" 절대 불선호 사용자에게 순두부찌개가 제외되지 않았고, 사용자가 "순두부"를 입력하면 data-1 전에는 두부로, data-1 후에는 순두부로 해석되어 절대 불선호 결과가 달라졌다.
- **효과**(draft 포함 엔진): 두부 절대 불선호 → 순두부찌개 제외. 순두부 보유 → 된장찌개·두부조림·마파두부도 후보(순두부가 두부의 하위 재료라서). 두부 보유 → 순두부찌개는 여전히 후보 아님(상위 보유로 하위 충족 안 함). 대두 알레르기 판정(allergen_closure)과 골든셋 적중률(0.88 / draft 포함 0.58)은 변화 없음.
- **"순두부" 절대 불선호의 범위(사람 결정 필요)**: 순두부를 절대 불선호로 두면 순두부찌개뿐 아니라 두부를 쓰는 된장찌개·두부조림·마파두부도 제외된다. 판정 경로: `engine/filters.py` `UserConstraints.dislike_hits` → 컴파일된 `ingredient_contains`(`kb/graph.py` `expand_contains`). plan.md 부록 C의 contains 규칙("x 자신에 is_a 하위 개념이 있으면 그 하위 개념도 possible로 포함")에 따라 두부는 순두부를 possible로 포함한다(경로 tofu → soft_tofu). 엔진은 부록 C대로 동작하지만, plan.md 4-3의 요약("is_a 하위와 derived_from 파생까지 제외")에는 이 규칙이 빠져 있다. 원하는 동작을 테스트로 고정하지 않았다(아래 "사람 확인 필요").
- **테스트 추가**: `tests/kb/test_soft_tofu.py` 4개(soft_tofu contains 두부·대두 definite, 두부 절대 불선호 → 순두부찌개·두부 요리 제외, 순두부 절대 불선호 → 순두부찌개 제외, 대두 알레르기 → 순두부찌개 제외). 기존 테스트는 바꾸지 않음.
- **골든셋 재검토 자료**: `docs/review/golden_review.md`. 적중률이 떨어진 5명의 draft 포함 상위 10(점수, 동점 묶음, 신규 여부, 동점이 갈린 기준, 다양성 보정 이동)과 참고 지표 "동점 인정 적중률"(기대 레시피 점수가 3위 점수와 같으면 적중: 전체 published만 0.92, draft 포함 0.83). 실제 평가 방식은 그대로이며 expected_top3는 사람이 고른다. 생성 도구는 커밋하지 않았다(`.scratch/`).
- 원인 분석 요약(data-1 검토): 역전 9건 중 7건이 점수 완전 동점(소수 셋째 자리)이었고 조리시간 → id 순으로 갈렸다. 나머지는 시간 점수 M(감자조림 25분 > 희망 20분) 1건, 재료 점수 I(연어 소금구이 기본 양념 외 재료 1개) 1건.

## 사람 확인 필요

- **(data-2) "순두부" 절대 불선호 범위**: 지금은 순두부 절대 불선호가 두부 요리(된장찌개·두부조림·마파두부)까지 제외한다(plan.md 부록 C의 contains 규칙). 순두부찌개만 제외하려면 엔진 판정 규칙(부록 C·`expand_contains`) 변경이 필요하고, 이 규칙은 "젓갈류 → 새우젓" 같은 넓은 재료의 안전 판정에도 쓰인다. 지금 동작을 유지할지, 규칙을 바꿀지 정한다. 어느 쪽이든 plan.md 4-3 문구를 부록 C와 맞춘다.
- **(data-2) 골든셋 기대값**: `docs/review/golden_review.md`를 보고 expected_top3를 다시 고를지 정한다.
- **(data-1) 레시피 1차 초안 50개 검수**: `docs/review/recipes_review.md` "검수 대기(draft)". confidence low 9개(가공육 4, 음식 종류 판단 3, 순두부 신규 재료 1, 깐풍기 매운맛 1). 신규 재료 `soft_tofu`(draft) 검수: `docs/review/ingredients_review.md`.
- **(data-1) published 전환 전 골든셋 처리**: draft를 모두 published로 바꾸면 적중률 0.58로 회귀 기준(0.85) 아래. expected_top3 재기입·기준 조정·다양성 한도 중 무엇을 할지 사람이 정한다.
- (선택) K에 선호 strength를 반영하지 않음(plan 4-4 표대로 1.0/0.5/0.1). 반영하려면 plan 4-4 수정이 필요하다. Phase 2 이후 검토.
- (해결, 1-6) 성분표 확인 표시 범위, 부족 재료 표시 구분, 다양성 보정 역전 → 위 "1-6에서 정한 것".

## 1-5 화면 요구사항

0-4 검수에서 사람이 정한 안내 문구(Phase 1-5 Streamlit 화면에 반영):

- 알레르기 선택에서 **고등어**를 고르면: "다른 생선에도 반응하면 '생선 전체'를 선택하세요."
- **식용유**가 들어간 레시피(또는 식용유 재료 표시)에: "제품의 기름 종류(콩기름 등)를 확인하세요."

1-3 레시피 검수에서 사람이 정한 안내 문구:

- **연어덮밥**(`salmon_don`) 카드에: "횟감용 생연어 사용"

## 알려진 문제

- (해결, viz 보완) /viz에서 노드가 잘 안 눌리던 문제: 기본 카메라에서 재료 노드 지름이 약 2.5px(레시피 약 7px)라 정확히 맞혀야만 클릭됐다. 노드마다 보이지 않는 판정용 구(반지름 12, 약 14px)를 붙였다. 판정 구가 겹치는 밀집 구역에서는 카메라에 가까운 노드가 잡힌다(커서에 가장 가까운 노드가 아닐 수 있음). 구역 이름 라벨(김치·채소 등)은 노드가 아니라 클릭되지 않는다.
- **D4 알레르기 목록 미확정**: allergens.yaml은 0-2에서 example 그대로 `status: draft`로 옮긴다. 0-4 시작 전에 사람이 표시 대상 목록과 생선 그룹 단위를 확정해야 한다(액젓의 derived_from 대상도 이에 따라 정해짐).
- (해결) `garlic_minced` → `garlic` 변경을 `config/pantry_staples.yaml`에 반영함.
- 콩기름(soybean_oil)과 식용유(cooking_oil) 사이 is_a 관계는 두지 않았다. 두면 식용유(기본 양념)가 대두 possible이 되어 대두 알레르기 사용자에게 기름을 쓰는 레시피가 대부분 제외된다. 0-4 검수에서 정한다.
- (해결) 재료 없는 알레르기 그룹 경고는 0-4에서 모두 해소.
- 컴파일 경고 3건(의도): 콩나물 derived_from 대두이나 가공품 아님, 멸치액젓·까나리액젓 is_a 4단계(액젓 → 젓갈류 → 해산물).
- (해결) 아몬드·밤 → 기타 견과류, 낙지·문어·주꾸미 → 기타 연체류(0-4 검수).
- (해결) `allergen_group.official/source` DB 저장: 마이그레이션 0002.
- (해결) 1-1부터 `uv run pytest` 전체 통과.
- 샌드박스 환경에서는 pytest의 기본 임시 폴더 접근이 막혀 `--basetemp`를 지정해 실행했다(일반 환경에서는 불필요).
- (해결, 1-6) 다양성 보정으로 점수가 크게 낮은 항목이 위에 오던 문제: 점수 차 0.1 이내만 교체.
- (1-5) FastAPI TestClient가 `httpx` 사용 관련 StarletteDeprecationWarning을 낸다(동작 영향 없음).
- 정제 식용유(콩기름 등)의 대두 알레르기 처리 기준은 0-4 검수표에서 사람이 판단한다.

## 다음 할 일

- MVP(Phase 0~1) 완료. Phase 2는 사람이 범위를 정한 뒤 시작한다(아래 "다음 단계 제안").
- 시각화 트랙 완료(viz-v1). 시연은 README 6-1 "시연 순서"(시연 프로필은 `scripts/seed_demo_profiles.py`).
- 새 재료를 추가할 때는 status: draft로 넣고 검수표(`scripts/make_review.py`)로 사람 확인 후 reviewed.
- 데이터 확장 트랙(data-1, `feature/recipe-expansion`): 신규 레시피 50개 draft 검수 대기. 승인된 레시피는 published로 바꾸고 `tests/kb/test_recipe_seed.py`의 `PUBLISHED_IDS`에 추가, soft_tofu 승인 시 reviewed로 바꾸고 `tests/kb/test_real_knowledge.py`의 `DRAFT_INGREDIENTS`에서 뺀다. published 전환 전에 골든셋 처리 방법을 정한다.

## 다음 단계 제안 (Phase 2 이후, 범위 밖)

Phase 2 할 일(plan.md 6장 로드맵 기준, 착수 전 사람이 범위 확정):

1. **LLM 자연어 입력 해석**(plan 2장 1단계): "냉장고에 계란이랑 김치 있어, 안 맵게"를 보유 재료·맛 한도·요청 파라미터로 변환. 결과는 반드시 정규 재료 id로 매핑하고, 매핑 실패어는 `unmapped_term`에 기록. 알레르기 판정에는 LLM을 쓰지 않는다(안전 규칙).
2. **LLM 설명 생성**(4-7): 엔진 결과(breakdown, 부족 재료, 대체, 제외 사유)만 근거로 문장을 다듬는다. 엔진 결과를 먼저 보여 주고 설명은 이어서 채운다(7-4). 근거 밖 내용 생성 금지 테스트.
3. **식단 조건 필터**(채식 등, B2 결정으로 Phase 2): target_type 추가와 vocab, 필터 테스트.
4. **별칭·미매칭 보강 흐름**: `unmapped_term` 누적 → 검수표 → knowledge 반영. 자동완성 품질을 위한 pg_trgm 인덱스.
5. **데이터 확장**: 레시피 공백(김치볶음밥, 맵지 않은 닭 요리, 햄 활용 요리) 추가(→ data-1에서 초안 작성, 검수 대기), `confidence: low` 재료 70개 재검수, substitutes.yaml(아직 draft) 검수.
6. **선호 축 확장**: 요리 유형(찌개·볶음·면) 선호, K에 선호 strength 반영 여부(plan 4-4).
7. **운영 준비**: Supabase 배포 설정, API 인증 범위(D1은 개인용 기본값), 제외 로그(`logs/exclusions.jsonl`) 보존 정책, CI에서 tests/allergy 실패 시 배포 차단.

8. **시각화 1만 개 대응**(viz 범위 밖, 사람 결정): 레시피가 2000개를 넘으면 레시피 층을 `THREE.Points` 한 번의 draw call로 그리고 hover는 화면 근접 검색으로 처리, 레시피 층 클러스터 요약(cuisine별 묶음 노드 → 확대 시 펼침), trace 제외 행 요약 모드. 먼저 로딩: 첫 화면 전 force warmup이 틱당 약 22ms(1천 개 1.6~2.5초)라 규모가 커지면 지배적이다 → `/graph` 생성 시 서버에서 x·z 배치를 미리 계산하고 화면은 warmup 0(1천 개 예상 약 1.1초, 같은 데이터 = 같은 배치). 대안: 브라우저 배치 캐시, warmup 틱 축소, Web Worker(장단점은 위 viz-5 기록).

9. **동점이 많은 순위**(data-1 검토, 2026-10-04): 맛·음식 종류·재료 선호 입력이 적은 사용자는 T·K·P가 중립값으로 모여 점수 동점이 많고, 순위가 동점 처리 규칙(I → 부족 재료 수 → 조리시간 → id 순)으로 정해진다. id 순은 의미 없는 순서다. 동점 처리 기준 재검토(예: 다양성·최근 추천 반영) 필요. 근거: `docs/review/golden_review.md`.
10. **다양성 한도의 상위 집중**(data-1 검토): 같은 main 재료 한도(3)는 4번째부터만 막으므로 상위 3개를 같은 main 재료가 모두 차지할 수 있다(draft 포함 multi_allergy: 감자전·감자볶음·감자조림이 1~3위, 니쿠자가는 점수 0.1 이내 대안이 없어 8위에 감자 4번째로 들어감). 상위 구간에 별도 한도를 둘지 검토.

Phase 3 이후(참고): user_event 기반 개인화 재정렬(4-6 상위 50개), 유통기한(expires_on) 활용, 장보기 목록, React 화면.
