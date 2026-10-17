# 진행 상황

> 에이전트는 각 단계가 끝날 때마다 이 파일을 갱신합니다. 새 세션은 이 파일부터 읽습니다.

## 현재 단계

**MVP 완료(Phase 1-6, 2026-10-03, 태그 `mvp-v1`).** 전체 테스트 323개 통과, 골든셋 상위 3개 적중률 0.88, bench p95 75.5ms(기준 200ms). Phase 2 이후 할 일은 "다음 단계 제안". 단계별 경과는 아래 기록. **tests/allergy/는 수정·삭제·skip 금지**(0-3 승인). 하나라도 실패하면 엔진 결함이다.

**통합 트랙 int-1**(2026-10-16, 브랜치 `feature/ontology-integration`): 기존 브랜치 5개를 새 브랜치에 병합해 레시피 200개(published 50 + draft 150)·재료 255개를 하나의 그래프로 연결. int-2: 살림팝 169개 시드(draft) 변환, 식품안전나라 1153개 그래프 표시 전용 연결 → 그래프 레시피 1522개. 미매칭 보강은 다음 단계. int-3: /viz 기본을 나무 배치(뿌리 알레르기·줄기 재료·가지 가공품·잎 레시피 반구)로, 잎 기준 주재료/음식 종류, 평면 유지. 아래 "통합 트랙" 참조. int-4(2026-10-17): main 병합 준비 — 롤백 태그 `checkpoint/before-int-4`, DB 포함 전체 473개 통과(DB 통합 테스트에서 분량 반올림 결함 발견·수정), bench p95 79.8ms, PR로 올림. 새 레시피는 계속 draft라 기본 추천 결과는 MVP와 같다.

