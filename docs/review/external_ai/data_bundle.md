# 검토 자료 번들 — 식재료·알레르기

> 생성일 2026-10-16, 브랜치 feature/recipe-expansion, 커밋 0754474. knowledge/와 docs/review/ingredients_review.md의 스냅샷입니다.

# A. 검수표 (상속 포함 최종 결과)

## 식재료 검수표

> `scripts/make_review.py`가 컴파일 결과로부터 생성합니다. 이 파일을 직접 고치지 말고 `knowledge/`를 고친 뒤 다시 생성하세요.

- 재료 253개(분류 노드 3개), 그중 `confidence: low` 68개
- 알레르기 그룹: 기본 23개(법정 19개, 자체 4개), 묶음 4개
- source_hash `28feb3384bc1`

### 읽는 법

- **상위 개념**: is_a 부모. 부모의 알레르기를 그대로 물려받습니다.
- **파생 원천**: derived_from. `(가능)`은 제품에 따라 들어갈 수 있다는 뜻(possible)입니다.
- **걸리는 알레르기**: 상속까지 계산한 기본 그룹 목록(묶음 그룹은 생략). `(가능)`도 알레르기 판정에서는 제외 대상입니다.
- 확인할 것: 원천이 빠졌거나 틀린 가공품, `(가능)`이어야 하는데 확정이거나 그 반대인 것, 별칭으로 묶으면 안 되는 것.

### 컴파일 경고

- `derived_not_processed` knowledge/ingredients/vegetables.yaml#41 (soybean_sprouts): derived_from이 있는데 is_processed가 지정되지 않았습니다
- `deep_is_a` knowledge/ingredients/seafood.yaml#50 (anchovy_fish_sauce): is_a 계층이 4단계입니다(권장 3단계 이내)
- `deep_is_a` knowledge/ingredients/seafood.yaml#51 (sand_lance_fish_sauce): is_a 계층이 4단계입니다(권장 3단계 이내)

### 1. 확신 낮음 (`confidence: low`) — 68개

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `almond` | 아몬드 |  |  | 기타 견과류(아몬드·밤 등) | 법정 표시 대상이 아니어서 자체 그룹 기타 견과류에 둠(0-4 검수) |
| `beef_bone` | 사골 | 쇠고기 |  | 쇠고기 | 우족(소 발)을 사골의 별칭으로 묶어도 되는지 검수 |
| `beef_bone_broth` | 사골육수 |  | 사골 | 쇠고기 | 시판 제품은 우유·대두 등 첨가가 있는지 확인 필요 |
| `beef_seasoning` | 쇠고기 맛 조미료 |  | 대두(가능), 밀가루(가능), 쇠고기(가능) | 대두(가능), 밀(가능), 쇠고기(가능) | 쇠고기 추출물 함량이 낮거나 없는 제품도 있음. 밀·대두 제품별 상이 |
| `bread` | 식빵 |  | 밀가루, 계란(가능), 대두(가능), 우유(가능) | 밀, 대두(가능), 알류(가금류)(가능), 우유(가능) | 우유·계란·대두 함유 여부는 제품별 상이 |
| `bread_crumbs` | 빵가루 |  | 밀가루, 계란(가능), 대두(가능), 우유(가능) | 밀, 대두(가능), 알류(가금류)(가능), 우유(가능) | 빵을 갈아 만듦. 우유·계란·대두 함유 여부는 제품별 상이 |
| `buchimgaru` | 부침가루 |  | 밀가루, 계란(가능), 대두(가능), 우유(가능) | 밀, 대두(가능), 알류(가금류)(가능), 우유(가능) | 밀가루 주원료. 대두분·난분·탈지분유 첨가 여부는 제품별 상이 |
| `buckwheat_flour` | 메밀가루 |  | 메밀, 밀가루(가능) | 메밀, 밀(가능) | 밀가루를 섞은 제품이 있음 |
| `buckwheat_noodles` | 메밀면 |  | 메밀, 밀가루(가능) | 메밀, 밀(가능) | 대부분 밀가루를 섞음. 밀 possible |
| `canned_tuna` | 참치캔 |  | 참치, 콩기름(가능) | 기타 생선(고등어 외), 대두(가능) | 기름담금 제품은 대두유 사용이 많음(정제유의 대두 처리 기준은 soybean_oil 검수에 따름) |
| `cheongju` | 청주 |  | 쌀 | - | 맛술과 같은 이유로 확인 필요 |
| `chestnut` | 밤 |  |  | 기타 견과류(아몬드·밤 등)(가능) | 밤을 견과 알레르기로 볼지 사람마다 달라 기타 견과류 possible(0-4 검수) |
| `chicken_stock` | 치킨스톡 |  | 닭고기, 대두(가능), 밀가루(가능), 우유(가능) | 닭고기, 대두(가능), 밀(가능), 우유(가능) | 고형·분말 제품은 밀·대두·유당 첨가가 흔함 |
| `chunjang` | 춘장 |  | 대두, 밀가루 | 대두, 밀 | 대두·밀이 주원료인 제품 기준 |
| `cooking_oil` | 식용유 |  |  | - | [기본 양념] 콩기름(대두유)은 별도 재료 soybean_oil. '식용유'가 콩기름일 수 있는 문제(대두 알레르기)는 검수 필요 |
| `corn_syrup` | 물엿 |  |  | - | [기본 양념] 조청(쌀 등을 고아 만든 것)과 물엿(전분당)은 원료가 다름. 별칭으로 둘지 검수 |
| `curry_powder` | 카레가루 |  | 밀가루, 닭고기(가능), 대두(가능), 돼지고기(가능), 쇠고기(가능), 우유(가능), 토마토(가능) | 밀, 닭고기(가능), 대두(가능), 돼지고기(가능), 쇠고기(가능), 우유(가능), 토마토(가능) | 국내 즉석 카레가루 기준 밀 definite. 향신료만 섞은 커리파우더는 밀이 없을 수 있음(별도 재료로 나눌지 검수). 유청·육류 추출물 등은 제품별 상이 |
| `doenjang` | 된장 |  | 대두, 밀가루(가능) | 대두, 밀(가능) | [기본 양념] 밀 포함 여부는 제품별 상이 |
| `doubanjiang` | 두반장 |  | 대두(가능), 밀가루(가능) | 대두(가능), 밀(가능) | 잠두(누에콩)가 주원료. 대두·밀 첨가는 제품별 상이 |
| `dried_apricot` | 건살구 |  | 아황산염(가능) | 아황산류(가능) | 살구 원물은 재료로 두지 않음. 아황산류 처리 제품이 흔하다고 알려져 있으나 확인 필요 |
| `dried_persimmon` | 곶감 |  | 감, 아황산염(가능) | 아황산류(가능) | 갈변 방지용 아황산류 처리 제품이 있음. 제품별 상이 |
| `fish_cake` | 어묵 |  | 생선, 계란(가능), 대두(가능), 밀가루(가능) | 고등어(가능), 기타 생선(고등어 외)(가능), 대두(가능), 밀(가능), 알류(가금류)(가능) | 어종이 제품마다 달라 '생선'(분류 노드)에서 파생 → 모든 생선 그룹 possible. 밀가루·전분·대두단백 첨가 제품 많음 |
| `fish_sauce` | 액젓 | 젓갈류 |  | 기타 생선(고등어 외)(가능) | 원료 어종을 모르는 넓은 재료. 하위(멸치액젓·까나리액젓)의 알레르기를 possible로 가짐. 피시소스(동남아)를 별칭으로 묶어도 되는지 검수 |
| `frozen_dumplings` | 냉동만두 |  | 밀가루, 계란(가능), 닭고기(가능), 돼지고기(가능), 두부(가능), 배추김치(가능), 쇠고기(가능) | 밀, 기타 생선(고등어 외)(가능), 닭고기(가능), 대두(가능), 돼지고기(가능), 새우(가능), 쇠고기(가능), 알류(가금류)(가능), 조개류(굴·전복·홍합 포함)(가능) | 만두피는 밀. 소는 제품마다 다름(고기·두부·김치·새우 등). 새우만두는 별도 재료로 두지 않음 |
| `frying_mix` | 튀김가루 |  | 밀가루, 계란(가능), 대두(가능), 우유(가능) | 밀, 대두(가능), 알류(가금류)(가능), 우유(가능) | 부침가루와 같은 이유 |
| `glass_noodles` | 당면 |  | 고구마 | - | 고구마전분 당면 기준. 다른 전분을 쓰는 제품도 있음 |
| `gochujang` | 고추장 |  | 고춧가루, 대두, 밀가루(가능) | 대두, 밀(가능) | [기본 양념] 밀 포함 여부는 제품별 상이(밀 고추장 많음). 포함 가능으로 처리 |
| `green_chili` | 풋고추 |  |  | - | 오이고추·꽈리고추는 품종이 다르고 맵기도 다름. 별도 재료로 나눌지 검수 |
| `ham` | 햄 |  | 돼지고기, 닭고기(가능), 대두(가능), 밀가루(가능), 우유(가능) | 돼지고기, 닭고기(가능), 대두(가능), 밀(가능), 우유(가능) | 돼지고기 햄 기준. 닭고기 혼합, 대두단백·밀·유청 첨가 제품이 있어 possible |
| `heavy_cream` | 생크림 |  | 우유 | 우유 | 식물성 휘핑크림(유지방 아님)은 우유 성분이 없거나 적을 수 있음. 휘핑크림을 별칭으로 둘지 검수 |
| `imitation_crab` | 게맛살 |  | 생선, 게(가능), 계란(가능), 대두(가능), 밀가루(가능) | 게(가능), 고등어(가능), 기타 생선(고등어 외)(가능), 대두(가능), 밀(가능), 알류(가금류)(가능) | 연육(생선살)이 주원료. 게 추출물·밀·난백·대두 함유 제품 있음 |
| `kimchi` | 배추김치 |  | 고춧가루, 배추, 굴(가능), 밀가루(가능), 새우젓(가능), 액젓(가능) | 기타 생선(고등어 외)(가능), 밀(가능), 새우(가능), 조개류(굴·전복·홍합 포함)(가능) | 젓갈 종류·포함 여부가 제품별로 다름. 새우젓·액젓(멸치·까나리 등 생선)·굴 possible. 밀가루풀을 쑤는 제품이 있어 밀 possible |
| `kkakdugi` | 깍두기 |  | 고춧가루, 무, 굴(가능), 밀가루(가능), 새우젓(가능), 액젓(가능) | 기타 생선(고등어 외)(가능), 밀(가능), 새우(가능), 조개류(굴·전복·홍합 포함)(가능) | 배추김치와 같은 이유 |
| `lemon` | 레몬 |  |  | - | 시판 레몬즙에 아황산류가 들어가는 제품이 있는지 검수(있으면 별도 가공품으로 분리) |
| `luncheon_meat` | 통조림햄 |  | 돼지고기, 닭고기(가능), 대두(가능), 밀가루(가능) | 돼지고기, 닭고기(가능), 대두(가능), 밀(가능) | 돼지고기 주원료. 닭고기 혼합·대두단백·전분(밀 가능) 제품 있음 |
| `mirin` | 맛술 |  | 쌀 | - | 쌀 발효 조미술. 아황산류 첨가 여부 확인 필요 |
| `miso` | 미소된장 |  | 대두, 밀가루(가능) | 대두, 밀(가능) | 보리·쌀 누룩 사용. 밀 사용 제품 있음 |
| `naengmyeon_noodles` | 냉면사리 |  | 감자전분(가능), 고구마(가능), 메밀(가능), 밀가루(가능) | 메밀(가능), 밀(가능) | 물냉면(메밀·밀)·비빔냉면(전분) 등 제품별 원료 상이 |
| `napa_cabbage` | 배추 |  |  | - | 절임배추(소금 절임)를 별칭으로 묶음. 별도 재료로 둘지 검수 |
| `octopus` | 문어 | 해산물 |  | 기타 연체류(문어·낙지·주꾸미) | 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수) |
| `oyster_sauce` | 굴소스 |  | 굴, 대두(가능), 밀가루(가능) | 조개류(굴·전복·홍합 포함), 대두(가능), 밀(가능) | 굴 추출물 주원료. 밀가루·전분·간장 첨가 제품 있음 |
| `pacific_saury` | 꽁치 | 생선 |  | 기타 생선(고등어 외) | 꽁치는 고등어과가 아님(꽁치과)으로 알고 있으나 확인 필요 |
| `pasta` | 파스타 |  | 밀가루, 계란(가능) | 밀, 알류(가금류)(가능) | 듀럼밀(밀). 생면·에그파스타는 계란 포함 |
| `pickled_radish` | 단무지 |  | 무 | - | 보존료·표백제(아황산류) 사용 여부 확인 필요 |
| `pollock` | 명태 | 생선 |  | 기타 생선(고등어 외) | 코다리(반건조 명태)를 별칭으로 묶음. 별도 가공품으로 둘지 검수 |
| `raisin` | 건포도 |  | 포도, 아황산염(가능) | 아황산류(가능) | 아황산류 첨가 여부는 제품별 상이 |
| `ramen_noodles` | 라면 |  | 밀가루, 대두(가능), 쇠고기(가능), 우유(가능) | 밀, 대두(가능), 쇠고기(가능), 우유(가능) | 면은 밀. 스프(분말)의 대두·쇠고기·우유 등은 제품별 상이. 사리만 쓰는 경우와 구분할지 검수 |
| `salt` | 소금 |  |  | - | [기본 양념] 맛소금은 MSG가 섞인 제품. 알레르기 성분은 없다고 보고 별칭으로 둠 |
| `sausage` | 소시지 |  | 닭고기(가능), 대두(가능), 돼지고기(가능), 밀가루(가능), 쇠고기(가능), 우유(가능) | 닭고기(가능), 대두(가능), 돼지고기(가능), 밀(가능), 쇠고기(가능), 우유(가능) | 원료육이 제품마다 다름(돼지·닭·소 혼합). 모두 possible |
| `scallop` | 가리비 | 조개 |  | 조개류(굴·전복·홍합 포함) | 관자는 키조개 관자일 수도 있으나 둘 다 조개류라 알레르기 판정은 같음 |
| `seasoned_laver` | 조미김 |  | 김, 들기름(가능), 참기름(가능) | 참깨(가능) | 참기름·들기름·식용유 중 무엇을 쓰는지 제품마다 다름 |
| `small_octopus` | 낙지 | 해산물 |  | 기타 연체류(문어·낙지·주꾸미) | 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수) |
| `soy_sauce` | 간장 |  | 대두, 밀가루 | 대두, 밀 | [기본 양념] 국간장(조선간장)은 밀이 없는 제품이 많으나 보수적으로 밀 definite. 국간장을 별도 재료로 나눌지 검수 |
| `soybean_oil` | 콩기름 |  | 대두(가능) | 대두(가능) | 정제유의 대두 알레르기 처리 기준은 사람이 판단. 식용유(cooking_oil)와의 is_a 관계는 두지 않음 |
| `soybean_sprouts` | 콩나물 |  | 대두 | 대두 | 대두를 발아시킨 것. 대두 알레르기에서 제외 대상으로 볼지 검수(가공품이 아니라 is_processed는 두지 않음 → 컴파일 경고 1건) |
| `spanish_mackerel` | 삼치 | 생선 |  | 기타 생선(고등어 외) | 삼치는 고등어과지만 법정 표시 대상 '고등어'와 다른 어종으로 보고 기타 생선에 둠. 고등어 그룹에도 넣을지 검수 |
| `squid` | 오징어 | 해산물 |  | 오징어 | 한치(오징어류)를 별칭으로 묶음. 법정 '오징어'에 한치가 포함되는지 검수 |
| `ssamjang` | 쌈장 |  | 고추장, 된장, 참기름(가능) | 대두, 밀(가능), 참깨(가능) | 된장·고추장 기반. 참기름·참깨 첨가 제품이 많아 possible |
| `tomato_sauce` | 토마토소스 |  | 토마토, 우유(가능), 치즈(가능) | 토마토, 우유(가능) | 치즈·크림 첨가 제품 있음 |
| `tonkatsu_sauce` | 돈가스소스 |  | 대두(가능), 밀가루(가능), 아황산염(가능), 토마토(가능) | 대두(가능), 밀(가능), 아황산류(가능), 토마토(가능) | 채소·과일 퓨레, 간장, 토마토, 전분 등 제품별 상이 |
| `tortilla` | 또띠아 |  | 밀가루, 옥수수(가능) | 밀 | 밀 또띠아 기준. 옥수수 또띠아도 있음 |
| `tsuyu` | 쯔유 |  | 가쓰오부시, 간장 | 기타 생선(고등어 외), 대두, 밀 | 간장(대두·밀)과 가쓰오부시(생선) 기반 |
| `tteokbokki_rice_cake` | 떡볶이떡 |  | 밀가루(가능), 쌀(가능) | 밀(가능) | 밀떡·쌀떡을 한 재료로 묶어 밀 possible. 별도 재료로 나눌지 검수 |
| `tuna_extract` | 참치액 |  | 가다랑어, 간장(가능) | 기타 생선(고등어 외), 대두(가능), 밀(가능) | 가다랑어 추출물 기반. 간장 혼합 여부 제품별 상이 |
| `webfoot_octopus` | 주꾸미 | 해산물 |  | 기타 연체류(문어·낙지·주꾸미) | 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수) |
| `wine` | 와인 |  | 아황산염, 포도 | 아황산류 | 대부분의 와인에 아황산류가 들어감(무첨가 제품도 발효 중 소량 생성된다고 알려짐). definite로 둠. 검수 |
| `young_radish_kimchi` | 열무김치 |  | 열무, 밀가루(가능), 새우젓(가능), 액젓(가능) | 기타 생선(고등어 외)(가능), 밀(가능), 새우(가능) | 풀(밀가루 또는 찹쌀풀)을 쑤어 넣는 경우가 많아 밀 possible |
| `zucchini` | 애호박 |  |  | - | 주키니와 애호박은 품종이 다르나 요리에서 대체로 같이 씀. 별칭으로 둘지 검수 |

