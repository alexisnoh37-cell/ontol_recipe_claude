# 자취요리신 데이터 변환 기록

> `scripts/convert_simplecooking.py`가 생성한다. 손으로 고치지 않는다.

원본 `recipes/simplecooking/*.yaml` 100개를 `data/recipes/<id>.yaml`(draft)로 변환했다. 원본 파일은 바꾸지 않는다.

## 원본과 같은 것

id·파일 이름(아래 표의 id 변경 제외), 제목, 난이도, 시간, 인분, status(draft), confidence, note(아래 추가분 제외), 재료 원문(raw_text)·역할·선택 여부·양·단위, 맛, 조리 단계와 기법.

## 형식 때문에 달라진 것 (전체 공통)

| 원본 | 변환본 | 이유 |
| --- | --- | --- |
| `ingredients[].name`(한국어 이름) | `ingredients[].ingredient`(knowledge id 또는 null) | 시드는 정규 id를 쓴다. 이름·별칭(공백 무시)이 정확히 맞을 때만 매핑, 그 외 null(미매칭) |
| `source`(객체: 채널·영상 제목·URL·날짜) | `source`(영상 URL 문자열) | 시드 형식의 source는 문자열. 나머지 출처 정보는 원본에 있다 |

## 레시피별로 달라진 것

| id | 제목 | 변경 |
| --- | --- | --- |
| `obun_gimcijjim_pvrcuh` | 5분 김치찜 | id '5bun_gimcijjim_pvrcuh'→'obun_gimcijjim_pvrcuh'(시드 id 형식, 원본 파일 이름은 그대로) |
| `beopalro_hasdalgdarisal_5ypayh` | 버팔로 핫닭다리살 | cuisine '기타'→'양식'(vocab에 없음, 검수 필요) |
| `bomdong_deulgireum_maggugsu_lgcb36` | 봄동 들기름 막국수 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `cadolbulgeuri_6g8c3x` | 차돌불그리 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요) |
| `camcikaeneul_deo_masissge_meogeoboja_7mulhb` | 참치캔을 더 맛있게 먹어보자 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `ggareubo_buldalg_ddeogboggi_exlla0` | 까르보 불닭 떡볶이 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요) |
| `gocujang_mogsalgui_e6l5ob` | 고추장 목살구이 | 조리기구 '토치'(선택) 제외(vocab에 없음) |
| `jidori_udong_z7aj3j` | 지도리 우동 | 조리기구 '토치'(선택) 제외(vocab에 없음) |
| `maeun_koncijeudalggui_vyiwuv` | 매운 콘치즈닭구이 | 조리기구 '토치'(선택) 제외(vocab에 없음) |
| `niggugamatama_udong_ta6cbt` | 니꾸가마타마 우동 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `odengeul_hwalyonghayeo_buldalgbbalganodeng_vnp9_n` | 오뎅을 활용하여 불닭빨간오뎅 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요) |
| `rojejjimdalg_qfddnt` | 로제찜닭 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요) |
| `yangnyeomgalbi_mas_dalggui_o9xd` | 양념갈비 맛 닭구이 | 조리기구 '토치'(선택) 제외(vocab에 없음) |

## 재료 매핑

- 모든 재료가 매핑된 레시피: 54/100
- 미매칭 재료가 있는 레시피: 46/100 (알레르기가 있는 사용자에게 제외됨)

미매칭 재료(등장 레시피 수). 상표 제품·시판 소스·가공품은 성분을 추측하지 않고 미매칭으로 둔다. 연결하려면 knowledge에 노드나 별칭을 검수해 추가한 뒤 다시 변환한다.

| 재료 이름 | 레시피 수 |
| --- | --- |
| 김가루 | 6 |
| 너구리 | 5 |
| 사리곰탕 라면 | 5 |
| 멸치칼국수 라면 | 4 |
| 조미유 | 4 |
| 분말 스프 | 3 |
| 까르보 불닭볶음면 | 2 |
| 냉면 육수 | 2 |
| 불닭 스프 | 2 |
| 불닭볶음면 | 2 |
| 비빔면 | 2 |
| 사천짜파게티 | 2 |
| 생생우동 | 2 |
| 짜파게티 | 2 |
| 참소스 | 2 |
| 깨 | 1 |
| 꼬꼬면 | 1 |
| 레트로 미트볼 | 1 |
| 매운 갈비 양념 | 1 |
| 매운 갈비양념 | 1 |
| 매운 라면 | 1 |
| 불닭볶음탕면 | 1 |
| 수제비 | 1 |
| 순대 | 1 |
| 신라면 | 1 |
| 쌍화탕 | 1 |
| 전분가루 | 1 |
| 진짜 쫄면 라면 | 1 |
| 진쫄면 | 1 |
| 쫄면 | 1 |
| 찜닭 소스 | 1 |
| 찜닭 양념 | 1 |
| 컵누들 마라탕 | 1 |
| 콜라 | 1 |
| 크림스프 | 1 |
| 포카칩 | 1 |
| 폰즈 소스 | 1 |

## 같은 재료 id로 매핑된 줄

원본에서 이름이 달라 따로 적힌 줄이 같은 knowledge id로 매핑된 경우. 한 줄로 합칠지 검수한다(변환은 원본 줄을 그대로 둔다).

| id | 재료 id | 원문 |
| --- | --- | --- |
| `alrioolrio_eadcoy` | `pasta` | 냉동 파스타면 / 스파게티면 |
| `daepaeyangbaecujjim_rkfz2f` | `soy_sauce` | 진간장 2스푼 / 간장 |
| `dalgramyeon_jnxcqn` | `soy_sauce` | 진간장 1/2스푼 / 간장 |
| `niggugamatama_udong_ta6cbt` | `egg` | 계란 / 노른자 |