**미매칭 보강 트랙 um-1**(2026-10-17, 브랜치 `feature/unmapped-resolution`, main(PR #4 병합 후)에서 분기): 세 출처(자취요리신·살림팝 = 엔진, 식품안전나라 = 표시 전용) 미매칭 표기를 분류한 검수표 `docs/review/unmapped_review.md`. knowledge·변환 결과는 아직 바꾸지 않음(사람 검수 대기). 아래 "미매칭 보강 트랙" 참조. um-2(2026-10-17): 사람 결정 반영 — 별칭 91개·새 재료 106개(draft)·원본 이름 보정표 54항목·식품안전나라 머리말 규칙, 시판 제품 안내 표시. 엔진 레시피 미매칭 없는 레시피 75 → 238/269, DB 포함 전체 488개 통과.

**부가 트랙 viz 완료**(2026-10-03, 태그 `viz-v1`, 3D 온톨로지 + 추천 워크플로 시각화, docs/plan.md 부록 D). 전체 테스트 390개 통과. 아래 "부가 트랙 viz" 참조.

**데이터 확장 트랙 data-1**(2026-10-04, 브랜치 `feature/recipe-expansion`, 기준점 태그 `checkpoint/before-recipe-expansion`): 레시피 1차 초안 50개를 draft로 추가(합계 100개, published 50 그대로). 사람 검수 대기. data-2(2026-10-04): soft_tofu is_a tofu, 골든셋 재검토 자료 `docs/review/golden_review.md`. data-3(2026-10-04): "순두부" 절대 불선호 범위 확정, 불선호 제외 범위 측정, `scripts/make_golden_review.py`. 전체 테스트 399개. data-4(2026-10-04): 신규 레시피 draft 유지, 검수·골든셋 재선정 보류, PR로 올림. 아래 "데이터 확장 트랙" 참조.

**식품안전나라 가져오기 트랙 fs-1~2**(2026-10-16, 브랜치 `feature/foodsafety-import`, `feature/recipe-expansion`에서 분기): D3 보완 2(개인용·출처 표시)로 식품안전나라 조리식품 레시피 DB 내려받기·변환 도구 추가(fs-1), 실제 1153개 변환, 재료 줄 미매칭 28.9%(fs-2). fs-5: D3 보완 3으로 원본·변환 결과 커밋(공개 저장소, 사람 결정). 아래 "식품안전나라 가져오기 트랙" 참조.

**외부 레시피 분석 트랙 adhoc-1**(2026-10-16, 브랜치 `feature/adhoc-recipe-analysis`, `feature/foodsafety-import`에서 분기, 사람 요청·승인): AI가 만든 레시피처럼 DB에 없는 레시피의 재료를 붙여 넣으면 재료 매핑·is_a·원천·알레르기 경로를 보여 주고 `/viz` 그래프에 임시 노드로 겹쳐 그린다. 저장 안 함, LLM 없음. docs/plan.md 부록 E. 아래 "외부 레시피 분석 트랙" 참조.

**재료 ↔ 레시피 조회 트랙 ui-1**(2026-10-16, 브랜치 `feature/ingredient-recipe-browse`, fs-3 커밋에서 분기): 추천 탭에서 그 자리에서 재료를 골라 추천받기, 추천 카드에서 레시피 전체 재료(보유 여부)·조리 순서 보기, `GET /recipes/{id}` 추가. ui-2(2026-10-16): **재료로 레시피 찾기**(여러 재료를 고르면 조합해 만들 수 있는 레시피와 1~2개 모자란 레시피, 알레르기는 제외 대신 주의 표시) — Streamlit 탭, `/viz` 카드, `GET /browse`. 전체 테스트 432개 통과(DB 테스트 9개 skip). 아래 "재료 ↔ 레시피 조회 트랙" 참조.

**데이터 트랙 sc-1(브랜치 `data/simplecooking-ontology`, 2026-10-16)**: 자취요리신 YouTube 레시피 100개를 시드로 변환해 기존 50개와 합쳐 150개. 새 100개는 draft(검수 전). 전체 테스트 389개 통과. 아래 "데이터 트랙 sc-1" 참조.

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

### data-3 "순두부" 절대 불선호 범위 확정, 불선호 제외 범위 측정 (2026-10-04)

- **결정(사람, 2026-10-04)**: 지금 동작 유지. "순두부" 절대 불선호는 순두부찌개와 함께 두부를 쓰는 된장찌개·두부조림·마파두부도 제외한다(plan.md 부록 C의 is_a 하위 possible 규칙). `tests/kb/test_soft_tofu.py`에 테스트 1개 추가.
- **plan.md 4-3 수정**: 절대 불선호 문장을 부록 C와 맞춤(불선호 재료를 is_a 하위로 가진 넓은 재료도 포함 가능으로 제외). 규칙 자체는 바꾸지 않음.
- **불선호 제외 범위 측정**: 하위 재료 26개를 하나씩 절대 불선호로 두면, 직접 들어간 레시피보다 "포함 가능"으로 제외되는 레시피가 훨씬 많다(draft 포함 100개 기준 직접 28 대 포함 가능만 269). 결과는 "다음 단계 제안" 11번.
- **스크립트**: 골든셋 재검토 자료 생성 도구를 `scripts/make_golden_review.py`로 옮김(`.scratch`에서 이동, 경로 기준과 머리말만 수정). 다시 만든 `docs/review/golden_review.md`는 본문이 같고 머리말 한 줄만 바뀜(작업 시점 커밋 번호 → 생성 명령).

### data-4 draft 상태로 정리, PR (2026-10-04)

- **결정(사람, 2026-10-04)**: 신규 레시피 50개는 `status: draft` 유지(기본 설정에서 추천에 쓰이지 않음). 레시피 검수와 골든셋 기대 레시피 재선정은 **보류**한다. 브랜치는 draft 상태 그대로 PR로 올린다.
- **보류를 풀 때 할 일(순서대로)**:
  1. 검수표 확인: `docs/review/recipes_review.md` "검수 대기(draft)"(confidence low 9개 먼저), 재료 `soft_tofu`는 `docs/review/ingredients_review.md`.
  2. expected_top3 재선정: `docs/review/golden_review.md`를 보고 사람이 고른다. 희망 시간·조리도구 입력은 빼고 판단한다(한끼살림 화면에서 받지 않을 예정, GitHub 이슈 alexisnoh37-cell/ontol_recipe_claude#1). 페르소나의 희망 시간(beginner 20분 등)·조리도구(western_lover 오븐 등) 처리도 함께 정한다.
  3. published 전환: 승인한 레시피를 published로 바꾸고 `tests/kb/test_recipe_seed.py`의 `PUBLISHED_IDS`에 추가. soft_tofu 승인 시 reviewed로 바꾸고 `tests/kb/test_real_knowledge.py`의 `DRAFT_INGREDIENTS`에서 뺀다.
  4. baseline 저장: `uv run python scripts/eval_golden.py --save-baseline "설명"`(사람 승인 후).
- **관련 이슈**: 조리도구·조리시간 미입력 시 처리 방식(보류) — alexisnoh37-cell/ontol_recipe_claude#1.

## 식품안전나라 가져오기 트랙 (브랜치 `feature/foodsafety-import`)

### fs-1 내려받기·변환 도구 (2026-10-16)

- **결정(사람, 2026-10-16)**: D3 보완 2. 이용 조건 확인 결과 API 안내에 공공누리 유형이 없고, 식약처 저작권정책은 공공누리 미부착 자료에 담당 부서 사전 협의와 출처 명시를 요구한다. 이를 확인한 상태에서 개인용 범위로 출처를 표시해 쓰기로 함. 별도 폴더, draft에 한해 cook_time_min 선택, cuisine `미분류`, role 모두 `sub`. plan.md 5-3, 5-3-1(신설), 5-4, 디렉터리 구조 수정.
- **추가한 것**
  - `scripts/fetch_foodsafety.py`: `.env`의 `FOODSAFETY_API_KEY`로 COOKRCP01을 1000건씩 받아 `data/external/foodsafety/raw/COOKRCP01.json`에 저장. 인증키는 출력·파일에 남기지 않음.
  - `kb/foodsafety.py` + `scripts/convert_foodsafety.py`: 원본 → `data/recipes_foodsafety/fs_<일련번호>.yaml`, 검수표 `docs/review/foodsafety_unmatched.md`(미매칭 빈도, 미매칭 1~2개 레시피, 이름 중복, 건너뛴 레시피).
  - 재료 매핑은 별칭 색인 **정확 일치만**(양 표기 앞 이름 → 원문 전체 순). concept 노드는 미매칭. 버리는 줄은 레시피 이름 줄과 고정 머리말 단어(`HEADER_WORDS`)뿐이다. 그 밖의 짧은 줄은 모두 재료로 남긴다(잘못 버리면 알레르기 판정에서 빠짐).
  - 검증 규칙(`kb/datacheck.py`): draft는 cuisine `미분류`(`UNCLASSIFIED_CUISINE`, vocab에는 없음), cook_time_min 없음 허용. published는 cook_time_min 필수.
  - 적재 차단(`kb/recipes.load_recipe_specs`): cuisine 미분류이거나 cook_time_min이 없으면 `not_loadable`로 거부. DB 컬럼은 NOT NULL 유지.
  - `.gitignore`: `data/external/`, `data/recipes_foodsafety/`(재배포 방지).
- **테스트**: DB 통합(tests/storage) 제외 408개 통과(allergy·logic·kb·golden 337, api 12, viz 59). tests/storage는 Docker Desktop이 꺼져 있어 DB 연결 대기로 실행하지 못함. 추가: `tests/kb/test_foodsafety.py` 14개(직접 만든 예시 행), `tests/kb/test_datacheck.py` 2개, `tests/kb/test_recipe_seed.py` 2개 추가. tests/allergy 무수정.
- **실행 순서(인증키 입력 후)**:
  1. `.env`에 `FOODSAFETY_API_KEY=<발급받은 키>`
  2. `uv run python scripts/fetch_foodsafety.py`
  3. `uv run python scripts/convert_foodsafety.py`
  4. `docs/review/foodsafety_unmatched.md` 확인 → 별칭·재료 보강(knowledge에 draft) → 3번 다시 실행
- **남은 일**: 실제 데이터 미수신. 미매칭률은 받은 뒤 측정. `data/recipes/`로 옮기는 기준(미매칭 0, cuisine·조리시간·role·맛·난이도 채움, 사람 검수)은 plan 5-3-1 4번.

### fs-2 실제 데이터 내려받기·변환 (2026-10-16)

- 인증키 입력 후 실행. 원본 1156건(`data/external/foodsafety/raw/COOKRCP01.json`, 인증키 미포함 확인), 변환 1153개(재료정보 없음 3개: fs_691, fs_692, fs_831). 사용자가 처음 준 목록(검색 가능 1153, 제외 3)과 같다.
- **변환 규칙 보완**(실제 원문 확인 후): HTML 태그(`<br>` 등), `[ 2인분 ]`·`[추가 재료]` 대괄호 머리말, 줄 중간 `[소스소개]`, ` - 양념장 : …`, `크림치즈 > 우유` 구분, "소제목 : 재료" 형태(소제목은 따로 미매칭 항목으로 남김), 물 제외. plan 5-3-1 갱신. 테스트 4개 추가(`tests/kb/test_foodsafety.py` 18개). DB 통합(tests/storage, Docker 꺼짐) 제외 412개 통과.
- 버려지는 줄 전수 확인: 머리말 15종(주재료, 2인분 기준, 양념, 고명, 레시피 이름 5개, "…재료" 3개 등)뿐, 재료 손실 없음. 변환 YAML에 `<`, `>`, `[`, `]`, `●`가 남은 재료 줄 0개.
- **결과**: 재료 줄 13048개 중 미매칭 3769개(28.9%), 미매칭 없는 레시피 82개(나머지 1071개는 알레르기 사용자에게 제외 대상), 서로 다른 미매칭 표기 1492개. 상위: 저염간장 110, 전분 44, 흰 후추 42, 파 41, 유자청 37, 다진 양파 36, 마늘다진것 36, 맛간장 32, 매실액 30, 녹말가루 29.
- 같은 이름 레시피 7쌍(가지볶음, 깻잎장아찌롤, 둥지튀김, 버섯 리조또, 봄주먹밥, 비타 오이 물김치, 양배추롤) — 검수 때 중복 여부 판단.
- 검수표: `docs/review/foodsafety_unmatched.md`(커밋, 재료 표기 빈도만 담음). 원본·변환 YAML은 gitignore.

### fs-3 미매칭 보강안 (2026-10-16, 검수 대기)

- `docs/review/foodsafety_alias_proposal.md`: 미매칭 표기 중 5회 이상 나온 154개를 분류. **knowledge는 아직 바꾸지 않음**(제안만).
  - A 확실한 별칭 60개(예: 저염간장 → 간장, 흑임자 → 참깨, 달걀흰자 → 계란, 브로컬리 → 브로콜리).
  - B 새 재료 71개(draft, 알레르기 표시 포함). 알레르기가 걸리는 항목은 possible로 넓게 잡고 `confidence: low`: 맛간장(가쓰오부시 가능), 어간장, 발사믹식초(아황산 가능), 미숫가루(대두·참깨·밀 가능), 백김치(젓갈·굴 가능), 젤라틴(돼지·소 가능), 견과류(견과 그룹 모두 가능), 새싹채소·어린잎채소(메밀싹 가능), 베이킹파우더(밀 가능), 은행(기타 견과 가능).
  - C 보류 12개: 파·다진 파(대파/쪽파), 깨(참깨/들깨 → 참깨 알레르기 판정이 갈려 미매칭 유지), 육수·국물(원료 불명), 호박, 칠리소스, 홍피망 등.
  - D 변환 규칙 후보 4개: "재료 닭가슴살", "양념 다진 마늘", "육수 무"처럼 머리말 단어가 공백으로 붙은 경우 떼기, "장식"을 머리말에 추가.
- 효과(시뮬레이션): 재료 줄 미매칭 28.9% → A 23.1% → A+B 15.5%. 미매칭 없는 레시피 82 → 127 → 272개(1153개 중).
- 별칭·이름 충돌, 없는 id·그룹·분류 자동 검사 통과(분석 스크립트 `.scratch/fs/proposal.py`, 커밋 안 함).

### fs-5 식품안전나라 원본·변환 결과 커밋 (2026-10-16)

- 사람 결정 D3 보완 3: 공개 저장소임을 확인한 상태에서 원본 JSON(`data/external/foodsafety/raw/COOKRCP01.json`, 1156건)과 변환 YAML 1153개(`data/recipes_foodsafety/`)를 커밋. `.gitignore`에서 두 폴더를 빼고 정적 뷰어 산출물(`viewer.html`)만 제외.
- 이 브랜치의 변환기로 다시 변환한 결과가 로컬 기존 파일과 동일(1153개, 미매칭 3769/13048줄 28.9%, 검수표 변화 없음). 원본·변환 결과에 API 인증키 없음 확인.
- 적재 대상이 아닌 것(5-3-1 4번)과 knowledge 무변경은 그대로다. push는 하지 않음(push하면 공개됨).

## 외부 레시피 분석 트랙 (브랜치 `feature/adhoc-recipe-analysis`)

### adhoc-1 일회성 분석 API와 그래프 겹쳐 보기 (2026-10-16)

- 사람이 정한 범위: 일회성 분석만(저장 안 함), 화면은 `/viz` 입력 카드, 사용자 판정은 선택 입력, 분기는 `feature/foodsafety-import`(재료 줄 파서 재사용). 설계는 docs/plan.md 부록 E(이번에 추가).
- `POST /analyze-recipe`(`api/adhoc.py`): 재료 줄 분리는 `kb.foodsafety.ingredient_segments`(식품안전나라 변환과 같은 규칙, 버린 항목은 `skipped`로 응답), 별칭 색인 정확 일치 매핑, concept에 맞은 줄은 미매칭과 같이 처리(A1). 줄별 is_a 조상·derived_from 원천·기본 그룹 알레르기 행(certainty·via·path_links)은 컴파일 결과 조회만. 사용자를 주면 임시 `Recipe`로 엔진 `UserConstraints.check`(추천 필터와 같은 기준) → possible·미매칭도 제외. 매운맛·조리기구·조리시간·음식 종류는 판정하지 않는다고 응답에 표시. 제외 시 `logs/exclusions.jsonl` 기록(recipe_id `adhoc_<해시>`).
- 표시 계층 재사용을 위해 `api/viz.py`의 레시피 알레르기 모음을 `lines_allergens`로 뺐고, `exclusion()`에 줄 색인 인자를 더했다(기존 동작 같음). `ingredient_segments`에 버린 항목을 모으는 선택 인자 `skipped` 추가(기존 동작 같음).
- `/viz`: "외부 레시피 분석" 카드(`viz/adhoc.js`), 결과 표(줄별 매핑·분류·알레르기 경로, 판정, 버린 항목), 그래프에 청록 임시 레시피 노드(레시피 층 위 가운데 고정)와 빨간 사면체 미매칭 줄 노드. 다시 분석·지우기 때 이전 임시 노드를 뺀다. `scene.setOverlay`는 warmup 없이 graphData를 다시 넣어 기존 배치가 움직이지 않음(브라우저에서 확인: 두부 노드 좌표 불변, 지우기 후 노드 330개로 복귀).
- 엔진(`engine/`)과 `tests/allergy/`는 바꾸지 않았다.
- 테스트: `tests/api/test_analyze_recipe.py` 19개, `tests/kb/test_foodsafety.py` 1개 추가, `tests/viz/test_page.py` 카드 요소 확인 추가. DB 없이 432개 통과(`--ignore=tests/storage`). `tests/storage/`는 로컬 DB(docker)가 꺼져 있어 이번에 실행하지 못함(연결 시간 초과).
- 브라우저 확인(ENGINE_SOURCE=files): 예시(마파두부, multi_allergy 페르소나) → 7줄 중 6줄 매핑, 굴소스 → 굴 → 조개 경로, 트러플 오일 미매칭으로 제외, 콘솔 오류 없음.

### fs-4 정적 HTML 레시피 뷰어 (2026-10-16)

- `scripts/make_foodsafety_viewer.py` + `scripts/foodsafety_viewer_template.html` → `data/recipes_foodsafety/viewer.html`(2.5MB, gitignore, 레시피 1153개 내장).
  - 카드 목록(대표 사진, 요리종류, 조리방법, 열량, 재료 매칭 막대), 검색(메뉴명·재료·해시태그·매칭된 재료 이름), 요리종류 칩, 조리방법·정렬(번호·이름·미매칭 적은 순·열량), "미매칭 없는 것만".
  - 상세 시트: 사진, 영양 정보(1인분), 재료별 매칭/미매칭 표시(매칭이면 정규 재료 이름), 미매칭이 있으면 "알레르기 판정 불가" 안내, 단계별 사진, 저감 조리 팁, 출처. 주소 `#fs_<번호>`로 바로 열림.
  - 사진은 식품안전나라 서버에서 직접 불러온다(인터넷 필요). 데이터는 textContent로만 넣고, 내장 JSON의 `</`를 이스케이프한다.
  - 알레르기 성분 표시는 넣지 않음(미매칭이 많아 "알레르기 없음"으로 오해될 수 있음).
- 확인: 브라우저 패널에서 목록·사진·검색("두부" 157개)·"미매칭 없는 것만"(82개)·상세 시트·딥 링크, 콘솔 오류 없음. 브라우저 패널이 file:// 를 열지 못해 `.claude/launch.json`에 `foodsafety-viewer`(로컬 정적 서버, 개인 설정이라 커밋 안 함)를 추가해 확인했다. 사용자는 파일을 더블클릭해 열면 된다.
- 테스트 1개 추가(`tests/kb/test_foodsafety.py` 20개).

## 재료 ↔ 레시피 조회 트랙 (브랜치 `feature/ingredient-recipe-browse`)

### ui-1 재료로 레시피 찾기·레시피 전체 재료 보기 (2026-10-16)

사람 요청: "재료를 고르면 가능한 레시피, 레시피를 누르면 필요한 재료"를 화면에서 바로 보기. 판정·점수는 바꾸지 않는 표시 기능이다(plan.md 6장 "부가 트랙 ui").

- `GET /recipes/{id}?profile_id=&pantry=`(api/main.py, api/present.py `Catalog.recipe_detail`): 역할별 전체 재료와 조리 단계. 보유 기준을 주면 줄마다 `have`. 보유 판정은 엔진과 같은 `engine.candidates.owned_ingredients`(삼겹살 보유 → "돼지고기" 줄 충족, 기본 양념 보유로 간주). 대체재는 보지 않는다. 역할 표기는 `config/display.yaml`의 `role_labels`.
- Streamlit 추천 탭: "프로필 보유 재료 / 이번만 재료 직접 고르기" 선택. 직접 고른 재료는 `POST /recommend`의 `pantry`로 보내고 저장하지 않는다. 카드마다 "전체 재료·조리 순서 보기"(✅ 보유 · ⬜ 없음, 선택·기본 양념·미확인 재료 표시, 주재료 → 부재료 → 양념 → 고명 순).
- 기존 버그 수정: 재료 선택기(`ingredient_picker`)의 "추가" 버튼이 동작하지 않았다(프로필 탭 보유 재료도 같음). Streamlit 1.64에서 키가 있는 multiselect는 default가 바뀌어도 이전 값을 유지하기 때문. "추가" 때 위젯 값(session_state)을 직접 바꾸도록 고쳤다.
- 테스트: `tests/api/test_api.py`에 4개(전체 줄·역할 표기, 보유 판정 is_a·기본 양념·pantry 우선, 404/400, 성분표 확인 표시는 알레르기 프로필만).
- 화면 확인: DB(docker)가 꺼져 있어 파일 지식 + 메모리 프로필 저장소로 임시 API를 띄워 확인(삼겹살·배추김치 선택 → 김치찌개 추천, 펼치면 돼지고기 ✅). 실제 DB 구성으로는 확인하지 않았다.

### ui-2 재료로 레시피 찾기 (2026-10-16)

ui-1은 고른 재료를 추천 엔진에 넣는 방식이라 사람의 의도(재료 여러 개 → 그 조합으로 만들 수 있는 레시피 조회)와 달랐다. 별도 조회 기능으로 만들었다. 사람이 정한 것(2026-10-16): 화면은 `/viz`와 Streamlit 둘 다, 1~2개 모자란 레시피도 "거의 가능"으로 표시, 대체재는 쓰지 않음, **알레르기는 제외하지 않고 주의 표시**, ui-1 커밋은 그대로 둠.

- 엔진 `engine/browse.py` + `Recommender.browse`: 보유 = 고른 재료 + 기본 양념 + is_a 조상(삼겹살 → 돼지고기). 꼭 필요한 재료 = 선택이 아닌 main·sub·seasoning(미매칭 줄은 부족). 부족 0 = 조리 가능, 1~2 = 거의 가능(`config/engine.yaml` `browse_max_missing`). 알레르기 경고는 추천 필터(`UserConstraints.check`)와 같은 판정 결과에서 알레르기·미매칭 사유만 가져온다. 경고가 있는 레시피는 각 묶음 안에서 뒤로.
- API `GET /browse`(api/main.py, api/present.py `Catalog.browse`): 이름·부족 줄·경고 문구·그래프 강조용 id.
- Streamlit "재료로 레시피 찾기" 탭: 재료 검색·추가, 프로필 알레르기로 주의 표시(체크), 조리 가능 / 조금 모자란 레시피 카드(⚠️ 알레르기 주의, 더 필요한 재료, 없어도 되는 재료, 전체 재료·조리 순서 펼치기).
- `/viz` "재료로 레시피 찾기" 카드(viz/browse.js): 검색 또는 "그래프에서 재료 노드를 클릭해 고르기", 알레르기 기준(페르소나·프로필), 결과 목록(클릭하면 해당 레시피로 카메라 이동)과 그래프 강조(고른 재료 초록, 조리 가능 연두, 거의 가능 노랑, 알레르기 주의 빨강, 모자란 재료 주황, 레시피-재료 간선).
- 테스트: `tests/logic/test_browse.py` 12개(조리 가능·거의 가능, is_a 방향, 고명·선택, 미매칭, 대체재 미사용, 경고 = 추천 제외 근거, 정렬, 모르는 그룹), `tests/api/test_api.py` 3개, `tests/viz/test_page.py` 1개.
- 화면 확인(임시 API: 파일 지식 + 메모리 프로필): Streamlit에서 삼겹살·배추김치 + 새우 알레르기 → 조리 가능 ⚠️김치찌개(새우: 배추김치 포함 가능), 거의 가능 제육볶음(양파·대파)·⚠️김치전(부침가루). `/viz`에서 삼겹살·배추김치·계란(그래프 클릭) + 알레르기 많은 아이 부모 → 조리 가능 3·거의 가능 5, 그래프 강조 확인. 실제 DB 구성으로는 확인하지 않았다.

## 데이터 트랙 sc-1: 자취요리신 데이터 연결 (2026-10-16)

기준: `data/simplecooking-recipes` 브랜치(origin/main + 원본 데이터셋 `data/simplecooking_recipe_dataset/`). `feature/recipe-expansion`의 1차 확장 50개와 soft_tofu는 포함하지 않는다(합칠 때 정리 필요).

사람이 정한 것(2026-10-16):

- **D3 예외**: 설명란 원문(raw_text·조리 단계)을 유지한 채 draft로만 넣는다. source는 영상 URL. published 전에 출처 이용 조건·표현 재검토(docs/decisions.md D3).
- **미매칭 처리**: 확실한 연결만 추가하고, 상표 제품·시판 소스·가공품은 성분을 추측하지 않고 `ingredient: null`.
- **draft만 미매칭 허용**: `kb/datacheck.py`가 draft 레시피의 null 재료를 오류로 보지 않는다. published는 계속 오류(docs/plan.md 5-4 수정). 엔진은 이미 알레르기 사용자에게 미매칭 레시피를 제외한다(tests/allergy 무수정 통과).

한 것:

- knowledge: 별칭 6개(노른자→egg, 통삼겹살→pork_belly, 절단용 닭→chicken, 파스타면→pasta, 꼬치어묵→fish_cake, 크래미→imitation_crab, 각 노드 note에 검수 필요 표시), 새 재료 2개 draft(`beef_plate` 우삼겹 is_a beef, `bomdong` 봄동 confidence low). '깨'는 참깨·들깨 모호(기존 검수 결정)라 연결하지 않음. 재료 254개.
- `scripts/convert_simplecooking.py`: 원본 YAML → `data/recipes/<id>.yaml` 변환, 차이는 `data/simplecooking_recipe_dataset/CONVERSION.md`(생성 파일). 완전 매핑 54개, 미매칭 포함 46개.
- 형식 때문에 바꾼 것: source(객체→URL), id 1개(`5bun_gimcijjim_pvrcuh`→`obun_gimcijjim_pvrcuh`, 숫자 시작 불가), cuisine '기타' 5개 임시 지정, vocab에 없는 선택 조리기구(토치·기타 조리도구) 제외. 모두 note와 CONVERSION.md에 기록.
- 테스트: `tests/kb/test_recipe_seed.py`·`tests/api/test_api.py`는 feature/recipe-expansion 선례(개수는 시드에서 셈, published 50개 고정)를 가져와 조정, 자취요리신 검사 3개 추가. `tests/kb/test_real_knowledge.py` DRAFT_INGREDIENTS, `tests/kb/test_datacheck.py` draft 미매칭 허용 검사 추가.
- 검수표 재생성: `docs/review/ingredients_review.md`, `docs/review/recipes_review.md`(150개).

사람 확인 필요:

- 새 재료 2개와 별칭 6개 검수(봄동을 is_a 배추로 둘지 포함).
- cuisine '기타' 5개의 임시 지정(버팔로 핫닭다리살→양식, 나머지 4개→한식). vocab에 '기타'를 넣을지.
- 미매칭 재료 목록(CONVERSION.md): 라면 제품·시판 소스 등을 knowledge에 넣을지는 제품 표시사항 확인 후.
- 같은 재료 id로 매핑된 줄 4건(CONVERSION.md) 합칠지.

알려진 문제:

- 주재료가 미매칭인 draft(예: 열무비빔냉면, 주재료가 냉면 제품)는 후보 생성 근거가 없어 누구에게도 추천되지 않는다(안전 문제는 아님).
- 새 100개는 기본 설정(published만 제공)에서는 추천에 나오지 않는다. 그래프(`/graph?recipes=all`)와 `serve_draft_recipes` 설정에서만 보인다.

## 부가 트랙 살림팝 레시피 뷰어 (2026-10-16)

- 브랜치 `feature/sallimpop-recipe-viewer`(기준 `main` ae7014b — 살림팝 데이터셋이 들어 있는 브랜치가 없어 자취요리신 데이터셋과 같은 방식으로 main에서 분기).
- `data/sallimpop_recipe_dataset/`: 살림팝 YouTube 레시피 169개(YAML, 전부 `status: draft`)와 index·ingredient_names·classification CSV, `validate.py`, README, REPORT. 전달받은 ZIP 내용을 그대로 복사했고 사실값·URL·ID·confidence·note·status는 바꾸지 않았다.
- `data/sallimpop_recipe_viewer/`: 정적 웹 뷰어(`dist/`)와 `build_viewer.py`(`../sallimpop_recipe_dataset/recipes/sallimpop/*.yaml` → `dist/recipes-data.js`). 경로 조정 없이 그대로 동작한다.
- 검증: `validate.py` 169개 통과, `build_viewer.py` 169개 생성(전달본과 바이트 동일), `node --check dist/app.js` 통과, 로컬 정적 서버에서 검색·분류·필터·정렬·더 보기·상세 창·체크리스트·모바일(375px) 확인.
- 엔진·지식·DB와 연결하지 않은 독립 자료다. 추천 엔진 시드로 쓰려면 재료 정규 ID 매핑과 사람 검수가 먼저 필요하다.

## 통합 트랙 int (브랜치 `feature/ontology-integration`)

### int-1 브랜치 통합 (2026-10-16)

- 사람 요청: 기존 브랜치는 손대지 않고 새 브랜치에서 레시피·재료·알레르기를 하나의 온톨로지로 합친다. 추천안은 `docs/review/ontology_integration_proposal.md`(PR #3, 승인 대기).
- `main`(ae7014b)에서 분기해 차례로 병합(`--no-ff`): `feature/foodsafety-import`(fs-5 포함) → `feature/adhoc-recipe-analysis` → `feature/ingredient-recipe-browse` → `data/simplecooking-ontology` → `feature/sallimpop-recipe-viewer`. 원래 브랜치는 바꾸지 않았다.
- 충돌 해결
  - `knowledge/`: 충돌 없음(자동 병합). 재료 255개(draft 3: soft_tofu, beef_plate, bomdong), 별칭 393개.
  - progress·decisions: 양쪽 기록을 모두 유지(D3 보완·보완 2·보완 3·자취요리신 예외).
  - `viz/app.js`: adhoc·browse import를 둘 다 유지.
  - `tests/kb/test_real_knowledge.py`: `DRAFT_INGREDIENTS`를 세 재료로, soft_tofu·자취요리신 연결 테스트 둘 다 유지.
  - `tests/kb/test_recipe_seed.py`: published 50 + 1차 확장 draft 50 + 자취요리신 draft 100 = 200 기준. 영상 출처 외 source는 모두 agent_draft. 김치 레시피 새우 제외 검사는 주재료가 매핑된 후보만(자취요리신 쪽 규칙).
  - `tests/api/test_api.py`: ui-1·ui-2 테스트 유지, /health는 시드 파일 수와 비교(자취요리신 쪽 변경).
  - 검수표 `ingredients_review.md`·`recipes_review.md`는 다시 생성(레시피 200개).
- 의미 충돌 1건: 자취요리신 갈래에서 승인된 "draft 미매칭 허용"(plan 5-4)으로 식품안전나라 변환 결과의 검증 결과가 `unmapped` 오류 → 오류 없음으로 바뀜. `tests/kb/test_foodsafety.py` 기대값과 `scripts/convert_foodsafety.py` 설명을 새 규칙에 맞춤(published는 계속 unmapped 오류). 엔진의 미매칭 알레르기 제외는 그대로다.
- 검증: `validate_data` 통과(재료 255, 레시피 200, 오류 0, 경고 3). 전체 458 통과 + DB 통합 9 건너뜀(TEST_DATABASE_URL 없음), `tests/allergy` 118 통과·무변경. 살림팝 `validate.py` 169 통과, `build_viewer.py` 결과 동일.
- 화면 확인(ENGINE_SOURCE=files, 내장 브라우저): `/graph?recipes=all` 재료 255 · 알레르기 그룹 27 · 레시피 200(published 50). `/viz`에 외부 레시피 분석·재료로 찾기 카드 모두 표시, 그래프 노드 482. 외부 분석 예시에서 우삼겹·봄동(자취요리신 갈래)이 매핑되고 코인육수는 미매칭으로 밀 알레르기 기준 제외. 로컬 DB가 꺼져 있어 `/profiles`는 응답 없음(병합과 무관).
- 알려진 문제
  - `data/recipes_foodsafety/`는 fs-5 시점 지식으로 변환된 결과다. 병합된 지식(별칭 +7, 재료 +2)으로 다시 변환하지 않았다(다음 단계 연결 작업에서 함께).
  - 살림팝 169개는 아직 원본만 있고 시드로 변환하지 않았다. 식품안전나라는 그래프에 아직 나오지 않는다(추천안 승인 후).

### int-2 1,522개 레시피를 그래프에 연결 (2026-10-16)

- 사람 승인: 추천안(PR #3) 1단계만 먼저(살림팝 시드 변환, 식품안전나라 그래프 표시 전용). 미매칭 보강(별칭·새 재료)은 아직 하지 않음. decisions D3 "통합", plan 5-3-1 5번·부록 D-8 추가.
- 살림팝 169개 → `data/recipes/`(draft): `scripts/convert_sallimpop.py`. 자취요리신 변환 로직을 `kb/youtube_seed.py`로 옮겨 두 스크립트가 함께 쓴다(자취요리신 출력은 리팩터 전과 같음). cuisine '기타' 2개(불닭계란두부탕·로제떡볶이)를 한식으로 임시 지정, 선택 조리기구 '기타 조리도구' 16건 제외(`data/sallimpop_recipe_dataset/CONVERSION.md`). 원본 YAML 무변경.
- 자취요리신 다시 변환: 병합된 지식에서 '순두부'가 `soft_tofu`(is_a 두부, 대두 definite)로 연결되어 4개 레시피의 순두부 줄이 `tofu` → `soft_tofu`(알레르기 결과 같음).
- 식품안전나라 다시 변환(병합된 지식): 미매칭 3769 → 3764줄(28.8%), 미매칭 없는 레시피 82개 그대로.
- 그래프: `GET /graph?display=true`로 식품안전나라 1153개(엔진 미적재)를 같은 지식으로 연결. 레시피 노드 `origin`·`engine`·`lines`·`unmapped_lines`. YAML 읽기는 libyaml C 파서(1153개 7.9초 → 1.4초, 시드 369개 결과 동일 확인), 표시 전용은 처음 요청 때만 읽음.
- 화면: 출처별 색(시드·자취요리신·살림팝·식품안전나라), 상단 "출처" 토글, "표시 전용 포함". 정보 패널에 출처·추천 사용 여부·미매칭 줄 원문.
- 결과(`/graph?recipes=all&display=true`): 노드 1804(재료 255, 알레르기 그룹 27, 레시피 1522) · 간선 12564 · 응답 3.8MB.

| 출처 | 레시피 | 미매칭 없음 | 재료 줄 | 미매칭 줄 | 엔진 |
| --- | --- | --- | --- | --- | --- |
| 기본·확장 시드 | 100 | 100 | 835 | 0 (0%) | 적재(published 50, draft 50) |
| 자취요리신 | 100 | 54 | 891 | 67 (7.5%) | 적재(draft) |
| 살림팝 | 169 | 21 | 1612 | 310 (19.2%) | 적재(draft) |
| 식품안전나라 | 1153 | 82 | 13048 | 3764 (28.8%) | 미적재(그래프 표시 전용) |

- 테스트: 462 통과 + DB 통합 9 건너뜀. `tests/allergy` 무변경. 추가·수정: `tests/viz/test_graph.py` 2개(출처가 모든 시드에 맞음, 표시 전용이 그래프에만 실리고 엔진에는 없음·ETag 다름), `tests/kb/test_recipe_seed.py`(영상 출처 검사를 데이터셋별 원본 URL 대조로, 살림팝 169개 추가, 시드 구성 369개).
- 화면 확인(내장 브라우저, ENGINE_SOURCE=files): `/viz?display=1`에서 레시피 1522개 출처별 색, 식품안전나라 토글 끄면 369개·켜면 1522개, 식품안전나라 레시피 정보 패널(출처, 추천 안 씀, 걸리는 알레르기 잣·참깨·호두, 미매칭 1/7줄 "시럽"), 콘솔 오류 없음(루트 `/` 404만). 기본 `/viz`는 이전과 같이 published 50개. 첫 로딩 HUD 11.6초(서버가 표시 전용 1153개를 처음 읽는 시간 포함), 이후 `/graph` 응답 94ms(캐시). 브라우저 창이 숨겨진 상태라 화면 첫 프레임 시간은 재지 못함.
- 알려진 문제
  - 미매칭이 많다(살림팝 148개, 식품안전나라 1071개 레시피에 미매칭 줄). 알레르기 사용자에게는 제외된다. 다음 단계(미매칭 보강)에서 줄인다.
  - 1522개 전체 화면 로딩은 viz-5 기준(1천 개 3~5초)보다 무거울 수 있다. 측정은 창을 띄운 상태에서 다시 한다.
  - 살림팝 cuisine 임시 지정 2건, 자취요리신 5건은 검수 필요.

### int-3 나무 배치 (2026-10-16)

- 사람 요청: 레시피 1522개가 평면 한 장에 겹쳐 보기 어려움 → 아래 층이 줄기, 레시피가 잔가지·잎인 나무 모양. 사람이 정한 것: 알레르기는 뿌리, 잎 배치는 주재료 방향과 음식 종류 둘 다 볼 수 있게, 잔가지(레시피-재료 간선)는 선택에 따라 전부 보이거나 숨김(기존 체크박스·선택 강조로 충족). plan.md 부록 D-1 주석·D-9 추가, README 6-1.
- `viz/tree.js`(새 파일): 뿌리·줄기·가지·잎(반구) 좌표를 결정적으로 계산(force 없음). 잎은 반구 표면 해바라기 배치 점을 방위각 순으로 배정해 같은 재료(또는 음식 종류) 레시피가 한 부채꼴에 모인다. 잎 무리 이름(재료·레시피 수)을 이웃끼리 높이 3단계로 엇갈려 표시, 줄기 원기둥·수관 반구 윤곽을 아주 흐리게.
- `viz/scene.js`: 배치 3가지(나무: 주재료 방향(기본) · 나무: 음식 종류 · 평면). 전환은 좌표만 바꿈(graphData 재설정 없음). 평면은 처음 고를 때만 force warmup, warmup이 비동기라 평면에서 나갈 때 좌표를 저장(처음 구현은 warmup 전 좌표를 저장하는 버그 → 브라우저 확인에서 발견·수정). 외부 레시피 노드는 나무에서 수관 위. 장식 라벨 점검용 `decorLabels`.
- `viz/app.js`·`index.html`: 상단 "배치" 선택(`?layout=`, 바꾸면 주소에 남김).
- 화면 확인(내장 브라우저, `/viz?display=1`, 1522개): 뿌리 → 줄기 → 가지 → 반구 수관 모양, 잎 무리 이름(양파 65, 두부 65, 쌀 55, 닭고기 48 …). 음식 종류 배치에서 양식·일식·중식 방위 집중도 1.0, 한식 0.95(미분류 1153개가 수관 약 3/4). 평면 전환 후 레시피 반경 4~441로 퍼짐, 나무 ↔ 평면 왕복 시 같은 좌표. 외부 레시피 노드 y=990(수관 꼭대기 840 위), 지우면 사라짐. 김치찌개 선택 시 정보 패널 정상. 콘솔 JS 오류 없음(`/profiles` 500은 로컬 DB 꺼짐, 무관).
- 로딩: 나무 배치 HUD 1.1초(warmup 없음), 같은 조건 재측정 8.5초도 나옴(브라우저 창이 백그라운드라 렌더링이 1fps로 묶여 시간·fps가 부정확). 창을 띄운 상태 측정은 사람 확인 필요.
- 테스트: 463 통과 + DB 통합 9 건너뜀(`tests/viz/test_page.py`에 배치 선택·tree.js 제공 확인 1개). `tests/allergy` 무변경.
- 알려진 문제: 잎 무리 이름 일부가 가까우면 조금 겹친다. 식품안전나라 미분류가 음식 종류 배치의 대부분을 차지한다(요리 종류 정보가 없음).

### int-4 main 병합 준비 (2026-10-17)

- 사람 요청: 지금 상태로 롤백할 수 있게 해 두고, DB 테스트·성능 검증 후 PR로 올려 통합 브랜치 작업을 닫는다. 손 인식 게임(poc-1)과 그래프 배치 실험 7종(`feature/viz-layout-lab`)은 통합하지 않고 각자 브랜치에 그대로 둔다. 통합 추천안 PR #3도 그대로 둔다.
- 롤백 지점: int-3 커밋(`b1b662e`)에 태그 `checkpoint/before-int-4`. 원래 폴더(`feature/adhoc-recipe-analysis`)에 커밋 안 된 채 있던 poc-1 기록·`poc/hand_grab/`·검토 문서 2개(`docs/review/ingredient_layers.md`, `ontology_enhancement.md`)는 그 브랜치에 커밋해 보존(`ae230e5`). `video/`, `.scratch/`, `.claude/`는 개인 작업 파일이라 커밋하지 않음.
- DB 반영(로컬 Docker PostgreSQL 16, 개발 DB): `alembic upgrade head`(0002, 변경 없음) → `compile_knowledge.py`(재료 255, concept 3, 별칭 648, allergen_closure 369행, 경고 3건 그대로) → `load_recipes.py`(369개: draft 319, published 50) → `validate_data.py --db` 통과.
- **DB 통합 테스트에서 발견한 결함**: `tests/storage/test_engine_source.py::test_db_source_equals_file_source` 실패. 원인: 자취요리신·살림팝 원본의 분량이 분수(1/3, 2/3)라 시드에 `0.3333333333333333`처럼 그대로 들어갔고, DB 컬럼은 `numeric(8,2)`라 0.33으로 저장되어 DB 스냅샷 ≠ 파일 스냅샷(40개 레시피, 분량 50줄). 지금까지 Docker가 꺼져 있어 이 테스트가 계속 건너뛰어져 드러나지 않았다. 엔진 입력(`recipe_from_spec`)과 추천 결과는 같아 판정·점수 영향은 없다.
  - 수정: `kb/youtube_seed.py`가 분량을 소수 둘째 자리로 반올림(DB와 같은 정밀도). 두 데이터셋 다시 변환 → 40개 파일의 `amount` 줄만 바뀜, `CONVERSION.md` 무변경.
  - 테스트 추가: `tests/kb/test_recipe_seed.py::test_amounts_fit_db_precision`(모든 시드 분량이 소수 둘째 자리 이내, DB 없이도 검사). 수정 전 실패 확인.
- 테스트: **DB 통합 포함 전체 473개 통과**(건너뜀 0). `tests/allergy` 118개 통과, main 대비 무변경.
- API(DB 모드, `ENGINE_SOURCE` 미지정): `/health` source db·재료 255·레시피 369, `/profiles` 200(이전 기록의 500은 DB가 꺼져 있었기 때문), `POST /recommend {profile_id: 1}` 200(점수 내역·부족 재료 포함). `/viz?display=1`에서 DB 프로필 목록과 출처 토글(1153·169·100·100) 표시, `/graph?recipes=all&display=true` 3.4MB·58ms(캐시 후).
- 성능(`scripts/bench.py`, 합성 1만 개, 요청 300회, seed 42): **p50 21.4ms · p95 79.8ms · 최대 114.5ms**, 기준 200ms 통과. `--trace` 3회: recommend p95 37~45ms, trace() p95 38~43ms, trace() + 표시 변환 p95 214~229ms(viz-5 기록 87.2ms보다 큼). 같은 측정을 통합 전 코드(원래 폴더, `feature/adhoc-recipe-analysis`)에서 해도 p95 235ms라 통합에 따른 회귀가 아니라 측정 환경 차이로 본다. 표시 변환은 시각화 경로라 엔진 기준 대상이 아니다.
- 화면 로딩 시간: 이 세션이 앱 창에 열려 있지 않아 브라우저가 백그라운드로만 돌았고 HUD(로딩 시간)가 그려지지 않아 재지 못함 → "사람 확인 필요".

## 미매칭 보강 트랙 um (브랜치 `feature/unmapped-resolution`)

### um-1 세 출처 미매칭 검수표 (2026-10-17, 검수 대기)

- 사람 요청: PR #4 병합 후 레시피 활용(B 단계)의 첫 단계로 미매칭부터. 식품안전나라까지 세 출처를 합쳐 검수표를 만들고 **엔진 레시피 영향 순**으로 정렬.
- 분석 결과: 추천 엔진에 들어가는 자취요리신·살림팝 269개 중 미매칭 있는 레시피 194개(377줄, 서로 다른 표기 226개). fs-3 보강안(식품안전나라 5회 이상 154개)은 이 중 32줄(8.5%)만 다뤄 따로 분류가 필요했다. 엔진 쪽 미매칭은 성격이 달랐다: 자막에서 이름을 뽑다 생긴 문구("맛을 위해 참기름", "고추장 크게", 오기 "진강장"), 시판 제품(코인육수 36줄, 라면 제품, 다시다), 새 재료(알룰로스, 매실청 등).
- 분류(5가지, 제안 데이터 `docs/review/unmapped_proposal.yaml`, 232항목)
  - A 별칭 64 · B 새 재료 84 · C 보류 13 · D 이름 다듬기 55 · E 시판 제품 16. 식품안전나라 fs-3 항목은 그대로 옮겨 합침(공백만 다른 표기 묶음).
  - **D 이름 다듬기**(새 분류): 원본 이름의 자막 문구·크기·오타를 변환 단계에서 고친다(knowledge에 문구를 별칭으로 넣지 않음). 반영 방법(변환기 이름 보정표)은 승인 후 정한다. 물은 재료에서 뺌(식품안전나라와 같은 규칙).
  - **E 시판 제품**(새 분류): 제품마다 성분이 달라 알레르기를 넓게 possible로 잡은 새 재료(예: 시판 육수 = 해산물 전체·육류·대두·밀·우유 가능, 라면 제품 하나로 묶음). 빠진 성분이 있으면 위험하므로 포장 표시를 확인할 수 없으면 X(미매칭 유지)를 권한다고 검수표에 적음. 상표명이 기존 검수 완료 재료와 같은 것은 별칭(스팸 → 통조림햄, 소고기 다시다 → 쇠고기 맛 조미료).
  - 새 재료의 알레르기는 모두 추정이며 possible 관계가 있으면 confidence low(견과류 혼합 제외, fs-3 판단 유지).
- 효과(모두 승인 가정 시뮬레이션): 엔진 미매칭 없는 레시피 75 → A 88 → A+B 111 → A+B+D 150 → A+B+D+E 252 / 269(남는 17줄은 C 보류). 식품안전나라 82 → 283 / 1153(5회 미만 표기 1317개는 표에 없음).
- 도구: `kb/unmapped_review.py` + `scripts/make_unmapped_review.py`. 제안을 지식 원본에 **메모리 안에서만** 얹어 컴파일해 별칭 충돌·없는 id를 검사하고 새 재료의 알레르기(상속 포함)를 계산한다. 다시 만들어도 승인 열은 유지된다. `docs/review/foodsafety_alias_proposal.md`에는 새 검수표로 옮겼다는 안내만 추가.
- 테스트: `tests/kb/test_unmapped_review.py` 9개(제안 컴파일·draft, 제안 표기가 아직 미매칭인지, 엔진 미매칭 전부 분류, possible 새 재료 low, 표기 중복 거부, D가 가리키는 새 재료 의존, 시뮬레이션, 검수표 최신, 식품안전나라 집계 = 변환 보고서). 전체 473 통과 + DB 통합 9 건너뜀(이번 작업은 DB 무관). `tests/allergy` 무변경.

### um-1 보완: 외부 검토 2건 종합, 검수 화면(HTML) (2026-10-17)

- 사람이 받은 외부 검토 2건(Gemini본, reviewed본)을 `docs/review/external/`에 보관. 둘 다 승인 열만 채웠고 다른 칸은 그대로였다(행 단위 대조).
- Claude 검토 요약: 두 검토가 같은 수정(전분·백김치 밀 가능, 젤라틴 생선 가능, 레몬주스 분리·아황산류, 발사믹·흰목이 분리, 분류 변경)은 수용. 원문 확인으로 결론: 기름 5개 모두 식용유(O), '파란부분 올리브유'는 대파+올리브유 분리(대파 줄 없음), '코스트코에서'는 소갈비 줄과 중복이라 뺌. E(시판 제품)는 Gemini의 '확인 권장 O'가 확인 없는 승인이고 Gemini 스스로 누락 성분(라면 땅콩 등)을 지적해, 확인 전 X(reviewed본) 쪽을 따름. 다만 알레르기별 계산상 E 효과(계란 +45, 참깨 +64 등)는 대부분 코인육수·다시다에서 나와 이 둘은 포장 표시 확인 후 결정(보류).
- 새로 확인한 점: D 줄 120개 중 50개는 같은 레시피에 같은 재료 줄이 이미 있는 중복, 70개는 그 줄에만 재료가 있다 → '재료에서 뺌'은 중복 줄에만. 검수표 효과 표의 'A+B+D+E 252개'는 E처럼 알레르기를 넓게 잡은 재료 때문에 실제 알레르기 사용자 기준으로는 과장 → um-2에서 알레르기별 표로 바꿀 것.
- 검수 화면 `docs/review/unmapped_review.html`(한 파일, 인터넷 불필요, 더블클릭으로 열림): 줄마다 O·X·보류 버튼과 메모 칸, 두 검토·Claude 의견 펼쳐 보기, 배경색(빨강 26 꼭 봐야 함 / 노랑 5 확인 후 결정 / 파랑 13 수정 내용 확인 / 흰색 189 넘어가도 됨), 색·분류·추천 영향·미확인·내가 바꾼 것 필터, 진행률, 브라우저 자동 저장, 결과 내보내기(`unmapped_decisions.json`)·불러오기. 미리 채운 판단은 `docs/review/unmapped_prefill.yaml`(두 검토가 갈린 줄은 모두 여기에 적어야 생성됨). 생성: `scripts/make_unmapped_review_html.py` + `scripts/unmapped_review_template.html`.
- 확인(내장 브라우저): 선택·메모·확인 표시 저장, 새로고침 후 유지, 되돌리기, 색 필터(빨강 26), 내보내기 JSON 233줄, 불러오기, 밝은·어두운 화면, 휴대폰 폭(가로 스크롤 없음), 콘솔 오류 없음.
- 테스트: `tests/kb/test_unmapped_review.py` 1개 추가(화면 최신, 미리 채움 값, E는 O로 미리 채우지 않음).

### um-2 사람 결정 반영 (2026-10-17)

- 사람 결정: 검수 화면에서 내보낸 `docs/review/unmapped_decisions.json`(233줄 모두 확인, 미리 채운 값에서 바꾼 줄 38개). 메모 해석이 알레르기 판정을 바꾸는 항목은 반영 전에 권장 해석 1~9와 D 보정표 방식을 다시 승인받음(첫 승인 요청 때 목록이 화면에 나가지 않아 다시 보여 주고 받음). 확정 내용은 검수표 승인 열과 `docs/review/unmapped_proposal.yaml`의 항목별 `decision`에 남김.
  - 시판 제품(E): 사람이 확인 권장 메모와 함께 대부분 O. 라면 제품은 '시판 라면 제품' 하나로(기존 '라면' 별칭 아님), 다시다는 새 재료 '조미료(다시다)'. Gemini가 지적한 누락 성분을 '가능'으로 추가(라면 땅콩, 냉면육수 돼지·조개, 불닭소스 계란·참깨, 순대 계란·우유·쇠고기·참깨, 포카칩 쇠고기·돼지·닭·계란·토마토, 쌍화탕 아황산류, 미숫가루 땅콩·호두·기타 견과·메밀·우유). X: 라면 스프·조미유, 갓장아찌, 분말가루.
  - 메모대로 새 재료: 생강즙·바질가루·청국장가루(별칭 대신), 맛간장(간장 별칭 아님), 호박(종류 불명). 분리: 배즙/시판 배 음료(아황산 가능), 발사믹식초/글레이즈, 레몬주스(아황산 가능), 목이/흰목이. 전분·백김치 밀 가능, 젤라틴 생선 가능, 어간장 생선 확정, 골뱅이 대두·밀 가능.
- **반영 중 바로잡은 것 2건(사람 승인 내용과 다름, 보고 필요)**
  - '양념은 불닭소스': 승인한 해석은 "같은 레시피의 '불닭소스 3스푼' 줄과 중복이니 뺌"이었으나, 원본은 '양념은 불닭소스 3스푼 / 불닭소스 3스푼'이 **한 줄 안의 표기**이고 불닭소스 줄은 따로 없었다(Claude가 앞서 원문을 잘못 읽음). 빼면 불닭소스 알레르기 성분이 판정에서 사라지므로, 변환기 중복 확인이 멈춘 것을 보고 **불닭소스로 연결**로 바꿈(처음 제안과 같음).
  - '코스트코에서': 승인한 해석은 "소갈비 줄과 중복이니 뺌"이었으나 이 줄이 원본의 주재료(main)이고 '소갈비 2.5kg'은 부재료(sub)라, 빼면 레시피에 주재료가 없어진다(테스트에서 발견). **소갈비로 연결**로 바꿈(같은 재료라 알레르기 판정 동일).
- knowledge: 기존 재료 별칭 91개 추가, 새 재료 106개(모두 `status: draft`, 성분 추정이 섞인 것은 `confidence: low`)를 분류별 파일 끝 "um-2" 구역에 추가. 재료 255 → 361, 별칭 648 → 941, allergen_closure 369 → 560행. 컴파일 경고는 기존 3건뿐.
- 원본 이름 보정표 `data/recipe_name_overrides.yaml`(54항목, 사람 승인 D): `kb/youtube_seed.py`가 매핑 전에 적용(`id` 매핑 / `drop` 물·중복 / `split` 한 줄 → 여러 재료). 중복 줄로 뺄 때 같은 재료 줄이 실제로 없으면 변환을 멈춘다. 바뀐 내용은 레시피 note와 `CONVERSION.md`. docs/plan.md 5-3-2 신설.
- 식품안전나라 변환 규칙(`kb/foodsafety.py`): '장식'을 머리말 단어에 추가, "재료 닭가슴살 100g"처럼 머리말이 공백으로 붙은 항목은 머리말을 뗌(뒤가 양 표기면 그대로). 외부 레시피 분석(`/analyze-recipe`)도 같은 줄 나누기를 쓴다. docs/plan.md 5-3-1.
- **시판 제품 안내**(사람 결정): `config/display.yaml` `commercial_product_notice` — 라면 제품·냉면육수·불닭소스·순대·포카칩·쌍화탕·미숫가루가 든 레시피는 알레르기 설정과 무관하게 "시판 제품으로 제품 성분을 확인해 알레르기 유무를 확인하시기 바랍니다."를 재료 목록 위에 보여 준다. API `GET /recipes/{id}`·추천 항목 `commercial_notice`, 그래프 레시피 노드 `commercial_notice`, Streamlit 레시피 상세(재료 위 경고), `/viz` 레시피 정보 패널(주재료 위 '시판 제품' 줄). 판정은 그대로(목록의 알레르기는 제외). 엔진 레시피 38개에 붙음. 코인육수·다시다 등 나머지 시판 제품은 이 목록에 넣지 않았다(사람이 정한 7개) — 알레르기 설정 사용자에게는 기존 '성분표 확인' 표시가 붙는다.
- 다시 변환: 자취요리신 완전 매핑 54 → 91/100, 살림팝 21 → 147/169, 식품안전나라 미매칭 줄 3764 → 1817(13042줄 중, '장식' 등 머리말로 6줄 줄어듦), 미매칭 없는 레시피 82 → 295/1153. 직접 작성한 시드 100개는 변경 없음.
- 효과(엔진 레시피 269개 중 미매칭이 없고 그 알레르기 성분이 없는 레시피 수, um-1 집계 → um-2): 새우 57 → 139, 계란 46 → 131, 우유 46 → 116, 쇠고기 62 → 131, 돼지고기 41 → 94, 닭고기 47 → 113, 조개류 38 → 102, 기타 생선 40 → 89, 참깨 51 → 150, 땅콩 74 → 214, 메밀 75 → 218, 토마토 67 → 192, 대두 3 → 8, 밀 3 → 6. 남은 엔진 미매칭 32줄(31개 레시피)은 모두 사람이 X·C로 정한 표기다(테스트로 확인).
- 검수표·검수 화면은 반영 전 기록으로 고정(`unmapped_review.md` 머리에 표시). 생성 도구(`scripts/make_unmapped_review*.py`, 템플릿)는 지금 지식으로는 다시 돌릴 수 없어 삭제, `kb/unmapped_review.py`는 결정 읽기·남은 미매칭 집계만 남김.
- 테스트: `tests/kb/test_unmapped_review.py`를 반영 검사로 교체(13개: 승인 표기 매핑·새 재료 draft, X·C 미매칭 유지, 보정표 = 승인 D, 엔진 잔여 미매칭은 X·C뿐, 시판 제품 목록·넓은 '가능' 성분, 보정표 매핑·분리·물 빼기, 중복 아닌 줄 빼기 거부, 모르는 재료 거부, 식품안전나라 머리말 떼기). `tests/kb/test_real_knowledge.py` draft 목록에 승인 새 재료 포함. `tests/api/test_api.py` 2개(안내는 알레르기 무관·재료 위, 설정 오타 거부). **DB 통합 포함 전체 488개 통과(건너뜀 0)**, `tests/allergy` 무변경. 골든셋 0.88 그대로(published만). bench p95 35.2ms. 개발 DB 재반영·`validate_data.py --db` 통과.
- 확인(내장 브라우저, ENGINE_SOURCE=files): `/viz?recipes=all`에서 바지락칼제비 정보 패널 주재료 위에 '시판 제품' 안내, 그래프 레시피 369개 중 38개에 안내. 콘솔 오류 없음(루트 `/` 404만).

### ir-1 draft 재료 검수 화면 (2026-10-17, 브랜치 `feature/ingredient-review`, 검수 대기)

- 사람 요청: um-2로 추가한 새 재료를 미매칭 보강 때처럼 검수 화면으로 검수. 대상은 status: draft 재료 전부 109개(um-2 새 재료 106 + 이전 검수 대기 soft_tofu·beef_plate·bomdong).
- 화면 `docs/review/ingredient_review.html`(한 파일, 인터넷 불필요): 재료마다 구분(시판 제품/새 재료/이전 draft), 분류·가공품·확신도, 별칭, is_a·derived_from, 상속 포함 알레르기(칩에 경로 툴팁, 펼치면 경로 목록), 시판 제품 안내 대상 표시, 쓰이는 추천 레시피·식품안전나라 레시피 수와 예시. 버튼 O(reviewed로) · X(재료 삭제 → 표기는 다시 미매칭) · 보류(draft 유지)와 메모, 색·구분·추천 사용·미확인·내가 바꾼 것 필터, 자동 저장, 결과 내보내기(`ingredient_decisions.json`)·불러오기. 정렬은 추천 레시피 사용 수 순.
- 미리 채운 판단 `docs/review/ingredient_prefill.yaml`: 시판 제품(um E)과 시판 제품 안내 대상은 보류·노랑 16개(포장 표시 확인 전 reviewed 아님, draft여도 엔진은 그대로 씀), 쟁점 있는 재료 빨강 12개(전분 밀 가능, 귀리 교차오염, 은행 견과 분류, 어린잎·새싹 메밀 가능, 골뱅이 분류, 미원, 호박(종류 불명), 참송이, 호박씨, 시판 배 음료·레몬주스 아황산 가능 — 모두 O로 채우고 Claude 의견 첨부), 확신 낮음·알레르기 있음 파랑 26개(O), 나머지 흰색 55개(O).
- 생성: `scripts/make_ingredient_review_html.py` + `scripts/ingredient_review_template.html`. knowledge·data는 바꾸지 않음.
- 확인(내장 브라우저): 선택·메모·확인 저장, 노랑 필터 16개, 내보내기 109개(형식 `ingredient-decisions/1`), 휴대폰 폭 가로 스크롤 없음, 콘솔 오류 없음.
- 테스트: `tests/kb/test_ingredient_review.py` 2개(모든 draft 포함·화면 최신, 시판 제품은 보류로 미리 채움).

### ir-2 재료 검수 결과 반영 (2026-10-17)

- 사람 결정: 검수 화면에서 내보낸 `docs/review/ingredient_decisions.json`(109개 모두 확인). O 102 · 보류 6 · X 1. 대화에서 추가 결정: 어린잎채소·새싹채소 모두 메밀(가능) 삭제, 나머지 메모는 적힌 그대로 전체 반영.
- knowledge: O 102개 status draft → reviewed(확신도 `confidence`는 그대로, note에 'ir-2 사람 재료 검수 완료'). 보류 6개(시판 고기 양념, 불닭소스, 참소스, 폰즈 소스, 감자칩, 순대)는 draft 유지(엔진은 그대로 씀). X 1개 식용 꽃 삭제 → 그 표기는 다시 미매칭(식품안전나라 전용, 미매칭 줄 1817 → 1826). 어린잎채소·새싹채소 메밀(가능) 삭제(알레르기 없음). 호박(종류 불명) 이름 → '호박'. 재료 361 → 360, draft 109 → 6.
- 시판 제품 안내 대상 확대(`config/display.yaml` `commercial_product_notice`): 메모 '시판 제품으로 포장 알레르기 표시를 확인한 뒤 사용 권장'을 단 재료 38개(um-2의 7개 포함, 보류 3개 포함). 콜라·탄산수·곤약·다시마육수처럼 알레르기 없는 재료도 메모대로 넣음. 안내가 붙는 엔진 레시피 38 → 113개(369개 중). 판정은 그대로.
- **해석해서 반영한 것(되돌리기 쉬움)**: 메모를 '재료 목록 위 안내 대상에 추가'로 읽음(재료 메모로만 남기는 해석도 가능했음). 확인 없이 O로 한 시판 제품도 reviewed로 바꾸되 `confidence: low`는 유지 → 알레르기 설정 사용자에게 '성분표 확인' 표시가 계속 붙는다. 레몬즙 별칭(생레몬)은 지시가 없어 그대로 둠.
- 기록: `docs/review/unmapped_proposal.yaml`의 식용 꽃 항목 decision → X(ir-2 삭제). 검수 화면 생성기는 reviewed가 된 재료의 미리 채운 판단을 기록으로 두고 화면에서는 뺀다(지금 화면에는 보류 6개만).
- 테스트: `tests/kb/test_ingredient_review.py`에 결정 반영 검사 1개(O → reviewed, 보류 → draft, X → 삭제, 메밀 삭제, 호박 이름). `tests/kb/test_real_knowledge.py` draft 목록을 보류 6개로, 삭제 재료 검사. `tests/kb/test_unmapped_review.py` 새 재료 status draft/reviewed 허용, 안내 대상 = um-2 7개 ∪ 메모 재료. `tests/api/test_api.py` 안내 테스트를 설정 목록 기준으로. **DB 포함 전체 491개 통과**, `tests/allergy` 무변경, 골든셋 0.88 그대로. 개발 DB 재반영·`validate_data.py --db` 통과.

### um-3 미매칭 2차 보강 (2026-10-17, 브랜치 `feature/unmapped-round2`)

- 사람 결정: 남은 미매칭은 지금까지의 검수 기준으로 Claude가 대부분 정리하고, "일괄 승인은 그대로 진행하고 꼭 확인해야 할 것만 검수". 대상은 1차(um-1·2) 결정 뒤 남은 식품안전나라 미매칭 표기 1,193개(엔진 레시피 미매칭은 모두 1차에서 결정됨).
- 분류 결과 `docs/review/unmapped_round2.yaml`(1차와 같은 형식): 별칭 A 196항목(표기 490개) · 새 재료 B 176 · 이름 보정 D 118 · 보류 C 207 → decision O로 반영. **꼭 확인 E 17개는 decision 없음(반영 안 함, 미매칭 유지)**.
  - 기준(1차 결정을 따름): 같은 재료의 표기·품종·손질 상태는 별칭(알레르기가 같을 때만). 생선은 기타 생선, 복족류(우렁이 등)는 조개류, 병 음료·과일 식초는 아황산류 가능. 종류를 모르는 재료는 넓게 '가능'(해물육수 → 해산물 전체, 떡 → 밀 가능, 생선살 → 생선 전체). 어느 재료인지 모르는 표기(파·고추·소스 소제목·요리 이름·육수류·코코아)는 보류.
  - 새 재료는 사람 일괄 승인이라 `status: reviewed`, 성분 추정이 섞인 것은 `confidence: low`(note에 'um-3 미매칭 2차 보강, 사람 일괄 승인').
- **변환기에서 찾아 고친 안전 문제**(`kb/foodsafety.py`): "황설탕(7g) 호떡소: 검정깨", "마늘다진것 2g 리코타치즈:우유 125g"처럼 양 뒤에 '소제목:'이 이어진 줄은 쌍점 뒤 재료가 앞 재료 줄에 묻혀 **이미 매핑된 레시피에서도 알레르기 성분이 빠지고 있었다**(27줄: 검정깨·우유·호두·아몬드가루·두부·간장·밀가루 등). 소제목부터 새 줄로 나누도록 고침. 다시 변환해 비교: 원래 매핑된 재료가 사라진 레시피 0개, 묻혀 있던 재료 41줄 회복. 번호 붙은 머리말("소스1 발사믹식초", "[소스1]")도 머리말로 처리. docs/plan.md 5-3-1.
- 식품안전나라 이름 보정표 `data/foodsafety_name_overrides.yaml`(236항목, D 승인분): 변환기가 별칭보다 먼저 적용(`id`·`drop`·`split`). `kb.youtube_seed.load_name_overrides`가 표 경로를 받도록, `drop` 사유에 `not_ingredient` 추가. `scripts/convert_foodsafety.py --overrides`.
- knowledge: 재료 360 → 536, 별칭 939 → 1735. 컴파일 경고는 기존 3건뿐.
- 다시 변환: 식품안전나라 미매칭 줄 1826 → 476(13102줄 중), 미매칭 없는 레시피 293 → 777/1153. 엔진 레시피(자취요리신·살림팝) 변환 결과는 변경 없음.
- 효과(전체 1,522개 중 미매칭이 없고 그 성분이 없는 레시피, 반영 전 → 후): 미매칭 없음 631 → 1115, 새우 484 → 886, 계란 413 → 750, 우유 393 → 679, 쇠고기 464 → 862, 돼지고기 418 → 820, 닭고기 431 → 836, 조개류 451 → 869, 기타 생선 399 → 752, 참깨 434 → 796, 땅콩 591 → 1052, 메밀 605 → 1082, 토마토 521 → 892, 대두 183 → 378, 밀 164 → 333.
- 꼭 확인 화면 `docs/review/unmapped_round2_review.html`(17개, 재료 검수 화면 템플릿 재사용, 내보내기 `unmapped_round2_decisions.json`, 형식 `unmapped-round2-decisions/1`). 생성 `scripts/make_unmapped_round2_html.py`(제안 재료를 넣은 지식 사본을 `build/um3_candidate/`에 만들어 알레르기 미리보기). 빨강 4개(분류 쟁점: 코코넛 → 기타 견과류 가능, 도토리묵 → 기타 견과류 가능, 멍게·미더덕 → 조개류 가능), 노랑 13개(시판 제품: 홍초·막걸리·스리라차·카스텔라·크림소스·초콜릿·바게트·버섯마늘소금·그라놀라·데미글라스·떡볶이 양념 분말·아이스크림·파인소프트). 모두 '제안대로 O'로 미리 채움.
- 테스트: `tests/kb/test_unmapped_round2.py` 9개(확인 대기는 E뿐, 승인 표기 매핑·새 재료 reviewed, 확인 대기·보류 미매칭 유지, 보정표 = 승인 D, 변환 결과의 남은 미매칭은 보류·제외·확인 대기뿐, 새 재료 알레르기, 쌍점 줄 나누기, 번호 머리말, 보정표 매핑·분리·빼기). `tests/kb/test_foodsafety.py` 끝단 테스트에 `--overrides` 지정.

### um-3 보완: 꼭 확인 17개 사람 결정 반영 (2026-10-18)

- 사람 결정: 검수 화면에서 내보낸 `docs/review/unmapped_round2_decisions.json`(17개 모두 확인, 모두 O). `docs/review/unmapped_round2.yaml`의 E 항목 decision → O.
- 메모 해석(이전 결정과 같은 방식): 코코넛·도토리묵의 '알레르기 제외' → 기타 견과류(가능)를 빼서 알레르기 없음(ir-2 '새싹채소 메밀 알레르기 제외'와 같은 뜻으로 읽음). '시판 제품으로 성분표 확인 후 사용 권장' 메모 14개(도토리묵 + 시판 제품 13개) → `config/display.yaml` 시판 제품 안내 대상에 추가(ir-2와 같은 해석, 38 → 52개). 멍게·미더덕은 제안대로 조개류(가능).
- knowledge: 17개를 `status: reviewed`로 추가(재료 536 → 553, 별칭 1735 → 1775). 식품안전나라 미매칭 줄 476 → 415.
- 효과(전체 1,522개, um-3 반영 전 → 지금): 미매칭 없음 631 → 1159, 기타 견과류 603 → 1075, 조개류 451 → 911, 우유 393 → 694, 대두 183 → 384, 밀 164 → 340.
- 검수 화면 `unmapped_round2_review.html`은 결정 전 기록으로 둔다(다시 만들면 대상이 0개).
- 테스트: `tests/kb/test_unmapped_round2.py` 확인 대기 검사를 결정 반영 검사로 교체(결정 = 제안서, 메모 반영), `tests/kb/test_unmapped_review.py` 시판 제품 안내 = um-2 7개 ∪ ir-2·um-3 메모 재료. **DB 포함 전체 509개 통과**, `tests/allergy` 무변경, 골든셋 0.88, `validate_data.py` 통과.

### um-4 미매칭 3차 정리 (2026-10-18, 브랜치 `feature/unmapped-round3`)

- 사람 요청: 남은 미매칭(363개 레시피)도 Claude가 먼저 정리하고 판단이 필요한 것만 골라 달라. 남은 447줄(식품안전나라 415 · 엔진 32)을 원문과 함께 분류해 추천안 1~6을 냈고, 사람이 "진행해"로 모두 승인. 결정 기록 `docs/review/unmapped_round3.yaml`.
- **1. 변환 규칙**(`kb/foodsafety.py`, docs/plan.md 5-3-1): 재료로 연결되지 않는 소제목 줄("구이소스 :", "[곁들임채소]", "●오이무침 :")과 같은 레시피에서 그 소제목을 가리키는 줄("겉절이 양념 15g")은 구성 재료가 따로 적혀 있으므로 뺀다(레시피 note에 뺀 줄 수). 소제목 이름이 재료로 연결되면("[팥소]", "리코타치즈:") 그대로 둔다 — 처음 시뮬레이션에서 이것까지 빼면 연결된 재료 39줄이 사라지는 것을 보고 좁혔다. 다시 변환 비교: 연결된 재료 손실 0. `ingredient_segments`의 항목 목록은 그대로(외부 레시피 분석 화면 호환), 소제목 이름은 `subtitles`로 따로 돌려준다.
- **2~3. 모호한 표기**(knowledge/README.md 별칭 규칙에 예외 추가): 후보의 알레르기가 같으면 '종류 불명' 재료 — 파(대파·쪽파), 고추(종류 불명), 홍피망 → 파프리카 별칭, 그린 샐러드 → 어린잎채소 별칭. 다르면 후보 알레르기를 모두 포함 가능 — 깨(참깨·들깨: 참깨 가능), 고기(쇠고기·돼지고기: '안심'·'등심얇게썬것'), 과일(종류 불명: 복숭아·토마토 가능). 지난 결정(파·고추·홍피망·깨 보류)을 바꾼 것.
- **4. 육수**: 육수(종류 불명) = 시판 육수와 같은 기준(해산물 전체·쇠·돼지·닭·대두·밀 가능), 채소 육수 = 대두·밀·우유 가능.
- **5. 시판 소스**: 칠리소스(스위트칠리 포함)·그린커리 페이스트·머스터드소스는 넓게 가능 + 시판 제품 안내(`config/display.yaml`, 52 → 55개). 키위소스·바질럽드·간편식 볶음소스·양념장·수제조미료·허브크러스트·삼색분말·호떡반죽·코코아는 미매칭 유지.
- **6. 오타·조각**(이름 보정표 um-4 구역): ghen → 호두(한/영 전환 없이 친 것), 현미휴 → 현미유, 고추자 → 고추장, 청 → 청고추('청,홍고추'), 재료 → 봄동, 두가지 묵 → 올방개묵 + 검정깨묵, 한 줄짜리 소제목 11개와 잘린 양('12g'·'8g')·앞말('미니')은 뺌.
- knowledge: 새 재료 10개(모두 reviewed, 추정 성분은 `confidence: low`), 재료 553 → 563, 별칭 1775 → 1803.
- 결과: 식품안전나라 미매칭 줄 415 → 24, 엔진 32 → 29. **미매칭 없는 레시피 1159 → 1471/1522**. 남은 51개 레시피는 모두 사람이 보류·제외로 정한 표기(자막 오류 문구, 라면 스프·조미유, 식용꽃, 위 미매칭 유지 9개, 재료 이름이 원문에 없는 것).
- 효과(전체 1,522개 중 미매칭이 없고 그 성분이 없는 레시피, um-4 전 → 후): 우유 694 → 905, 계란 772 → 997, 새우 925 → 1168, 조개류 911 → 1160, 참깨 834 → 1034, 땅콩 1088 → 1377, 대두 384 → 466, 밀 340 → 415.
- 테스트: `tests/kb/test_unmapped_round3.py` 7개(결정 반영, 모호 표기 알레르기, 시판 안내, 남은 미매칭은 사람이 보류·제외한 표기뿐, 소제목 빼기와 재료 소제목 유지, 소제목 목록). 지난 결정을 검사하던 테스트 5개를 um-4 결정에 맞춤('파'·'깨'는 종류 불명 재료로만, 보류 표기 검사에서 3차에서 다시 정한 표기 제외, 보정표 = 2·3차 D, 시판 안내 = 이전 ∪ 3차 E). **DB 포함 전체 516개 통과**, `tests/allergy` 무변경, 골든셋 0.88, `validate_data.py`·bench 통과.

### um-5 미매칭 4차 정리 · 꼭 확인 화면 (2026-10-18, 브랜치 `feature/unmapped-round4`)

- 사람 요청: 그동안의 검수 결과를 활용해 Claude가 검수하고, 사람이 확인해야 할 것만 지난번처럼. 대상은 um-4 뒤 남은 53줄(식품안전나라 24 · 엔진 29, 50개 레시피). 줄마다 레시피의 다른 재료·조리 단계·원문을 함께 봤다(`docs/review/unmapped_round4.yaml`).
- 바로 반영(지난 결정을 바꾸지 않는 것): 변환기가 '곁들이채소2 : 2가지색 미니파프리카'의 '2가지'를 양으로 읽던 문제 수정(`kb/foodsafety.py` `_starts_with_amount`), 번호 붙은 소제목('곁들이채소1')도 소제목 빼기 규칙에 맞게 비교 → 통삼겹스테이크 미매칭 해소(파프리카 연결). '케찹 5g,10g'의 10g은 원문에 재료 이름이 없어 유지. 식품안전나라 미매칭 줄 24 → 22, 연결된 재료 손실 0.
- **꼭 확인 25개**(남은 줄은 모두 사람이 1~3차에서 보류·반영 안 함으로 정한 표기라 바꾸려면 확인 필요): 검수 화면 `docs/review/unmapped_round4_review.html`(생성 `scripts/make_unmapped_round4_html.py`, 내보내기 `unmapped_round4_decisions.json`). 모두 '제안대로 O'로 미리 채움.
  - 파랑 13(조리 단계·원문 근거): 자막 문구 11개('비빌 때' → 올리브유, '잘 안뭉쳐서' → 전분, '마지막에' → 깨소금, '아니 저는' → 막국수, '000원에' → 애호박, '볶을때 단단' → 공심채, 재료 아닌 자막 5개는 뺌), '양파오이지 채수' → 오이·양파, '분말가루' → 시판 육수(5개 레시피).
  - 노랑 10(시판·가정식 성분 넓게 추정): 라면 스프·조미유 → 시판 라면 제품(12개 레시피), 갓장아찌, 코코아(가루·믹스), 키위소스, 바질 럽, 간편식 동봉 소스, 수제조미료 → 육수(종류 불명), 허브크러스트, 색 내는 가루, 호떡 믹스.
  - 빨강 2(지난 결정 뒤집기): 식용꽃(ir-2에서 지움, 9개 레시피) 알레르기 없음으로 다시 추가, 재료정보가 '.'뿐인 레시피(fs_799)에 조리 단계의 재료 16가지로 목록 만들기.
  - 모두 승인하면 미매칭 레시피 50 → 1(fs_3069 '10g').
- 테스트: `tests/kb/test_unmapped_round4.py` 3개(확인 대기는 미반영, 바로 반영분, '2가지' 규칙). `test_unmapped_round2.py` 보정표 비교에 4차 승인 D 포함. 전체 519개 통과(DB 포함), `tests/allergy` 무변경, `validate_data.py` 통과.

### um-5 보완: 꼭 확인 25개 사람 결정 반영 (2026-10-18)

- 사람 결정: 검수 화면에서 내보낸 `docs/review/unmapped_round4_decisions.json`(25개 모두 O). `docs/review/unmapped_round4.yaml` decision → O.
- 메모 반영: '.'(fs_799)은 "+ 기준으로 개별 식재료로 정리" → 조리 단계 재료 16가지를 재료 이름 그대로 한 줄씩(이름 보정표 split에 `text` 추가, `kb/foodsafety.py`). '시판 제품으로 성분표 확인 후 사용 권장' 메모 → 새 재료 6개(갓장아찌·코코아·키위소스·바질 럽·간편식 동봉 소스·호떡 믹스)를 시판 제품 안내에 추가(55 → 61개, 시판 라면 제품·시판 육수는 이미 대상).
- **반영 중 바꾼 것(보고 필요)**
  - '000원에'(→ 애호박)에 같은 메모가 있었으나 애호박은 시판 제품이 아니어서 안내 대상에 넣지 않았다.
  - 자막 문구 4개('저도 제일 좋아하는 반찬'·'양은'·'제가 제일 좋아하는 식재료'·'적절')는 승인 내용이 '뺌'이었으나 원본의 주재료(main) 줄이라 빼면 레시피에 주재료가 없어진다(테스트에서 발견). um-2 '코스트코에서'와 같이 그 레시피에 이미 있는 실제 주재료(돼지고기·순두부·삼겹살·삼겹살)로 연결(같은 재료라 알레르기 판정 동일).
  - 소제목 빼기 규칙을 이름 보정표보다 먼저 보게 바꿈: 보정표의 '볶음 소스'(간편식 소스)가 낙지볶음면의 소제목 '볶음소스:'(뒤에 재료가 적힘)에 붙지 않게. 이 때문에 장어구이의 소제목 '곁들이김치 :'(→ 김치, um-3 보정)가 빠졌으나 구성 재료 명이김치·백김치가 따로 있고 백김치의 알레르기가 김치와 같아 판정 손실 없음.
- knowledge: 새 재료 9개(식용꽃은 ir-2에서 지웠다가 다시 추가, 모두 reviewed·추정 성분 `confidence: low`), 재료 563 → 572. 엔진 이름 보정표(`data/recipe_name_overrides.yaml`)에 자막 문구·라면 스프·분말가루, 식품안전나라 보정표에 라면스프·수제조미료·간편식 소스·'.'.
- 결과: **미매칭 없는 레시피 1472 → 1521/1522**(자취요리신 100/100, 살림팝 169/169). 남은 1개는 원문 '케찹 5g,10g'의 10g(fs_3069, 재료 이름이 원문에 없음). 효과(미매칭 없고 그 성분 없는 레시피): 메밀 1432 → 1468, 땅콩 1378 → 1414, 참깨 1035 → 1065, 새우 1169 → 1193, 계란 998 → 1020, 우유 905 → 924.
- 테스트: `tests/kb/test_unmapped_round4.py`를 결정 반영 검사로(7개: 결정 = 내보내기, 반영, 남은 미매칭 1줄, 시판 안내·애호박 제외, split text, 소제목 규칙 우선, '2가지'). 지난 결정을 검사하던 테스트를 4차 결정에 맞춤(식용꽃 재추가, 엔진 보정표 = 1차 ∪ 4차 엔진 항목, 자막 문구 뺌 허용, 엔진 미매칭 0, 미매칭 draft 검사는 식품안전나라 포함). **DB 포함 전체 523개 통과**, `tests/allergy` 무변경, 골든셋 0.88, `validate_data.py`·bench 통과.

## 전체 레시피 추천 트랙 ar (브랜치 `feature/all-recipes`)

### ar-1 레시피 1,522개 전부를 추천 대상으로 (2026-10-17)

- 사람 결정: "1500개 모든 레시피를 대상으로 추천". 방식(사람 승인): draft 추천 켜기 + 식품안전나라를 엔진·DB에 적재, 원본에 없는 값은 지어내지 않고 '모름'으로 처리(점수 중간값, 맛을 모르면 매운맛 한도 사용자에게 제외, 조리시간을 모르면 시간 필터에서 빼지 않음). docs/decisions.md D3, docs/plan.md 3-2·4-2·4-3·4-4·5-3-1·부록 B 0003.
- 설정: `config/engine.yaml` `serve_draft_recipes: true`, `recipe_dirs: [data/recipes, data/recipes_foodsafety]`. `config/weights.yaml`에 `difficulty.unknown`·`time.unknown`·`taste.unknown`(0.5). 그래프 출처 설정에서 식품안전나라 `display_dir` 삭제(표시 전용 아님).
- 엔진: `Recipe.difficulty`·`cook_time_min`·`taste`가 None(모름) 가능. 이전에는 맛이 없으면 0으로 채워 매운맛 필터를 그대로 통과했다(맛 모르는 레시피가 '안 매움'으로 처리될 뻔함) → None으로 두고 필터·점수에서 따로 처리. 정렬 동점 기준에서 모르는 조리시간은 뒤로. 설명에 "조리시간, 난이도, 맛 정보가 없는 레시피입니다(점수는 중간값으로 계산)".
- **구현 중 발견·수정 2건**
  - 후보 생성은 주재료(main)를 가진 레시피만 잡는데 식품안전나라는 역할 구분이 없어 모두 sub라 한 건도 후보가 되지 못했다 → 주재료 표시가 하나도 없는 레시피는 sub를 후보 근거로(`engine.candidates.candidate_roles`, 후보 생성·색인·재료로 찾기·추천 과정 시각화가 같이 씀). 기존 369개(주재료 있음)는 동작 그대로.
  - 매운맛 한도 5(최대치)도 '한도'로 보고 맛 모르는 레시피 794개를 뺐다 → 한도가 5 미만일 때만 제외(5는 어떤 레시피도 넘지 않음).
- 적재·DB: `kb.recipes.load_recipe_specs`가 여러 폴더를 읽고 미분류·조리시간 없음 거부 규칙 삭제(published는 검증 규칙이 계속 요구). `scripts/load_recipes.py`·`validate_data.py` 기본 폴더 = recipe_dirs. 마이그레이션 0003(`0003_recipe_unknown_fields`, difficulty·cook_time_min NULL 허용; 처음 이름이 alembic 버전 칸 32자를 넘어 실패 → 줄임, 트랜잭션이라 DB 무변경). 되돌리기(downgrade)는 값을 지어내지 않고 모르는 레시피를 지운 뒤 NOT NULL. 개발 DB: 레시피 1,522개 적재(조리시간·난이도 있는 것 369, published 50), `validate_data.py --db` 통과.
- 화면: Streamlit 카드·추천 과정 재생 카드에서 모르는 값은 '-'.
- 결과(골든셋 페르소나 8명, 실제 데이터): 레시피 1,522개(식품안전나라 1,153 · draft 시드 319 · published 50)가 모두 엔진에 들어간다. 매운맛 한도가 없거나 5인 페르소나 4명은 추천 가능 621~881개 중 식품안전나라 589~794개. 매운맛 한도 1~4인 4명(초보·알레르기 많은 부모·매운 것 못 먹음·해산물 숙련자)은 식품안전나라가 모두 제외(맛 정보 없음, 설계대로). 알레르기 사용자에게는 미매칭 860개도 제외. **상위 10개에는 식품안전나라가 아직 없다**(최고 22~86위): 난이도·음식 종류·맛이 중간값이라 정보가 다 있는 레시피보다 점수가 낮다. 보유 재료가 잘 맞으면 올라온다(예: 단호박·우유·꿀 보유 → 상위 5개가 모두 식품안전나라).
- 테스트: `tests/logic/test_unknown_recipe_fields.py` 7개(맛 모름 → 매운맛 한도 사용자 제외·한도 5는 제외 안 함·한도 없으면 유지, 조리시간 모름 → 시간 필터 통과, 모름 점수 중간값·설명, 정렬 기준). 설계 변경을 검사하던 테스트 6개를 새 동작으로(적재 허용, published는 여전히 필수, draft 추천 기본 켬, 식품안전나라 = 엔진 레시피, /health 1,522개). **DB 포함 전체 499개 통과(건너뜀 0)**, `tests/allergy` 무변경, 골든셋 0.88(published만), bench p95 29.2ms.

## 기준점 트랙 bl (추천 로직 재설계 준비)

### bl-1 기준점 태그와 현재 추천 결과 기록 (2026-10-17)

- 사람 결정: 추천 로직을 바꿀 수 있어(이유는 복합적) 현재 레시피 정보를 유지한 채 먼저 통합하고 기준을 남긴다. PR #7(ar-1) main 병합 후 그 커밋에 태그 `baseline/v1`(원격에도 올림).
- 기준 결과 `docs/review/baseline_recommendations.md`(표)·`.json`(같은 내용): 지금 엔진(설정 그대로, 레시피 1,522개)으로 시나리오 14개(골든셋 페르소나 8명 + 보유 재료 시나리오 6개: 식품안전나라에 유리한 재료, 냉장고 거의 빔, 흔한 채소와 계란, 새우 알레르기, 매운 것 못 먹음(한도 1), 20분 엄수)의 추천 가능 수·출처별 수·제외 사유와 상위 20개(점수·I/K/T/P/D/M·부족 재료 수·검수 전/정보 없음 표시). 생성 `scripts/make_baseline_recommendations.py`. 기록이라 로직이 바뀌어도 고치지 않는다(새 로직 결과는 같은 시나리오로 따로 만들어 비교).
- 관찰: 상위 20개에 식품안전나라가 들어오는 것은 보유 재료가 맞는 시나리오뿐(단호박·우유·꿀 19개, 새우 알레르기 5개, 냉장고 거의 빔 3개, 흔한 채소 2개). 매운맛 한도가 있는 시나리오 5개는 식품안전나라 0개(맛 정보 없음으로 제외).
- 앞으로: 로직 재설계는 `baseline/v1`에서 새 브랜치로, 그동안 레시피 데이터는 고정. 바꾸고 싶은 점을 이 기준 결과를 보며 정리 → 설계 제안서 승인 → 기존 로직과 나란히(설정으로 선택) 구현해 비교.

## 사람 확인 필요

- (um-5) '000원에'(→ 애호박)의 '시판 제품 성분표 확인' 메모를 반영하지 않은 것, 주재료 자막 4줄을 '뺌' 대신 실제 주재료로 연결한 것 확인.
- (um-5) 개발 DB에 지식·레시피 다시 적재 필요(테스트 DB로만 확인).
- (um-3) 꼭 확인 17개 메모 해석 확인: 코코넛·도토리묵 '알레르기 제외' = 견과류(가능) 삭제로 반영.
- (um-4) 개발 DB에 지식·레시피 다시 적재(`scripts/compile_knowledge.py`·`scripts/load_recipes.py`) 필요. 이번에는 테스트 DB로만 확인했다.
- (um-3) 시판 제품 안내(`commercial_product_notice`) 대상에 2차 일괄 승인분 중 시판 제품(우스터소스·크래커·해선장·허니머스터드·제빵개량제·후르츠칵테일 등)을 넣을지. 지금은 넣지 않았다(1차·ir-2에서 사람이 정한 38개 그대로).

- **(ar-1) 식품안전나라 레시피 순위**: 모르는 값을 중간값(0.5)으로 두어 상위 10개에 거의 오르지 않는다. 더 자주 보이게 하려면 (가) `config/weights.yaml`의 unknown 값을 높이거나, (나) 재료로 매운맛 여부를 판정(고추류가 없으면 맵지 않음 등)하거나, (다) 조리 단계로 조리시간·난이도를 추정(확신 낮음)하는 방법이 있다. 어느 쪽도 정하지 않았다.
- **(ar-1) 매운맛 한도 사용자**: 맛 정보가 없는 식품안전나라 레시피는 매운맛 한도(5 미만)를 정한 사용자에게 모두 제외된다(설계대로). 위 (나)를 하면 상당수를 살릴 수 있다.

- **(ir-2) 보류한 시판 제품 6개**: 시판 고기 양념·불닭소스·참소스·폰즈 소스·감자칩·순대는 포장 알레르기 표시를 확인한 뒤 `docs/review/ingredient_review.html`에서 다시 검수(지금 화면에는 이 6개만 나온다).
- (ir-2) 메모 해석 확인: 안내 대상 38개(알레르기 없는 재료 포함), 확인 없이 승인한 시판 제품의 reviewed 처리.
- (um-2) 승인과 다르게 반영한 2건('양념은 불닭소스', '코스트코에서')을 위 기록대로 확인.

- **(int-4) 병합 PR 리뷰·병합**: `feature/ontology-integration` → main PR. 병합 후 PR #2(레시피 1차 확장)는 이 PR에 포함되어 닫는다. 병합 뒤 레시피를 실제 추천에 쓰려면 아래 fs-3 → data-1·data-2 검수 → 골든셋 처리 → published 전환 순서.

- **(int-4) 그래프 화면 로딩 측정**: 창을 앞에 띄운 상태에서 `/viz?display=1`(1522개)의 HUD 로딩 시간을 잰다(viz-5 기준 1천 개 3~5초). 백그라운드 측정값(1.1~11.6초)은 부정확하다.

- **(adhoc-1) 외부 레시피 분석 확인**: `/viz` "외부 레시피 분석"에서 예시 넣기 → 분석. 안전 관련 판정 테스트(possible·미매칭·concept 제외)를 `tests/api/`에 두었다. `tests/allergy/`로 옮겨 승인 대상으로 둘지 정한다.

- **(ui-2) 알레르기 주의 표시 방식 확인**: 재료로 찾기에서는 알레르기 레시피를 빼지 않고 ⚠️로 보여 준다(사람 결정). 안내 문구(`config/display.yaml` `browse_allergy_notice`)와 경고 레시피를 뒤로 정렬하는 방식이 괜찮은지 확인. 추천 탭의 제외 규칙은 그대로다.

- **(fs-3) 식품안전나라 보강안 검수**: `docs/review/foodsafety_alias_proposal.md`의 A·B 승인 열에 O/X, C 보류 처리, D 변환 규칙 적용 여부를 정한다. 승인분만 knowledge에 draft로 반영한다. 상업화 전에는 식약처에 이용 조건 문의(D3 보완 3).
- **(보류, data-4) 레시피 1차 확장 검수·골든셋 재선정**: 위 "data-4"의 "보류를 풀 때 할 일" 순서대로 진행. 아래 data-1·data-2 항목도 이때 함께 처리한다.
- (해결, data-3) "순두부" 절대 불선호 범위: 지금 동작 유지(두부 요리도 제외). 불선호의 "포함 가능" 처리는 "다음 단계 제안" 11번에서 검토.
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
- (ui-1) 레시피 상세의 보유 표시는 대체재를 반영하지 않는다. 추천 카드에서 대체 안내(🔄)가 나온 재료도 상세에서는 ⬜로 보인다.
- (1-5) FastAPI TestClient가 `httpx` 사용 관련 StarletteDeprecationWarning을 낸다(동작 영향 없음).
- 정제 식용유(콩기름 등)의 대두 알레르기 처리 기준은 0-4 검수표에서 사람이 판단한다.

## 다음 할 일

- MVP(Phase 0~1) 완료. Phase 2는 사람이 범위를 정한 뒤 시작한다(아래 "다음 단계 제안").
- 시각화 트랙 완료(viz-v1). 시연은 README 6-1 "시연 순서"(시연 프로필은 `scripts/seed_demo_profiles.py`).
- 새 재료를 추가할 때는 status: draft로 넣고 검수표(`scripts/make_review.py`)로 사람 확인 후 reviewed.
- 전체 레시피 추천(ar-1) main 병합(PR #7), 기준점 `baseline/v1`과 기준 결과(bl-1). 다음: 기준 결과를 보며 추천 로직에서 바꿀 점 정리 → 설계 제안서.
- 통합 트랙(int-4): PR #4 main 병합 완료(2026-10-17). 병합 후 레시피 활용(미매칭 보강 → 레시피 검수 → 골든셋 → published 전환)은 main 위에서 단계별로 진행한다.
- 데이터 확장 트랙(data-1, `feature/recipe-expansion`): 신규 레시피 50개 draft 검수 대기. 승인된 레시피는 published로 바꾸고 `tests/kb/test_recipe_seed.py`의 `PUBLISHED_IDS`에 추가, soft_tofu 승인 시 reviewed로 바꾸고 `tests/kb/test_real_knowledge.py`의 `DRAFT_INGREDIENTS`에서 뺀다. published 전환 전에 골든셋 처리 방법을 정한다.

## 다음 단계 제안 (Phase 2 이후, 범위 밖)

외부 레시피 분석(adhoc) 후속(범위 밖, 사람 결정): 분석한 레시피를 draft YAML로 저장(source: ai_generated) → 기존 검수 절차, 미매칭 표기를 `unmapped_term`에 누적해 검수표로 연결, 줄별 역할·선택 재료 지정 입력.

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
11. **"포함 가능"을 알레르기와 불선호에서 다르게 다룰지 검토**(data-3 측정, 2026-10-04, 알레르기 판정은 바꾸지 않는 전제): 절대 불선호도 알레르기와 같은 `ingredient_contains`(부록 C)를 쓰므로, 넓은 재료(닭고기·돼지고기·쇠고기·두부·치즈 등)를 쓰는 레시피와 그 넓은 재료를 원천으로 둔 가공품(햄·소시지·통조림햄·카레가루 등) 레시피가 "포함 가능"으로 함께 제외된다. 하위 재료 26개를 하나씩 절대 불선호로 둔 측정(엔진 필터를 모든 레시피에 적용, 후보 여부 무관):

    | 절대 불선호 | published 50: 직접 / 파생(확실) / 포함 가능만 / 합계 | draft 포함 100: 직접 / 파생(확실) / 포함 가능만 / 합계 |
    |---|---|---|
    | 닭가슴살 | 0 / 0 / 4 / 4 | 1 / 0 / 19 / 20 |
    | 닭다리살 | 1 / 0 / 4 / 5 | 1 / 0 / 19 / 20 |
    | 삼겹살 | 0 / 1 / 7 / 8 | 1 / 2 / 18 / 21 |
    | 돼지고기 목살·앞다리살·안심·갈비(각각) | 0 / 0 / 7 / 7 | 0 / 0 / 18 / 18 |
    | 불고기용 소고기 | 3 / 0 / 3 / 6 | 3 / 0 / 7 / 10 |
    | 소고기 안심·차돌박이(각각) | 0 / 0 / 3 / 3 | 0 / 0 / 7 / 7 |
    | 순두부 | 0 / 0 / 7 / 7 | 1 / 0 / 8 / 9 |
    | 방울토마토 | 0 / 0 / 4 / 4 | 1 / 0 / 8 / 9 |
    | 파마산치즈 | 2 / 0 / 1 / 3 | 5 / 0 / 1 / 6 |

    26개 합계: published 직접 17 · 파생 1 · 포함 가능만 106, draft 포함 직접 28 · 파생 2 · 포함 가능만 269. 예: "닭가슴살 못 먹음"이면 닭가슴살이 직접 든 레시피는 1개인데 닭고기(넓은 재료)·햄·소시지·카레가루·돈가스소스 등으로 19개가 더 제외된다. 알레르기에서는 안전 쪽(포함 가능도 제외)이 맞지만, 부위 불선호에는 과하다. 검토안: 불선호 판정만 is_a 하위 방향 possible을 따르지 않는 별도 contains를 둘지, possible 불선호는 제외 대신 감점으로 둘지. 전체 표는 측정 스크립트 결과(재현: 분석용 `.scratch`, 커밋 안 함).

Phase 3 이후(참고): user_event 기반 개인화 재정렬(4-6 상위 50개), 유통기한(expires_on) 활용, 장보기 목록, React 화면.