### 2. 나머지 — 185개 (카테고리별)

#### 육류 (23)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `beef` | 쇠고기 | 육류 |  | 쇠고기 |  |
| `beef_brisket` | 차돌박이 | 쇠고기 |  | 쇠고기 |  |
| `beef_bulgogi_cut` | 불고기용 소고기 | 쇠고기 |  | 쇠고기 |  |
| `beef_short_ribs` | 소갈비 | 쇠고기 |  | 쇠고기 |  |
| `beef_sirloin` | 소고기 등심 | 쇠고기 |  | 쇠고기 |  |
| `beef_soup_cut` | 국거리 소고기 | 쇠고기 |  | 쇠고기 |  |
| `beef_tenderloin` | 소고기 안심 | 쇠고기 |  | 쇠고기 |  |
| `chicken` | 닭고기 | 육류 |  | 닭고기 |  |
| `chicken_breast` | 닭가슴살 | 닭고기 |  | 닭고기 |  |
| `chicken_thigh` | 닭다리살 | 닭고기 |  | 닭고기 |  |
| `chicken_wing` | 닭날개 | 닭고기 |  | 닭고기 |  |
| `duck` | 오리고기 | 육류 |  | - | 가금류 고기. 알류(가금류) 알레르기는 알에만 해당하므로 그룹 없음 |
| `ground_beef` | 소고기 다짐육 | 쇠고기 |  | 쇠고기 |  |
| `ground_pork` | 돼지고기 다짐육 | 돼지고기 |  | 돼지고기 |  |
| `lamb` | 양고기 | 육류 |  | - |  |
| `meat` | 육류 |  |  | 닭고기(가능), 돼지고기(가능), 쇠고기(가능) | [분류 노드] |
| `pork` | 돼지고기 | 육류 |  | 돼지고기 |  |
| `pork_belly` | 삼겹살 | 돼지고기 |  | 돼지고기 |  |
| `pork_loin` | 돼지고기 등심 | 돼지고기 |  | 돼지고기 |  |
| `pork_neck` | 돼지고기 목살 | 돼지고기 |  | 돼지고기 |  |
| `pork_ribs` | 돼지갈비 | 돼지고기 |  | 돼지고기 |  |
| `pork_shoulder` | 돼지고기 앞다리살 | 돼지고기 |  | 돼지고기 |  |
| `pork_tenderloin` | 돼지고기 안심 | 돼지고기 |  | 돼지고기 |  |

#### 육가공품 (2)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `bacon` | 베이컨 |  | 삼겹살 | 돼지고기 |  |
| `smoked_duck` | 훈제오리 |  | 오리고기 | - |  |

#### 해산물 (13)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `abalone` | 전복 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `clam` | 조개 | 해산물 |  | 조개류(굴·전복·홍합 포함) |  |
| `cockle` | 꼬막 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `crab` | 게 | 해산물 |  | 게 |  |
| `dried_shrimp` | 건새우 |  | 새우 | 새우 |  |
| `dried_squid` | 오징어채 |  | 오징어 | 오징어 |  |
| `hard_clam` | 모시조개 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `manila_clam` | 바지락 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `marsh_clam` | 재첩 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `mussel` | 홍합 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `oyster` | 굴 | 조개 |  | 조개류(굴·전복·홍합 포함) |  |
| `seafood` | 해산물 |  |  | 게(가능), 고등어(가능), 기타 생선(고등어 외)(가능), 기타 연체류(문어·낙지·주꾸미)(가능), 새우(가능), 오징어(가능), 조개류(굴·전복·홍합 포함)(가능) | [분류 노드] |
| `shrimp_raw` | 새우 | 해산물 |  | 새우 |  |

#### 생선 (17)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `anchovy` | 멸치 | 생선 |  | 기타 생선(고등어 외) |  |
| `canned_mackerel` | 고등어통조림 |  | 고등어 | 고등어 |  |
| `canned_saury` | 꽁치통조림 |  | 꽁치 | 기타 생선(고등어 외) |  |
| `cod` | 대구 | 생선 |  | 기타 생선(고등어 외) |  |
| `dried_pollock` | 황태 |  | 명태 | 기타 생선(고등어 외) |  |
| `fish` | 생선 | 해산물 |  | 고등어(가능), 기타 생선(고등어 외)(가능) | [분류 노드] |
| `flatfish` | 가자미 | 생선 |  | 기타 생선(고등어 외) |  |
| `gulbi` | 굴비 |  | 조기 | 기타 생선(고등어 외) |  |
| `hairtail` | 갈치 | 생선 |  | 기타 생선(고등어 외) |  |
| `katsuobushi` | 가쓰오부시 |  | 가다랑어 | 기타 생선(고등어 외) |  |
| `mackerel` | 고등어 | 생선 |  | 고등어 |  |
| `salmon` | 연어 | 생선 |  | 기타 생선(고등어 외) |  |
| `salted_mackerel` | 자반고등어 |  | 고등어 | 고등어 |  |
| `sand_lance` | 까나리 | 생선 |  | 기타 생선(고등어 외) |  |
| `skipjack` | 가다랑어 | 생선 |  | 기타 생선(고등어 외) |  |
| `tuna` | 참치 | 생선 |  | 기타 생선(고등어 외) |  |
| `yellow_croaker` | 조기 | 생선 |  | 기타 생선(고등어 외) |  |

