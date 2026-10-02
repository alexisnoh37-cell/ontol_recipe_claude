# 진행 상황

> 에이전트는 각 단계가 끝날 때마다 이 파일을 갱신합니다. 새 세션은 이 파일부터 읽습니다.

## 현재 단계

Phase 0-1 완료. 다음은 Phase 0-2(스키마와 지식 컴파일러).

## 단계별 상태

| 단계 | 상태 | 완료일 | 사람 확인 | 비고 |
| --- | --- | --- | --- | --- |
| 0-1 설계 확정 | 완료 | 2026-10-03 | 완료 | docs/plan.md 부록 A~C, knowledge/README.md |
| 0-2 스키마와 지식 컴파일러 | 대기 | | | |
| 0-3 알레르기 테스트 작성 | 대기 | | 필요(시나리오 승인) | |
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

## 알려진 문제

- **D4 알레르기 목록 미확정**: allergens.yaml은 0-2에서 example 그대로 `status: draft`로 옮긴다. 0-4 시작 전에 사람이 표시 대상 목록과 생선 그룹 단위를 확정해야 한다(액젓의 derived_from 대상도 이에 따라 정해짐).
- 0-2에서 example을 확정 형식으로 옮길 때 `garlic_minced` → `garlic`으로 바뀌므로 `config/pantry_staples.yaml`의 id도 함께 고쳐야 한다.
- 정제 식용유(콩기름 등)의 대두 알레르기 처리 기준은 0-4 검수표에서 사람이 판단한다.

## 다음 할 일

- Phase 0-2: docker-compose(PostgreSQL 16), pyproject(uv), Alembic 마이그레이션(부록 B), knowledge 실제 파일과 vocab.yaml, `kb/` + `scripts/compile_knowledge.py`(부록 C), `scripts/validate_data.py`(5-4), `tests/kb/` 컴파일러 테스트, README Windows 실행 방법.

## 다음 단계 제안 (범위 밖 아이디어)

- cuisine 외에 요리 유형(찌개, 볶음, 면 등) 선호 축 추가
- 식단 조건(채식 등) 필터 — Phase 2
- 자동완성 검색 품질을 위한 pg_trgm 인덱스
