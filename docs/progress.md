# 진행 상황

> 에이전트는 각 단계가 끝날 때마다 이 파일을 갱신합니다. 새 세션은 이 파일부터 읽습니다.

## 현재 단계

Phase 0-3 완료(사람 승인, 2026-10-03). **tests/allergy/는 이제 수정·삭제·skip 금지.** 118개 중 115개는 엔진 미구현으로 실패(NotImplementedError)하는 것이 정상이고, 적재 검증 3개는 통과한다. 다음은 Phase 0-4(시작 전 사람이 D4 알레르기 목록 확정).

## 단계별 상태

| 단계 | 상태 | 완료일 | 사람 확인 | 비고 |
| --- | --- | --- | --- | --- |
| 0-1 설계 확정 | 완료 | 2026-10-03 | 완료 | docs/plan.md 부록 A~C, knowledge/README.md |
| 0-2 스키마와 지식 컴파일러 | 완료 | 2026-10-03 | 필요(아래 승인 필요 2건) | 테스트 72개 통과, Docker DB에 마이그레이션·컴파일 반영 확인 |
| 0-3 알레르기 테스트 작성 | 완료 | 2026-10-03 | 완료(승인) | 118개. 1-1 전까지 115개 실패가 정상 |
| 0-4 식재료 200개 확장 | 대기 | | 필요(검수표) | 시작 전 사람이 알레르기 목록 확정(D4) |
| 1-1 필터 엔진 | 대기 | | | |
| 1-2 점수 엔진 | 대기 | | 선택 | |
| 1-3 레시피 시드 | 대기 | | 필요(검수표) | |
| 1-4 골든셋 | 대기 | | 필요(기대 결과) | |
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
- **레시피 시드 형식 잠정안**(승인 필요): `kb/datacheck.py`의 RecipeSpec. DDL 컬럼을 그대로 따르고 1-3에서 확정.
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

## 알려진 문제

- **D4 알레르기 목록 미확정**: allergens.yaml은 0-2에서 example 그대로 `status: draft`로 옮긴다. 0-4 시작 전에 사람이 표시 대상 목록과 생선 그룹 단위를 확정해야 한다(액젓의 derived_from 대상도 이에 따라 정해짐).
- (해결) `garlic_minced` → `garlic` 변경을 `config/pantry_staples.yaml`에 반영함.
- 콩기름(soybean_oil)과 식용유(cooking_oil) 사이 is_a 관계는 두지 않았다. 두면 식용유(기본 양념)가 대두 possible이 되어 대두 알레르기 사용자에게 기름을 쓰는 레시피가 대부분 제외된다. 0-4 검수에서 정한다.
- 알레르기 그룹 6개(crab, fish, pine_nut, shellfish, squid, walnut)는 아직 재료가 없어 컴파일 경고가 난다. 0-4에서 재료를 채운다.
- `uv run pytest` 전체는 Phase 1-1 전까지 tests/allergy 때문에 실패로 끝난다(의도). 나머지만 볼 때는 `uv run pytest --ignore=tests/allergy`.
- 샌드박스 환경에서는 pytest의 기본 임시 폴더 접근이 막혀 `--basetemp`를 지정해 실행했다(일반 환경에서는 불필요).
- 정제 식용유(콩기름 등)의 대두 알레르기 처리 기준은 0-4 검수표에서 사람이 판단한다.

## 다음 할 일

- Phase 0-4: 시작 전에 사람이 알레르기 표시 대상 목록(D4) 확정 → 식재료 200개 확장과 검수표.

## 다음 단계 제안 (범위 밖 아이디어)

- cuisine 외에 요리 유형(찌개, 볶음, 면 등) 선호 축 추가
- 식단 조건(채식 등) 필터 — Phase 2
- 자동완성 검색 품질을 위한 pg_trgm 인덱스