#### 젓갈 (9)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `anchovy_fish_sauce` | 멸치액젓 | 액젓 | 멸치 | 기타 생선(고등어 외) |  |
| `eorigul_jeot` | 어리굴젓 | 젓갈류 | 굴 | 조개류(굴·전복·홍합 포함) |  |
| `jeotgal` | 젓갈류 | 해산물 |  | 기타 생선(고등어 외)(가능), 새우(가능), 오징어(가능), 조개류(굴·전복·홍합 포함)(가능) |  |
| `jogae_jeot` | 조개젓 | 젓갈류 | 조개 | 조개류(굴·전복·홍합 포함) |  |
| `myeolchijeot` | 멸치젓 | 젓갈류 | 멸치 | 기타 생선(고등어 외) |  |
| `myeongnanjeot` | 명란젓 | 젓갈류 | 명태 | 기타 생선(고등어 외) |  |
| `ojingeojeot` | 오징어젓 | 젓갈류 | 오징어 | 오징어 |  |
| `saeujeot` | 새우젓 | 젓갈류 | 새우 | 새우 |  |
| `sand_lance_fish_sauce` | 까나리액젓 | 액젓 | 까나리 | 기타 생선(고등어 외) |  |

#### 해조류 (3)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `kelp` | 다시마 |  |  | - |  |
| `laver` | 김 |  |  | - |  |
| `seaweed` | 미역 |  |  | - |  |

#### 채소 (38)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `asparagus` | 아스파라거스 |  |  | - |  |
| `bell_pepper` | 파프리카 |  |  | - |  |
| `bellflower_root` | 도라지 |  |  | - |  |
| `bok_choy` | 청경채 |  |  | - |  |
| `bracken` | 고사리 |  |  | - |  |
| `broccoli` | 브로콜리 |  |  | - |  |
| `burdock` | 우엉 |  |  | - |  |
| `cabbage` | 양배추 |  |  | - |  |
| `canned_corn` | 스위트콘 |  | 옥수수 | - |  |
| `carrot` | 당근 |  |  | - |  |
| `celery` | 셀러리 |  |  | - |  |
| `cheongyang_pepper` | 청양고추 |  |  | - |  |
| `cherry_tomato` | 방울토마토 | 토마토 |  | 토마토 |  |
| `chive` | 부추 |  |  | - |  |
| `corn` | 옥수수 |  |  | - |  |
| `crown_daisy` | 쑥갓 |  |  | - |  |
| `cucumber` | 오이 |  |  | - |  |
| `eggplant` | 가지 |  |  | - |  |
| `garlic` | 마늘 |  |  | - | [기본 양념] |
| `ginger` | 생강 |  |  | - |  |
| `green_bell_pepper` | 피망 |  |  | - |  |
| `green_onion` | 대파 |  |  | - |  |
| `iceberg_lettuce` | 양상추 |  |  | - |  |
| `kabocha` | 단호박 |  |  | - |  |
| `lettuce` | 상추 |  |  | - |  |
| `lotus_root` | 연근 |  |  | - |  |
| `minari` | 미나리 |  |  | - |  |
| `mung_bean_sprouts` | 숙주 |  |  | - | 녹두 싹. 대두 아님 |
| `onion` | 양파 |  |  | - |  |
| `perilla_leaf` | 깻잎 |  |  | - | 들깨의 잎. 참깨 알레르기 그룹과 무관 |
| `potato` | 감자 |  |  | - |  |
| `radish` | 무 |  |  | - |  |
| `red_chili` | 홍고추 |  |  | - |  |
| `scallion` | 쪽파 |  |  | - |  |
| `spinach` | 시금치 |  |  | - |  |
| `sweet_potato` | 고구마 |  |  | - |  |
| `tomato` | 토마토 |  |  | 토마토 |  |
| `young_radish` | 열무 |  |  | - |  |

#### 버섯 (5)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `button_mushroom` | 양송이버섯 |  |  | - |  |
| `enoki` | 팽이버섯 |  |  | - |  |
| `king_oyster_mushroom` | 새송이버섯 |  |  | - |  |
| `oyster_mushroom` | 느타리버섯 |  |  | - |  |
| `shiitake` | 표고버섯 |  |  | - |  |

#### 과일 (12)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `apple` | 사과 |  |  | - |  |
| `banana` | 바나나 |  |  | - |  |
| `canned_peach` | 복숭아통조림 |  | 복숭아 | 복숭아 |  |
| `grape` | 포도 |  |  | - |  |
| `jujube` | 대추 |  |  | - |  |
| `kiwi` | 키위 |  |  | - |  |
| `maesil` | 매실 |  |  | - |  |
| `orange` | 오렌지 |  |  | - |  |
| `peach` | 복숭아 |  |  | 복숭아 |  |
| `pear` | 배 |  |  | - |  |
| `persimmon` | 감 |  |  | - |  |
| `strawberry` | 딸기 |  |  | - |  |

#### 견과·씨앗 (7)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `peanut` | 땅콩 |  |  | 땅콩 |  |
| `peanut_butter` | 땅콩버터 |  | 땅콩 | 땅콩 |  |
| `perilla_powder` | 들깨가루 |  | 들깨 | - |  |
| `perilla_seed` | 들깨 |  |  | - | 들깨는 참깨와 다른 식물. 참깨 그룹에 넣지 않음 |
| `pine_nut` | 잣 |  |  | 잣 |  |
| `sesame` | 참깨 |  |  | 참깨 | 별칭 "깨"는 참깨·들깨를 모두 가리킬 수 있어 뺌 |
| `walnut` | 호두 |  |  | 호두 |  |

#### 곡류·가루 (9)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `brown_rice` | 현미 |  |  | - |  |
| `buckwheat` | 메밀 |  |  | 메밀 |  |
| `corn_starch` | 옥수수전분 |  | 옥수수 | - |  |
| `glutinous_rice` | 찹쌀 |  |  | - |  |
| `glutinous_rice_flour` | 찹쌀가루 |  | 찹쌀 | - |  |
| `potato_starch` | 감자전분 |  | 감자 | - | 별칭 "전분"·"녹말"은 감자·옥수수·고구마 중 무엇인지 모호해 뺌 |
| `rice` | 쌀 |  |  | - |  |
| `rice_flour` | 쌀가루 |  | 쌀 | - |  |
| `wheat_flour` | 밀가루 |  |  | 밀 |  |

#### 면·떡·빵 (6)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `dumpling_wrapper` | 만두피 |  | 밀가루 | 밀 |  |
| `kalguksu_noodles` | 칼국수면 |  | 밀가루 | 밀 |  |
| `rice_cake` | 가래떡 |  | 쌀 | - |  |
| `rice_noodles` | 쌀국수면 |  | 쌀 | - |  |
| `somen` | 소면 |  | 밀가루 | 밀 |  |
| `udon_noodles` | 우동면 |  | 밀가루 | 밀 |  |

#### 콩·두부 (7)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `black_soybean` | 검은콩 | 대두 |  | 대두 | 검정콩은 대두의 한 품종이라 is_a로 대두 알레르기 상속 |
| `fried_tofu` | 유부 |  | 두부 | 대두 |  |
| `red_bean` | 팥 |  |  | - | 팥은 대두가 아님 |
| `soft_tofu` | 순두부 | 두부 | 대두 | 대두 | 1차 레시피 확장(순두부찌개)용으로 추가. 2026-10-04 is_a tofu 결정(두부 절대 불선호가 순두부에도 적용되도록). 검수 필요 |
| `soy_milk` | 두유 |  | 대두 | 대두 |  |
| `soybean` | 대두 |  |  | 대두 |  |
| `tofu` | 두부 |  | 대두 | 대두 | 2026-10-04 별칭 '순두부'를 soft_tofu로 옮김(이름 중복 방지) |

#### 알 (2)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `egg` | 계란 |  |  | 알류(가금류) |  |
| `quail_egg` | 메추리알 |  |  | 알류(가금류) |  |

#### 유제품 (8)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `butter` | 버터 |  | 우유 | 우유 |  |
| `cheese` | 치즈 |  | 우유 | 우유 |  |
| `cream_cheese` | 크림치즈 | 치즈 |  | 우유 |  |
| `milk` | 우유 |  |  | 우유 |  |
| `mozzarella` | 모차렐라치즈 | 치즈 |  | 우유 |  |
| `parmesan` | 파마산치즈 | 치즈 |  | 우유 |  |
| `sliced_cheese` | 슬라이스치즈 | 치즈 |  | 우유 |  |
| `yogurt` | 요거트 |  | 우유 | 우유 |  |

#### 양념 (5)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `gochugaru` | 고춧가루 |  |  | - | [기본 양념] |
| `honey` | 꿀 |  |  | - |  |
| `oligosaccharide` | 올리고당 |  |  | - | [기본 양념] |
| `sugar` | 설탕 |  |  | - | [기본 양념] |
| `vinegar` | 식초 |  |  | - | [기본 양념] |

#### 장류 (1)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `cheonggukjang` | 청국장 |  | 대두 | 대두 |  |

#### 소스 (5)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `ketchup` | 토마토케첩 |  | 토마토 | 토마토 |  |
| `mayonnaise` | 마요네즈 |  | 계란, 콩기름(가능) | 알류(가금류), 대두(가능) |  |
| `mustard` | 머스터드 |  |  | - |  |
| `tomato_paste` | 토마토페이스트 |  | 토마토 | 토마토 |  |
| `wasabi` | 와사비 |  |  | - |  |

#### 기름 (4)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `chili_oil` | 고추기름 |  | 고춧가루, 식용유 | - |  |
| `olive_oil` | 올리브유 |  |  | - |  |
| `perilla_oil` | 들기름 |  | 들깨 | - |  |
| `sesame_oil` | 참기름 |  | 참깨 | 참깨 | [기본 양념] |

#### 허브·향신료 (6)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `basil` | 바질 |  |  | - |  |
| `bay_leaf` | 월계수잎 |  |  | - |  |
| `black_pepper` | 후추 |  |  | - | [기본 양념] |
| `cinnamon` | 계피 |  |  | - |  |
| `mustard_powder` | 겨자 |  |  | - |  |
| `parsley` | 파슬리 |  |  | - |  |

#### 육수·조미료 (1)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `anchovy_stock` | 멸치육수 |  | 멸치, 다시마(가능) | 기타 생선(고등어 외) |  |

#### 첨가물 (1)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `sulfite` | 아황산염 |  |  | 아황산류 | 레시피 재료로 직접 쓰지 않음. 와인·건과일 등의 derived_from 원천으로만 사용 |

#### 가공식품 (1)

| id | 이름 | 상위 개념 | 파생 원천 | 걸리는 알레르기(상속 포함) | 메모 |
|---|---|---|---|---|---|
| `pickled_cucumber` | 피클 |  | 오이 | - |  |

### 부록: 알레르기 그룹

| id | 이름 | 종류 | 법정 | 재료 수(상속 포함) |
|---|---|---|---|---|
| `beef` | 쇠고기 | 기본 | 예 | 16 |
| `buckwheat` | 메밀 | 기본 | 예 | 4 |
| `chicken` | 닭고기 | 기본 | 예 | 11 |
| `crab` | 게 | 기본 | 예 | 3 |
| `crustacean_bundle` | 갑각류 | 묶음 | 아니오 | 11 |
| `egg` | 알류(가금류) | 기본 | 예 | 11 |
| `fish_bundle` | 생선 전체 | 묶음 | 아니오 | 37 |
| `mackerel` | 고등어 | 기본 | 예 | 7 |
| `milk` | 우유 | 기본 | 예 | 19 |
| `nuts_bundle` | 견과류 | 묶음 | 아니오 | 6 |
| `other_cephalopods` | 기타 연체류(문어·낙지·주꾸미) | 기본 | 아니오 | 4 |
| `other_fish` | 기타 생선(고등어 외) | 기본 | 아니오 | 34 |
| `other_tree_nuts` | 기타 견과류(아몬드·밤 등) | 기본 | 아니오 | 2 |
| `peach` | 복숭아 | 기본 | 예 | 2 |
| `peanut` | 땅콩 | 기본 | 예 | 2 |
| `pine_nut` | 잣 | 기본 | 예 | 1 |
| `pork` | 돼지고기 | 기본 | 예 | 15 |
| `seafood_bundle` | 해산물 전체 | 묶음 | 아니오 | 59 |
| `sesame` | 참깨 | 기본 | 아니오 | 4 |
| `shellfish` | 조개류(굴·전복·홍합 포함) | 기본 | 예 | 17 |
| `shrimp` | 새우 | 기본 | 예 | 9 |
| `soybean` | 대두 | 기본 | 예 | 36 |
| `squid` | 오징어 | 기본 | 예 | 5 |
| `sulfites` | 아황산류 | 기본 | 예 | 6 |
| `tomato` | 토마토 | 기본 | 예 | 7 |
| `walnut` | 호두 | 기본 | 예 | 1 |
| `wheat` | 밀 | 기본 | 예 | 39 |

# B. knowledge/allergens.yaml

```yaml
# 알레르기 그룹 (형식: knowledge/README.md). docs/decisions.md D4에서 사람이 확정(2026-10-03).
#
# official: true / source: law_annex2
#   법정 알레르기 유발물질 표시 대상. 근거: 식품 등의 표시·광고에 관한 법률 시행규칙 별표 2.
#   목록은 사람이 확정했다. 법령이 바뀌면 사람이 확인해 이 파일을 고친다.
# official: false / source: custom
#   서비스가 자체로 추가한 그룹(법정 표시 대상 아님). 제품 성분표에 표시되지 않을 수 있다.
#
# 기본 그룹(groups): 재료의 allergens에는 기본 그룹만 쓴다.
# 묶음 그룹(bundles): 사용자가 고르기 쉬운 단위. includes에는 기본 그룹만 쓴다(묶음 안의 묶음은 펼쳐서 적는다).

groups:
  # --- 법정 표시 대상 19개 ---
  - id: egg
    display_name: 알류(가금류)
    official: true
    source: law_annex2
    status: reviewed
  - id: milk
    display_name: 우유
    official: true
    source: law_annex2
    status: reviewed
  - id: buckwheat
    display_name: 메밀
    official: true
    source: law_annex2
    status: reviewed
  - id: peanut
    display_name: 땅콩
    official: true
    source: law_annex2
    status: reviewed
  - id: soybean
    display_name: 대두
    official: true
    source: law_annex2
    status: reviewed
  - id: wheat
    display_name: 밀
    official: true
    source: law_annex2
    status: reviewed
  - id: mackerel
    display_name: 고등어
    official: true
    source: law_annex2
    status: reviewed
  - id: crab
    display_name: 게
    official: true
    source: law_annex2
    status: reviewed
  - id: shrimp
    display_name: 새우
    official: true
    source: law_annex2
    status: reviewed
  - id: pork
    display_name: 돼지고기
    official: true
    source: law_annex2
    status: reviewed
  - id: peach
    display_name: 복숭아
    official: true
    source: law_annex2
    status: reviewed
  - id: tomato
    display_name: 토마토
    official: true
    source: law_annex2
    status: reviewed
  - id: sulfites
    display_name: 아황산류
    official: true
    source: law_annex2
    status: reviewed
  - id: walnut
    display_name: 호두
    official: true
    source: law_annex2
    status: reviewed
  - id: chicken
    display_name: 닭고기
    official: true
    source: law_annex2
    status: reviewed
  - id: beef
    display_name: 쇠고기
    official: true
    source: law_annex2
    status: reviewed
  - id: squid
    display_name: 오징어
    official: true
    source: law_annex2
    status: reviewed
  - id: shellfish
    display_name: 조개류(굴·전복·홍합 포함)
    official: true
    source: law_annex2
    status: reviewed
  - id: pine_nut
    display_name: 잣
    official: true
    source: law_annex2
    status: reviewed

  # --- 자체 추가(비공식) ---
  - id: other_fish
    display_name: 기타 생선(고등어 외)
    official: false
    source: custom
    status: reviewed
  - id: sesame
    display_name: 참깨
    official: false
    source: custom
    status: reviewed
  - id: other_cephalopods
    display_name: 기타 연체류(문어·낙지·주꾸미)
    official: false
    source: custom
    status: reviewed
    note: 오징어(법정)와 별도. 0-4 검수에서 추가
  - id: other_tree_nuts
    display_name: 기타 견과류(아몬드·밤 등)
    official: false
    source: custom
    status: reviewed
    note: 땅콩·호두·잣(법정) 외 견과. 0-4 검수에서 추가

bundles:
  - id: crustacean_bundle
    display_name: 갑각류
    includes: [shrimp, crab]
    official: false
    source: custom
    status: reviewed
  - id: nuts_bundle
    display_name: 견과류
    includes: [peanut, walnut, pine_nut, other_tree_nuts]
    official: false
    source: custom
    status: reviewed
    note: 땅콩은 식물학적으로 콩과지만 사용자 인식상 함께 피하는 경우가 많아 포함. 아몬드·밤 등은 기타 견과류로 포함
  - id: fish_bundle
    display_name: 생선 전체
    includes: [mackerel, other_fish]
    official: false
    source: custom
    status: reviewed
  - id: seafood_bundle
    display_name: 해산물 전체
    # 갑각류(shrimp, crab) + 오징어 + 기타 연체류 + 조개류 + 생선 전체(mackerel, other_fish)
    includes: [shrimp, crab, squid, other_cephalopods, shellfish, mackerel, other_fish]
    official: false
    source: custom
    status: reviewed
```

# C. knowledge/ingredients/*.yaml (원본, 별칭 포함)

## knowledge/ingredients/dairy_egg_soy.yaml

```yaml
# 알·유제품·콩 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft

# --- 알 (법정: 알류(가금류)) ---
- id: egg
  name: 계란
  aliases: [달걀, 계란 노른자, 계란 흰자, 유정란]
  category: 알
  allergens: [{group: egg, certainty: definite}]
  status: reviewed
- id: quail_egg
  name: 메추리알
  aliases: [깐 메추리알]
  category: 알
  allergens: [{group: egg, certainty: definite}]
  status: reviewed

# --- 유제품 ---
- id: milk
  name: 우유
  aliases: [흰우유, 저지방우유]
  category: 유제품
  allergens: [{group: milk, certainty: definite}]
  status: reviewed
- id: butter
  name: 버터
  aliases: [무염버터, 가염버터]
  derived_from: [milk]
  is_processed: true
  category: 유제품
  status: reviewed
- id: heavy_cream
  name: 생크림
  aliases: [휘핑크림, 동물성 생크림]
  derived_from: [milk]
  is_processed: true
  category: 유제품
  confidence: low
  note: 식물성 휘핑크림(유지방 아님)은 우유 성분이 없거나 적을 수 있음. 휘핑크림을 별칭으로 둘지 검수
  status: reviewed
- id: yogurt
  name: 요거트
  aliases: [플레인요거트, 요구르트, 그릭요거트]
  derived_from: [milk]
  is_processed: true
  category: 유제품
  status: reviewed
- id: cheese
  name: 치즈
  derived_from: [milk]
  is_processed: true
  category: 유제품
  status: reviewed
- id: mozzarella
  name: 모차렐라치즈
  aliases: [모짜렐라치즈, 모짜렐라, 피자치즈]
  is_a: [cheese]
  category: 유제품
  status: reviewed
- id: sliced_cheese
  name: 슬라이스치즈
  aliases: [체다치즈, 체다 슬라이스]
  is_a: [cheese]
  category: 유제품
  status: reviewed
- id: parmesan
  name: 파마산치즈
  aliases: [파르메산, 파르미지아노 레지아노, 파마산 가루]
  is_a: [cheese]
  category: 유제품
  status: reviewed
- id: cream_cheese
  name: 크림치즈
  is_a: [cheese]
  category: 유제품
  status: reviewed

# --- 콩·두부 (법정: 대두) ---
- id: soybean
  name: 대두
  aliases: [메주콩, 백태, 노란콩]
  category: 콩·두부
  allergens: [{group: soybean, certainty: definite}]
  status: reviewed
- id: black_soybean
  name: 검은콩
  aliases: [서리태, 쥐눈이콩, 서목태]
  is_a: [soybean]
  category: 콩·두부
  note: 검정콩은 대두의 한 품종이라 is_a로 대두 알레르기 상속
  status: reviewed
- id: tofu
  name: 두부
  aliases: [부침두부, 찌개두부, 연두부]
  derived_from: [soybean]
  is_processed: true
  category: 콩·두부
  note: 2026-10-04 별칭 '순두부'를 soft_tofu로 옮김(이름 중복 방지)
  status: reviewed
- id: soft_tofu
  name: 순두부
  aliases: [찌개용 순두부]
  is_a: [tofu]
  derived_from: [soybean]
  is_processed: true
  category: 콩·두부
  note: 1차 레시피 확장(순두부찌개)용으로 추가. 2026-10-04 is_a tofu 결정(두부 절대 불선호가 순두부에도 적용되도록). 검수 필요
  status: draft
- id: fried_tofu
  name: 유부
  aliases: [유부초밥용 유부, 사각유부]
  derived_from: [tofu]
  is_processed: true
  category: 콩·두부
  status: reviewed
- id: soy_milk
  name: 두유
  aliases: [무가당 두유]
  derived_from: [soybean]
  is_processed: true
  category: 콩·두부
  status: reviewed
- id: red_bean
  name: 팥
  aliases: [적두, 통팥]
  category: 콩·두부
  note: 팥은 대두가 아님
  status: reviewed
```

## knowledge/ingredients/fruits_nuts.yaml

```yaml
# 과일·견과·씨앗 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft

# --- 과일 ---
- id: apple
  name: 사과
  category: 과일
  status: reviewed
- id: pear
  name: 배
  aliases: [배(과일), 신고배]
  category: 과일
  status: reviewed
- id: lemon
  name: 레몬
  aliases: [{text: 레몬즙, form: juice}]
  category: 과일
  confidence: low
  note: 시판 레몬즙에 아황산류가 들어가는 제품이 있는지 검수(있으면 별도 가공품으로 분리)
  status: reviewed
- id: banana
  name: 바나나
  category: 과일
  status: reviewed
- id: strawberry
  name: 딸기
  category: 과일
  status: reviewed
- id: grape
  name: 포도
  aliases: [청포도, 샤인머스캣]
  category: 과일
  status: reviewed
- id: persimmon
  name: 감
  aliases: [단감, 홍시]
  category: 과일
  status: reviewed
- id: kiwi
  name: 키위
  aliases: [참다래]
  category: 과일
  status: reviewed
- id: orange
  name: 오렌지
  category: 과일
  status: reviewed
- id: peach
  name: 복숭아
  aliases: [백도, 황도, 천도복숭아]
  category: 과일
  allergens: [{group: peach, certainty: definite}]
  status: reviewed
- id: canned_peach
  name: 복숭아통조림
  aliases: [황도 통조림]
  derived_from: [peach]
  is_processed: true
  category: 과일
  status: reviewed
- id: maesil
  name: 매실
  aliases: [청매실]
  category: 과일
  status: reviewed
- id: jujube
  name: 대추
  aliases: [건대추]
  category: 과일
  status: reviewed

# --- 건과일 (아황산류: 표백·보존용으로 쓰는 제품이 있어 possible) ---
- id: raisin
  name: 건포도
  derived_from: [grape, {id: sulfite, certainty: possible}]
  is_processed: true
  category: 과일
  confidence: low
  note: 아황산류 첨가 여부는 제품별 상이
  status: reviewed
- id: dried_persimmon
  name: 곶감
  aliases: [반건시]
  derived_from: [persimmon, {id: sulfite, certainty: possible}]
  is_processed: true
  category: 과일
  confidence: low
  note: 갈변 방지용 아황산류 처리 제품이 있음. 제품별 상이
  status: reviewed
- id: dried_apricot
  name: 건살구
  derived_from: [{id: sulfite, certainty: possible}]
  is_processed: true
  category: 과일
  confidence: low
  note: 살구 원물은 재료로 두지 않음. 아황산류 처리 제품이 흔하다고 알려져 있으나 확인 필요
  status: reviewed

# --- 견과 (법정: 땅콩, 호두, 잣) ---
- id: peanut
  name: 땅콩
  aliases: [볶은 땅콩, 땅콩가루, 피넛]
  category: 견과·씨앗
  allergens: [{group: peanut, certainty: definite}]
  status: reviewed
- id: peanut_butter
  name: 땅콩버터
  aliases: [피넛버터]
  derived_from: [peanut]
  is_processed: true
  category: 견과·씨앗
  status: reviewed
- id: walnut
  name: 호두
  aliases: [호두살, 호두알]
  category: 견과·씨앗
  allergens: [{group: walnut, certainty: definite}]
  status: reviewed
- id: pine_nut
  name: 잣
  aliases: [통잣, 잣가루]
  category: 견과·씨앗
  allergens: [{group: pine_nut, certainty: definite}]
  status: reviewed
- id: almond
  name: 아몬드
  aliases: [슬라이스 아몬드, 아몬드 슬라이스]
  category: 견과·씨앗
  allergens: [{group: other_tree_nuts, certainty: definite}]
  confidence: low
  note: 법정 표시 대상이 아니어서 자체 그룹 기타 견과류에 둠(0-4 검수)
  status: reviewed
- id: chestnut
  name: 밤
  aliases: [깐밤, 생밤]
  category: 견과·씨앗
  allergens: [{group: other_tree_nuts, certainty: possible}]
  confidence: low
  note: 밤을 견과 알레르기로 볼지 사람마다 달라 기타 견과류 possible(0-4 검수)
  status: reviewed

# --- 씨앗 (참깨는 자체 그룹 sesame) ---
- id: sesame
  name: 참깨
  aliases: [통깨, 볶은 참깨, 깨소금, 흰깨]
  category: 견과·씨앗
  allergens: [{group: sesame, certainty: definite}]
  note: 별칭 "깨"는 참깨·들깨를 모두 가리킬 수 있어 뺌
  status: reviewed
- id: perilla_seed
  name: 들깨
  aliases: [통들깨]
  category: 견과·씨앗
  note: 들깨는 참깨와 다른 식물. 참깨 그룹에 넣지 않음
  status: reviewed
- id: perilla_powder
  name: 들깨가루
  aliases: [들깻가루]
  derived_from: [perilla_seed]
  is_processed: true
  category: 견과·씨앗
  status: reviewed
```

## knowledge/ingredients/grains.yaml

```yaml
# 곡류·가루·면·떡·빵 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft

# --- 곡류 ---
- id: rice
  name: 쌀
  aliases: [백미, 멥쌀, {text: 밥, form: cooked}, {text: 쌀밥, form: cooked}, {text: 흰밥, form: cooked}]
  category: 곡류·가루
  status: reviewed
- id: glutinous_rice
  name: 찹쌀
  category: 곡류·가루
  status: reviewed
- id: brown_rice
  name: 현미
  aliases: [{text: 현미밥, form: cooked}]
  category: 곡류·가루
  status: reviewed
- id: buckwheat
  name: 메밀
  aliases: [메밀쌀]
  category: 곡류·가루
  allergens: [{group: buckwheat, certainty: definite}]
  status: reviewed

# --- 가루·전분 ---
- id: wheat_flour
  name: 밀가루
  aliases: [중력분, 박력분, 강력분, 통밀가루]
  category: 곡류·가루
  allergens: [{group: wheat, certainty: definite}]
  status: reviewed
- id: rice_flour
  name: 쌀가루
  aliases: [습식 쌀가루, 건식 쌀가루]
  derived_from: [rice]
  is_processed: true
  category: 곡류·가루
  status: reviewed
- id: glutinous_rice_flour
  name: 찹쌀가루
  derived_from: [glutinous_rice]
  is_processed: true
  category: 곡류·가루
  status: reviewed
- id: buckwheat_flour
  name: 메밀가루
  derived_from: [buckwheat, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 곡류·가루
  confidence: low
  note: 밀가루를 섞은 제품이 있음
  status: reviewed
- id: buchimgaru
  name: 부침가루
  derived_from:
    - wheat_flour
    - {id: soybean, certainty: possible}
    - {id: egg, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 곡류·가루
  confidence: low
  note: 밀가루 주원료. 대두분·난분·탈지분유 첨가 여부는 제품별 상이
  status: reviewed
- id: frying_mix
  name: 튀김가루
  derived_from:
    - wheat_flour
    - {id: soybean, certainty: possible}
    - {id: egg, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 곡류·가루
  confidence: low
  note: 부침가루와 같은 이유
  status: reviewed
- id: bread_crumbs
  name: 빵가루
  aliases: [습식 빵가루, 건식 빵가루]
  derived_from:
    - wheat_flour
    - {id: milk, certainty: possible}
    - {id: egg, certainty: possible}
    - {id: soybean, certainty: possible}
  is_processed: true
  category: 곡류·가루
  confidence: low
  note: 빵을 갈아 만듦. 우유·계란·대두 함유 여부는 제품별 상이
  status: reviewed
- id: potato_starch
  name: 감자전분
  aliases: [감자녹말]
  derived_from: [potato]
  is_processed: true
  category: 곡류·가루
  note: 별칭 "전분"·"녹말"은 감자·옥수수·고구마 중 무엇인지 모호해 뺌
  status: reviewed
- id: corn_starch
  name: 옥수수전분
  aliases: [옥수수녹말, 콘스타치]
  derived_from: [corn]
  is_processed: true
  category: 곡류·가루
  status: reviewed

# --- 면 ---
- id: somen
  name: 소면
  aliases: [중면, 국수면]
  derived_from: [wheat_flour]
  is_processed: true
  category: 면·떡·빵
  status: reviewed
- id: kalguksu_noodles
  name: 칼국수면
  aliases: [칼국수 생면]
  derived_from: [wheat_flour]
  is_processed: true
  category: 면·떡·빵
  status: reviewed
- id: udon_noodles
  name: 우동면
  aliases: [우동사리]
  derived_from: [wheat_flour]
  is_processed: true
  category: 면·떡·빵
  status: reviewed
- id: ramen_noodles
  name: 라면
  aliases: [라면사리, 인스턴트라면]
  derived_from:
    - wheat_flour
    - {id: soybean, certainty: possible}
    - {id: beef, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 면은 밀. 스프(분말)의 대두·쇠고기·우유 등은 제품별 상이. 사리만 쓰는 경우와 구분할지 검수
  status: reviewed
- id: pasta
  name: 파스타
  aliases: [스파게티, 스파게티면, 펜네, 링귀니]
  derived_from: [wheat_flour, {id: egg, certainty: possible}]
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 듀럼밀(밀). 생면·에그파스타는 계란 포함
  status: reviewed
- id: buckwheat_noodles
  name: 메밀면
  aliases: [메밀국수, 소바, 소바면]
  derived_from: [buckwheat, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 대부분 밀가루를 섞음. 밀 possible
  status: reviewed
- id: naengmyeon_noodles
  name: 냉면사리
  aliases: [냉면 면, 냉면사리면]
  derived_from:
    - {id: buckwheat, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - {id: potato_starch, certainty: possible}
    - {id: sweet_potato, certainty: possible}
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 물냉면(메밀·밀)·비빔냉면(전분) 등 제품별 원료 상이
  status: reviewed
- id: glass_noodles
  name: 당면
  derived_from: [sweet_potato]
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 고구마전분 당면 기준. 다른 전분을 쓰는 제품도 있음
  status: reviewed
- id: rice_noodles
  name: 쌀국수면
  aliases: [라이스누들]
  derived_from: [rice]
  is_processed: true
  category: 면·떡·빵
  status: reviewed

# --- 떡·빵·피 ---
- id: rice_cake
  name: 가래떡
  aliases: [{text: 떡국떡, form: sliced}]
  derived_from: [rice]
  is_processed: true
  category: 면·떡·빵
  status: reviewed
- id: tteokbokki_rice_cake
  name: 떡볶이떡
  aliases: [밀떡, 쌀떡]
  derived_from: [{id: rice, certainty: possible}, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 밀떡·쌀떡을 한 재료로 묶어 밀 possible. 별도 재료로 나눌지 검수
  status: reviewed
- id: bread
  name: 식빵
  aliases: [우유식빵, 통밀식빵]
  derived_from:
    - wheat_flour
    - {id: milk, certainty: possible}
    - {id: egg, certainty: possible}
    - {id: soybean, certainty: possible}
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 우유·계란·대두 함유 여부는 제품별 상이
  status: reviewed
- id: dumpling_wrapper
  name: 만두피
  derived_from: [wheat_flour]
  is_processed: true
  category: 면·떡·빵
  status: reviewed
- id: tortilla
  name: 또띠아
  aliases: [토르티야]
  derived_from: [wheat_flour, {id: corn, certainty: possible}]
  is_processed: true
  category: 면·떡·빵
  confidence: low
  note: 밀 또띠아 기준. 옥수수 또띠아도 있음
  status: reviewed
```

## knowledge/ingredients/kimchi_processed.yaml

```yaml
# 김치·절임·기타 가공식품 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft
# 육가공품은 meat.yaml, 어묵·게맛살은 seafood.yaml에 있다.

- id: kimchi
  name: 배추김치
  aliases: [김치, 묵은지, 포기김치, 신김치]
  derived_from:
    - napa_cabbage
    - {id: saeujeot, certainty: possible}
    - {id: fish_sauce, certainty: possible}
    - {id: oyster, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - gochugaru
  is_processed: true
  category: 김치
  confidence: low
  note: 젓갈 종류·포함 여부가 제품별로 다름. 새우젓·액젓(멸치·까나리 등 생선)·굴 possible. 밀가루풀을 쑤는 제품이 있어 밀 possible
  status: reviewed
- id: kkakdugi
  name: 깍두기
  derived_from:
    - radish
    - {id: saeujeot, certainty: possible}
    - {id: fish_sauce, certainty: possible}
    - {id: oyster, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - gochugaru
  is_processed: true
  category: 김치
  confidence: low
  note: 배추김치와 같은 이유
  status: reviewed
- id: young_radish_kimchi
  name: 열무김치
  derived_from:
    - young_radish
    - {id: saeujeot, certainty: possible}
    - {id: fish_sauce, certainty: possible}
    - {id: wheat_flour, certainty: possible}
  is_processed: true
  category: 김치
  confidence: low
  note: 풀(밀가루 또는 찹쌀풀)을 쑤어 넣는 경우가 많아 밀 possible
  status: reviewed
- id: pickled_radish
  name: 단무지
  aliases: [김밥 단무지]
  derived_from: [radish]
  is_processed: true
  category: 가공식품
  confidence: low
  note: 보존료·표백제(아황산류) 사용 여부 확인 필요
  status: reviewed
- id: pickled_cucumber
  name: 피클
  aliases: [오이피클]
  derived_from: [cucumber]
  is_processed: true
  category: 가공식품
  status: reviewed
```

## knowledge/ingredients/meat.yaml

```yaml
# 육류·육가공품 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft
# 돼지고기·쇠고기·닭고기 알레르기는 중간 노드(pork, beef, chicken)에만 적고, 부위는 is_a로 상속한다.

- id: meat
  name: 육류
  kind: concept
  category: 육류
  status: reviewed

# --- 돼지고기 ---
- id: pork
  name: 돼지고기
  aliases: [돈육]
  is_a: [meat]
  category: 육류
  allergens: [{group: pork, certainty: definite}]
  status: reviewed
- id: pork_belly
  name: 삼겹살
  aliases: [통삼겹, 대패삼겹살, 오겹살]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: pork_neck
  name: 돼지고기 목살
  aliases: [목살]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: pork_shoulder
  name: 돼지고기 앞다리살
  aliases: [앞다리살, 돼지 앞다리]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: pork_loin
  name: 돼지고기 등심
  aliases: [돈등심, 돼지등심]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: pork_tenderloin
  name: 돼지고기 안심
  aliases: [돈안심, 돼지안심]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: pork_ribs
  name: 돼지갈비
  aliases: [돼지등갈비, 등갈비]
  is_a: [pork]
  category: 육류
  status: reviewed
- id: ground_pork
  name: 돼지고기 다짐육
  aliases: [다진 돼지고기, 돼지 다짐육, 돼지고기 간 것]
  is_a: [pork]
  category: 육류
  status: reviewed

# --- 쇠고기 ---
- id: beef
  name: 쇠고기
  aliases: [소고기, 우육]
  is_a: [meat]
  category: 육류
  allergens: [{group: beef, certainty: definite}]
  status: reviewed
- id: beef_brisket
  name: 차돌박이
  aliases: [차돌]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_bulgogi_cut
  name: 불고기용 소고기
  aliases: [불고기감, 소불고기감]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_soup_cut
  name: 국거리 소고기
  aliases: [소고기 국거리, 양지, 양지머리]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_sirloin
  name: 소고기 등심
  aliases: [소등심, 꽃등심]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_tenderloin
  name: 소고기 안심
  aliases: [소안심]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: ground_beef
  name: 소고기 다짐육
  aliases: [다진 소고기, 소 다짐육]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_short_ribs
  name: 소갈비
  aliases: [LA갈비, 찜갈비]
  is_a: [beef]
  category: 육류
  status: reviewed
- id: beef_bone
  name: 사골
  aliases: [소 사골, 우족]
  is_a: [beef]
  category: 육류
  confidence: low
  note: 우족(소 발)을 사골의 별칭으로 묶어도 되는지 검수
  status: reviewed

# --- 닭고기·가금류 ---
- id: chicken
  name: 닭고기
  aliases: [닭, 생닭, 닭 한 마리]
  is_a: [meat]
  category: 육류
  allergens: [{group: chicken, certainty: definite}]
  status: reviewed
- id: chicken_breast
  name: 닭가슴살
  is_a: [chicken]
  category: 육류
  status: reviewed
- id: chicken_thigh
  name: 닭다리살
  aliases: [닭다리, 닭 정육, 닭다리 정육]
  is_a: [chicken]
  category: 육류
  status: reviewed
- id: chicken_wing
  name: 닭날개
  aliases: [닭봉, 닭윙]
  is_a: [chicken]
  category: 육류
  status: reviewed
- id: duck
  name: 오리고기
  aliases: [오리]
  is_a: [meat]
  category: 육류
  note: 가금류 고기. 알류(가금류) 알레르기는 알에만 해당하므로 그룹 없음
  status: reviewed
- id: lamb
  name: 양고기
  aliases: [램, 양갈비]
  is_a: [meat]
  category: 육류
  status: reviewed

# --- 육가공품 (제품마다 성분이 달라 대부분 possible, confidence: low) ---
- id: bacon
  name: 베이컨
  derived_from: [pork_belly]
  is_processed: true
  category: 육가공품
  status: reviewed
- id: ham
  name: 햄
  aliases: [슬라이스햄, 김밥햄, 샌드위치햄]
  derived_from:
    - pork
    - {id: chicken, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 육가공품
  confidence: low
  note: 돼지고기 햄 기준. 닭고기 혼합, 대두단백·밀·유청 첨가 제품이 있어 possible
  status: reviewed
- id: sausage
  name: 소시지
  aliases: [비엔나소시지, 프랑크소시지, 후랑크소시지]
  derived_from:
    - {id: pork, certainty: possible}
    - {id: chicken, certainty: possible}
    - {id: beef, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 육가공품
  confidence: low
  note: 원료육이 제품마다 다름(돼지·닭·소 혼합). 모두 possible
  status: reviewed
- id: luncheon_meat
  name: 통조림햄
  aliases: [런천미트, 캔햄]
  derived_from:
    - pork
    - {id: chicken, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: wheat_flour, certainty: possible}
  is_processed: true
  category: 육가공품
  confidence: low
  note: 돼지고기 주원료. 닭고기 혼합·대두단백·전분(밀 가능) 제품 있음
  status: reviewed
- id: smoked_duck
  name: 훈제오리
  derived_from: [duck]
  is_processed: true
  category: 육가공품
  status: reviewed
- id: frozen_dumplings
  name: 냉동만두
  aliases: [만두, 고기만두, 김치만두]
  derived_from:
    - wheat_flour
    - {id: pork, certainty: possible}
    - {id: beef, certainty: possible}
    - {id: chicken, certainty: possible}
    - {id: tofu, certainty: possible}
    - {id: kimchi, certainty: possible}
    - {id: egg, certainty: possible}
  is_processed: true
  category: 가공식품
  confidence: low
  note: 만두피는 밀. 소는 제품마다 다름(고기·두부·김치·새우 등). 새우만두는 별도 재료로 두지 않음
  status: reviewed
```

## knowledge/ingredients/seafood.yaml

```yaml
# 해산물·생선·젓갈·해조류 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft
# 법정 그룹: 고등어(mackerel), 게, 새우, 오징어, 조개류. 고등어 외 생선은 자체 그룹 other_fish.

- id: seafood
  name: 해산물
  kind: concept
  category: 해산물
  status: reviewed
- id: fish
  name: 생선
  kind: concept
  is_a: [seafood]
  category: 생선
  status: reviewed

# --- 생선: 고등어(법정) ---
- id: mackerel
  name: 고등어
  aliases: [생고등어]
  is_a: [fish]
  category: 생선
  allergens: [{group: mackerel, certainty: definite}]
  status: reviewed
- id: salted_mackerel
  name: 자반고등어
  aliases: [간고등어, 고등어자반]
  derived_from: [mackerel]
  is_processed: true
  category: 생선
  status: reviewed
- id: canned_mackerel
  name: 고등어통조림
  aliases: [고등어캔]
  derived_from: [mackerel]
  is_processed: true
  category: 생선
  status: reviewed

# --- 생선: 기타(자체 그룹 other_fish) ---
- id: spanish_mackerel
  name: 삼치
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  confidence: low
  note: 삼치는 고등어과지만 법정 표시 대상 '고등어'와 다른 어종으로 보고 기타 생선에 둠. 고등어 그룹에도 넣을지 검수
  status: reviewed
- id: pacific_saury
  name: 꽁치
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  confidence: low
  note: 꽁치는 고등어과가 아님(꽁치과)으로 알고 있으나 확인 필요
  status: reviewed
- id: canned_saury
  name: 꽁치통조림
  aliases: [꽁치캔]
  derived_from: [pacific_saury]
  is_processed: true
  category: 생선
  status: reviewed
- id: hairtail
  name: 갈치
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: yellow_croaker
  name: 조기
  aliases: [참조기]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: gulbi
  name: 굴비
  derived_from: [yellow_croaker]
  is_processed: true
  category: 생선
  status: reviewed
- id: pollock
  name: 명태
  aliases: [동태, 생태, 코다리]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  confidence: low
  note: 코다리(반건조 명태)를 별칭으로 묶음. 별도 가공품으로 둘지 검수
  status: reviewed
- id: dried_pollock
  name: 황태
  aliases: [북어, 황태채, 북어채]
  derived_from: [pollock]
  is_processed: true
  category: 생선
  status: reviewed
- id: cod
  name: 대구
  aliases: [대구살, 생대구]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: flatfish
  name: 가자미
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: salmon
  name: 연어
  aliases: [생연어]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: tuna
  name: 참치
  aliases: [참치회, 다랑어]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: canned_tuna
  name: 참치캔
  aliases: [참치통조림, 통조림참치]
  derived_from: [tuna, {id: soybean_oil, certainty: possible}]
  is_processed: true
  category: 생선
  confidence: low
  note: 기름담금 제품은 대두유 사용이 많음(정제유의 대두 처리 기준은 soybean_oil 검수에 따름)
  status: reviewed
- id: skipjack
  name: 가다랑어
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: katsuobushi
  name: 가쓰오부시
  aliases: [가다랑어포, 가츠오부시]
  derived_from: [skipjack]
  is_processed: true
  category: 생선
  status: reviewed
- id: anchovy
  name: 멸치
  aliases: [국물용 멸치, 다시멸치, 볶음용 멸치, {text: 잔멸치, form: small}]
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed
- id: sand_lance
  name: 까나리
  is_a: [fish]
  category: 생선
  allergens: [{group: other_fish, certainty: definite}]
  status: reviewed

# --- 생선 가공품 ---
- id: fish_cake
  name: 어묵
  aliases: [오뎅, 사각어묵, 부산어묵, 어묵탕용 어묵]
  derived_from:
    - fish
    - {id: wheat_flour, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: egg, certainty: possible}
  is_processed: true
  category: 가공식품
  confidence: low
  note: 어종이 제품마다 달라 '생선'(분류 노드)에서 파생 → 모든 생선 그룹 possible. 밀가루·전분·대두단백 첨가 제품 많음
  status: reviewed
- id: imitation_crab
  name: 게맛살
  aliases: [맛살, 게살맛살]
  derived_from:
    - fish
    - {id: crab, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - {id: egg, certainty: possible}
    - {id: soybean, certainty: possible}
  is_processed: true
  category: 가공식품
  confidence: low
  note: 연육(생선살)이 주원료. 게 추출물·밀·난백·대두 함유 제품 있음
  status: reviewed

# --- 갑각류 ---
- id: shrimp_raw
  name: 새우
  aliases: [대하, 칵테일새우, 새우살, 흰다리새우, 냉동새우]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: shrimp, certainty: definite}]
  status: reviewed
- id: dried_shrimp
  name: 건새우
  aliases: [마른 새우, 보리새우]
  derived_from: [shrimp_raw]
  is_processed: true
  category: 해산물
  status: reviewed
- id: crab
  name: 게
  aliases: [꽃게, 대게, 홍게, 게살]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: crab, certainty: definite}]
  status: reviewed

# --- 연체류 ---
- id: squid
  name: 오징어
  aliases: [생물 오징어, 한치]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: squid, certainty: definite}]
  confidence: low
  note: 한치(오징어류)를 별칭으로 묶음. 법정 '오징어'에 한치가 포함되는지 검수
  status: reviewed
- id: dried_squid
  name: 오징어채
  aliases: [진미채, 오징어 진미채, 마른오징어]
  derived_from: [squid]
  is_processed: true
  category: 해산물
  status: reviewed
- id: small_octopus
  name: 낙지
  is_a: [seafood]
  category: 해산물
  confidence: low
  allergens: [{group: other_cephalopods, certainty: definite}]
  note: 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수)
  status: reviewed
- id: octopus
  name: 문어
  aliases: [자숙문어]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: other_cephalopods, certainty: definite}]
  confidence: low
  note: 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수)
  status: reviewed
- id: webfoot_octopus
  name: 주꾸미
  aliases: [쭈꾸미]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: other_cephalopods, certainty: definite}]
  confidence: low
  note: 오징어(법정)가 아니라 자체 그룹 기타 연체류에 둠(0-4 검수)
  status: reviewed

# --- 조개류(법정: 굴·전복·홍합 포함). 알레르기는 중간 노드 clam에만 적고 하위는 is_a로 상속 ---
- id: clam
  name: 조개
  aliases: [조개류, 조갯살]
  is_a: [seafood]
  category: 해산물
  allergens: [{group: shellfish, certainty: definite}]
  status: reviewed
- id: manila_clam
  name: 바지락
  aliases: [바지락살]
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: hard_clam
  name: 모시조개
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: cockle
  name: 꼬막
  aliases: [새꼬막, 참꼬막]
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: scallop
  name: 가리비
  aliases: [가리비살, 관자]
  is_a: [clam]
  category: 해산물
  confidence: low
  note: 관자는 키조개 관자일 수도 있으나 둘 다 조개류라 알레르기 판정은 같음
  status: reviewed
- id: mussel
  name: 홍합
  aliases: [섭, 홍합살]
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: oyster
  name: 굴
  aliases: [생굴, 석화]
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: abalone
  name: 전복
  is_a: [clam]
  category: 해산물
  status: reviewed
- id: marsh_clam
  name: 재첩
  is_a: [clam]
  category: 해산물
  status: reviewed

# --- 젓갈 ---
- id: jeotgal
  name: 젓갈류
  aliases: [젓갈]
  is_a: [seafood]
  category: 젓갈
  status: reviewed
- id: saeujeot
  name: 새우젓
  aliases: [새우젓갈, 육젓, 추젓]
  is_a: [jeotgal]
  derived_from: [shrimp_raw]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: myeongnanjeot
  name: 명란젓
  aliases: [명란, 백명란]
  is_a: [jeotgal]
  derived_from: [pollock]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: ojingeojeot
  name: 오징어젓
  aliases: [오징어젓갈]
  is_a: [jeotgal]
  derived_from: [squid]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: myeolchijeot
  name: 멸치젓
  aliases: [멸치젓갈]
  is_a: [jeotgal]
  derived_from: [anchovy]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: eorigul_jeot
  name: 어리굴젓
  aliases: [굴젓]
  is_a: [jeotgal]
  derived_from: [oyster]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: jogae_jeot
  name: 조개젓
  aliases: [조개젓갈, 바지락젓]
  is_a: [jeotgal]
  derived_from: [clam]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: fish_sauce
  name: 액젓
  aliases: [피시소스]
  is_a: [jeotgal]
  category: 젓갈
  confidence: low
  note: 원료 어종을 모르는 넓은 재료. 하위(멸치액젓·까나리액젓)의 알레르기를 possible로 가짐. 피시소스(동남아)를 별칭으로 묶어도 되는지 검수
  status: reviewed
- id: anchovy_fish_sauce
  name: 멸치액젓
  is_a: [fish_sauce]
  derived_from: [anchovy]
  is_processed: true
  category: 젓갈
  status: reviewed
- id: sand_lance_fish_sauce
  name: 까나리액젓
  is_a: [fish_sauce]
  derived_from: [sand_lance]
  is_processed: true
  category: 젓갈
  status: reviewed

# --- 해조류 ---
- id: laver
  name: 김
  aliases: [김밥김, 생김, 구운김]
  category: 해조류
  status: reviewed
- id: seasoned_laver
  name: 조미김
  aliases: [맛김, 도시락김]
  derived_from: [laver, {id: sesame_oil, certainty: possible}, {id: perilla_oil, certainty: possible}]
  is_processed: true
  category: 해조류
  confidence: low
  note: 참기름·들기름·식용유 중 무엇을 쓰는지 제품마다 다름
  status: reviewed
- id: seaweed
  name: 미역
  aliases: [건미역, 자른미역]
  category: 해조류
  status: reviewed
- id: kelp
  name: 다시마
  aliases: [국물용 다시마]
  category: 해조류
  status: reviewed

# --- 육수 ---
- id: anchovy_stock
  name: 멸치육수
  aliases: [멸치다시마육수, 멸치 다시물]
  derived_from: [anchovy, {id: kelp, certainty: possible}]
  is_processed: true
  category: 육수·조미료
  status: reviewed
```

## knowledge/ingredients/seasonings.yaml

```yaml
# 양념·장류·소스·기름·향신료·주류·첨가물 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft
# 기본 양념 여부는 config/pantry_staples.yaml이 정한다(여기 적지 않음).

# --- 기본 양념 ---
- id: salt
  name: 소금
  aliases: [굵은소금, 꽃소금, 천일염, 맛소금]
  category: 양념
  confidence: low
  note: 맛소금은 MSG가 섞인 제품. 알레르기 성분은 없다고 보고 별칭으로 둠
  status: reviewed
- id: sugar
  name: 설탕
  aliases: [백설탕, 황설탕, 흑설탕]
  category: 양념
  status: reviewed
- id: black_pepper
  name: 후추
  aliases: [후춧가루, 통후추, 흑후추]
  category: 허브·향신료
  status: reviewed
- id: gochugaru
  name: 고춧가루
  aliases: [고운 고춧가루, 굵은 고춧가루]
  category: 양념
  status: reviewed
- id: vinegar
  name: 식초
  aliases: [양조식초, 사과식초, 현미식초]
  category: 양념
  status: reviewed
- id: honey
  name: 꿀
  aliases: [벌꿀]
  category: 양념
  status: reviewed
- id: oligosaccharide
  name: 올리고당
  category: 양념
  status: reviewed
- id: corn_syrup
  name: 물엿
  aliases: [조청]
  category: 양념
  confidence: low
  note: 조청(쌀 등을 고아 만든 것)과 물엿(전분당)은 원료가 다름. 별칭으로 둘지 검수
  status: reviewed

# --- 기름 ---
- id: cooking_oil
  name: 식용유
  aliases: [카놀라유, 포도씨유, 해바라기유, 옥수수유]
  category: 기름
  confidence: low
  note: 콩기름(대두유)은 별도 재료 soybean_oil. '식용유'가 콩기름일 수 있는 문제(대두 알레르기)는 검수 필요
  status: reviewed
- id: soybean_oil
  name: 콩기름
  aliases: [대두유]
  category: 기름
  derived_from: [{id: soybean, certainty: possible}]
  is_processed: true
  confidence: low
  note: 정제유의 대두 알레르기 처리 기준은 사람이 판단. 식용유(cooking_oil)와의 is_a 관계는 두지 않음
  status: reviewed
- id: sesame_oil
  name: 참기름
  derived_from: [sesame]
  is_processed: true
  category: 기름
  status: reviewed
- id: perilla_oil
  name: 들기름
  derived_from: [perilla_seed]
  is_processed: true
  category: 기름
  status: reviewed
- id: olive_oil
  name: 올리브유
  aliases: [올리브오일, 엑스트라버진 올리브유]
  category: 기름
  status: reviewed
- id: chili_oil
  name: 고추기름
  aliases: [라유]
  derived_from: [gochugaru, cooking_oil]
  is_processed: true
  category: 기름
  status: reviewed

# --- 장류 ---
- id: soy_sauce
  name: 간장
  aliases: [진간장, 국간장, 양조간장, 조선간장]
  derived_from: [soybean, wheat_flour]
  is_processed: true
  category: 장류
  confidence: low
  note: 국간장(조선간장)은 밀이 없는 제품이 많으나 보수적으로 밀 definite. 국간장을 별도 재료로 나눌지 검수
  status: reviewed
- id: doenjang
  name: 된장
  aliases: [재래식 된장, 시판 된장]
  derived_from: [soybean, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 장류
  confidence: low
  note: 밀 포함 여부는 제품별 상이
  status: reviewed
- id: gochujang
  name: 고추장
  derived_from: [soybean, {id: wheat_flour, certainty: possible}, gochugaru]
  is_processed: true
  category: 장류
  confidence: low
  note: 밀 포함 여부는 제품별 상이(밀 고추장 많음). 포함 가능으로 처리
  status: reviewed
- id: ssamjang
  name: 쌈장
  derived_from: [doenjang, gochujang, {id: sesame_oil, certainty: possible}]
  is_processed: true
  category: 장류
  confidence: low
  note: 된장·고추장 기반. 참기름·참깨 첨가 제품이 많아 possible
  status: reviewed
- id: cheonggukjang
  name: 청국장
  derived_from: [soybean]
  is_processed: true
  category: 장류
  status: reviewed
- id: chunjang
  name: 춘장
  aliases: [짜장 소스용 춘장]
  derived_from: [soybean, wheat_flour]
  is_processed: true
  category: 장류
  confidence: low
  note: 대두·밀이 주원료인 제품 기준
  status: reviewed
- id: doubanjiang
  name: 두반장
  derived_from: [{id: soybean, certainty: possible}, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 장류
  confidence: low
  note: 잠두(누에콩)가 주원료. 대두·밀 첨가는 제품별 상이
  status: reviewed
- id: miso
  name: 미소된장
  aliases: [미소, 일본된장]
  derived_from: [soybean, {id: wheat_flour, certainty: possible}]
  is_processed: true
  category: 장류
  confidence: low
  note: 보리·쌀 누룩 사용. 밀 사용 제품 있음
  status: reviewed

# --- 소스 ---
- id: oyster_sauce
  name: 굴소스
  aliases: [오이스터소스]
  derived_from: [oyster, {id: wheat_flour, certainty: possible}, {id: soybean, certainty: possible}]
  is_processed: true
  category: 소스
  confidence: low
  note: 굴 추출물 주원료. 밀가루·전분·간장 첨가 제품 있음
  status: reviewed
- id: mayonnaise
  name: 마요네즈
  aliases: [마요]
  derived_from: [egg, {id: soybean_oil, certainty: possible}]
  is_processed: true
  category: 소스
  status: reviewed
- id: ketchup
  name: 토마토케첩
  aliases: [케첩, 케찹]
  derived_from: [tomato]
  is_processed: true
  category: 소스
  status: reviewed
- id: tomato_sauce
  name: 토마토소스
  aliases: [토마토 파스타소스, 마리나라소스]
  derived_from: [tomato, {id: milk, certainty: possible}, {id: cheese, certainty: possible}]
  is_processed: true
  category: 소스
  confidence: low
  note: 치즈·크림 첨가 제품 있음
  status: reviewed
- id: tomato_paste
  name: 토마토페이스트
  derived_from: [tomato]
  is_processed: true
  category: 소스
  status: reviewed
- id: mustard
  name: 머스터드
  aliases: [디종 머스터드, 홀그레인 머스터드, 양겨자]
  category: 소스
  status: reviewed
- id: wasabi
  name: 와사비
  aliases: [고추냉이]
  category: 소스
  status: reviewed
- id: tonkatsu_sauce
  name: 돈가스소스
  aliases: [돈까스소스]
  derived_from:
    - {id: wheat_flour, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: tomato, certainty: possible}
    - {id: sulfite, certainty: possible}
  is_processed: true
  category: 소스
  confidence: low
  note: 채소·과일 퓨레, 간장, 토마토, 전분 등 제품별 상이
  status: reviewed
- id: curry_powder
  name: 카레가루
  aliases: [카레, 카레분말, 고형카레, 카레 루]
  derived_from:
    - wheat_flour
    - {id: milk, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: beef, certainty: possible}
    - {id: pork, certainty: possible}
    - {id: chicken, certainty: possible}
    - {id: tomato, certainty: possible}
  is_processed: true
  category: 소스
  confidence: low
  note: 국내 즉석 카레가루 기준 밀 definite. 향신료만 섞은 커리파우더는 밀이 없을 수 있음(별도 재료로 나눌지 검수). 유청·육류 추출물 등은 제품별 상이
  status: reviewed
- id: tsuyu
  name: 쯔유
  aliases: [가쓰오 쯔유, 메밀소스]
  derived_from: [soy_sauce, katsuobushi]
  is_processed: true
  category: 소스
  confidence: low
  note: 간장(대두·밀)과 가쓰오부시(생선) 기반
  status: reviewed
- id: tuna_extract
  name: 참치액
  derived_from: [skipjack, {id: soy_sauce, certainty: possible}]
  is_processed: true
  category: 소스
  confidence: low
  note: 가다랑어 추출물 기반. 간장 혼합 여부 제품별 상이
  status: reviewed

# --- 육수·조미료 ---
- id: beef_bone_broth
  name: 사골육수
  aliases: [사골국물, 사골곰탕 육수]
  derived_from: [beef_bone]
  is_processed: true
  category: 육수·조미료
  confidence: low
  note: 시판 제품은 우유·대두 등 첨가가 있는지 확인 필요
  status: reviewed
- id: chicken_stock
  name: 치킨스톡
  aliases: [치킨스톡 큐브, 닭육수]
  derived_from:
    - chicken
    - {id: wheat_flour, certainty: possible}
    - {id: soybean, certainty: possible}
    - {id: milk, certainty: possible}
  is_processed: true
  category: 육수·조미료
  confidence: low
  note: 고형·분말 제품은 밀·대두·유당 첨가가 흔함
  status: reviewed
- id: beef_seasoning
  name: 쇠고기 맛 조미료
  aliases: [쇠고기 조미료, 소고기 조미료]
  derived_from:
    - {id: beef, certainty: possible}
    - {id: wheat_flour, certainty: possible}
    - {id: soybean, certainty: possible}
  is_processed: true
  category: 육수·조미료
  confidence: low
  note: 쇠고기 추출물 함량이 낮거나 없는 제품도 있음. 밀·대두 제품별 상이
  status: reviewed

# --- 허브·향신료 ---
- id: basil
  name: 바질
  aliases: [바질잎, 건바질]
  category: 허브·향신료
  status: reviewed
- id: parsley
  name: 파슬리
  aliases: [파슬리가루, 건파슬리]
  category: 허브·향신료
  status: reviewed
- id: bay_leaf
  name: 월계수잎
  aliases: [로리에]
  category: 허브·향신료
  status: reviewed
- id: cinnamon
  name: 계피
  aliases: [시나몬, 계피가루, 시나몬파우더]
  category: 허브·향신료
  status: reviewed
- id: mustard_powder
  name: 겨자
  aliases: [겨잣가루, 연겨자]
  category: 허브·향신료
  status: reviewed

# --- 주류 (아황산류) ---
- id: wine
  name: 와인
  aliases: [레드와인, 화이트와인, 포도주, 요리용 와인]
  derived_from: [grape, sulfite]
  is_processed: true
  category: 주류
  confidence: low
  note: 대부분의 와인에 아황산류가 들어감(무첨가 제품도 발효 중 소량 생성된다고 알려짐). definite로 둠. 검수
  status: reviewed
- id: mirin
  name: 맛술
  aliases: [미림, 미향]
  derived_from: [rice]
  is_processed: true
  category: 주류
  confidence: low
  note: 쌀 발효 조미술. 아황산류 첨가 여부 확인 필요
  status: reviewed
- id: cheongju
  name: 청주
  aliases: [요리술, 정종]
  derived_from: [rice]
  is_processed: true
  category: 주류
  confidence: low
  note: 맛술과 같은 이유로 확인 필요
  status: reviewed

# --- 첨가물 ---
- id: sulfite
  name: 아황산염
  aliases: [아황산나트륨, 메타중아황산칼륨, 무수아황산]
  category: 첨가물
  allergens: [{group: sulfites, certainty: definite}]
  note: 레시피 재료로 직접 쓰지 않음. 와인·건과일 등의 derived_from 원천으로만 사용
  status: reviewed
```

## knowledge/ingredients/vegetables.yaml

```yaml
# 채소·버섯 (형식: knowledge/README.md). 모든 항목은 사람이 검수하기 전까지 status: draft

# --- 파·마늘·양념 채소 ---
- id: green_onion
  name: 대파
  aliases: [대파 흰대]
  category: 채소
  status: reviewed
- id: scallion
  name: 쪽파
  aliases: [실파]
  category: 채소
  status: reviewed
- id: garlic
  name: 마늘
  aliases: [깐마늘, 통마늘, {text: 다진 마늘, form: minced}, {text: 편마늘, form: sliced}]
  category: 채소
  status: reviewed
- id: onion
  name: 양파
  aliases: [적양파, 자색양파]
  category: 채소
  status: reviewed
- id: chive
  name: 부추
  aliases: [영양부추, 정구지]
  category: 채소
  status: reviewed
- id: ginger
  name: 생강
  aliases: [{text: 다진 생강, form: minced}]
  category: 채소
  status: reviewed
- id: green_chili
  name: 풋고추
  aliases: [청고추, 오이고추, 꽈리고추]
  category: 채소
  confidence: low
  note: 오이고추·꽈리고추는 품종이 다르고 맵기도 다름. 별도 재료로 나눌지 검수
  status: reviewed
- id: cheongyang_pepper
  name: 청양고추
  category: 채소
  status: reviewed
- id: red_chili
  name: 홍고추
  aliases: [빨간 고추, 홍청양고추]
  category: 채소
  status: reviewed

# --- 뿌리·줄기 채소 ---
- id: potato
  name: 감자
  aliases: [햇감자, 알감자]
  category: 채소
  status: reviewed
- id: sweet_potato
  name: 고구마
  aliases: [밤고구마, 호박고구마]
  category: 채소
  status: reviewed
- id: carrot
  name: 당근
  category: 채소
  status: reviewed
- id: radish
  name: 무
  aliases: [무우, 조선무, 월동무]
  category: 채소
  status: reviewed
- id: young_radish
  name: 열무
  category: 채소
  status: reviewed
- id: lotus_root
  name: 연근
  category: 채소
  status: reviewed
- id: burdock
  name: 우엉
  category: 채소
  status: reviewed
- id: bellflower_root
  name: 도라지
  category: 채소
  status: reviewed

# --- 잎채소 ---
- id: napa_cabbage
  name: 배추
  aliases: [알배추, 알배기배추, 절임배추]
  category: 채소
  confidence: low
  note: 절임배추(소금 절임)를 별칭으로 묶음. 별도 재료로 둘지 검수
  status: reviewed
- id: cabbage
  name: 양배추
  aliases: [적양배추]
  category: 채소
  status: reviewed
- id: spinach
  name: 시금치
  aliases: [섬초]
  category: 채소
  status: reviewed
- id: perilla_leaf
  name: 깻잎
  aliases: [들깻잎]
  category: 채소
  note: 들깨의 잎. 참깨 알레르기 그룹과 무관
  status: reviewed
- id: lettuce
  name: 상추
  aliases: [청상추, 적상추]
  category: 채소
  status: reviewed
- id: iceberg_lettuce
  name: 양상추
  category: 채소
  status: reviewed
- id: minari
  name: 미나리
  category: 채소
  status: reviewed
- id: crown_daisy
  name: 쑥갓
  category: 채소
  status: reviewed
- id: bok_choy
  name: 청경채
  category: 채소
  status: reviewed
- id: bracken
  name: 고사리
  aliases: [삶은 고사리, 건고사리]
  category: 채소
  status: reviewed
- id: celery
  name: 셀러리
  aliases: [샐러리]
  category: 채소
  status: reviewed

# --- 열매채소 ---
- id: zucchini
  name: 애호박
  aliases: [호박(애호박), 주키니]
  category: 채소
  confidence: low
  note: 주키니와 애호박은 품종이 다르나 요리에서 대체로 같이 씀. 별칭으로 둘지 검수
  status: reviewed
- id: kabocha
  name: 단호박
  category: 채소
  status: reviewed
- id: cucumber
  name: 오이
  aliases: [백오이, 다다기오이]
  category: 채소
  status: reviewed
- id: eggplant
  name: 가지
  category: 채소
  status: reviewed
- id: bell_pepper
  name: 파프리카
  aliases: [빨간 파프리카, 노란 파프리카]
  category: 채소
  status: reviewed
- id: green_bell_pepper
  name: 피망
  category: 채소
  status: reviewed
- id: tomato
  name: 토마토
  aliases: [완숙토마토, 찰토마토]
  category: 채소
  allergens: [{group: tomato, certainty: definite}]
  status: reviewed
- id: cherry_tomato
  name: 방울토마토
  aliases: [대추방울토마토, 미니토마토]
  is_a: [tomato]
  category: 채소
  status: reviewed
- id: corn
  name: 옥수수
  aliases: [찰옥수수, 초당옥수수]
  category: 채소
  status: reviewed
- id: canned_corn
  name: 스위트콘
  aliases: [옥수수콘, 콘통조림]
  derived_from: [corn]
  is_processed: true
  category: 채소
  status: reviewed
- id: broccoli
  name: 브로콜리
  category: 채소
  status: reviewed
- id: asparagus
  name: 아스파라거스
  category: 채소
  status: reviewed

# --- 나물(콩 유래 포함) ---
- id: soybean_sprouts
  name: 콩나물
  derived_from: [soybean]
  category: 채소
  confidence: low
  note: 대두를 발아시킨 것. 대두 알레르기에서 제외 대상으로 볼지 검수(가공품이 아니라 is_processed는 두지 않음 → 컴파일 경고 1건)
  status: reviewed
- id: mung_bean_sprouts
  name: 숙주
  aliases: [숙주나물]
  category: 채소
  note: 녹두 싹. 대두 아님
  status: reviewed

# --- 버섯 ---
- id: shiitake
  name: 표고버섯
  aliases: [표고, {text: 건표고, form: dried}]
  category: 버섯
  status: reviewed
- id: oyster_mushroom
  name: 느타리버섯
  aliases: [느타리]
  category: 버섯
  status: reviewed
- id: enoki
  name: 팽이버섯
  aliases: [팽이]
  category: 버섯
  status: reviewed
- id: king_oyster_mushroom
  name: 새송이버섯
  aliases: [새송이]
  category: 버섯
  status: reviewed
- id: button_mushroom
  name: 양송이버섯
  aliases: [양송이]
  category: 버섯
  status: reviewed
```
