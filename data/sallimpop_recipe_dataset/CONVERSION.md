# 살림팝 데이터 변환 기록

> `scripts/convert_sallimpop.py`가 생성한다. 손으로 고치지 않는다.

원본 `recipes/sallimpop/*.yaml` 169개를 `data/recipes/<id>.yaml`(draft)로 변환했다. 원본 파일은 바꾸지 않는다.

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
| `aesuni_ojingeogug_b1h_t` | 애순이 오징어국 | 재료 이름 '고운 고춧가루로' → gochugaru(이름 보정표) |
| `agwisuyug_enhnd6` | 아귀수육 | 재료 이름 '두꼬집 진간장' → soy_sauce(이름 보정표) |
| `bab_3gonggi_ddugddag_halsu_issneun_gamjacamcijjageuli_0_72mg` | 밥 3공기 뚝딱 할수 있는 감자참치짜글이 | 재료 이름 '감자 큰거' → potato(이름 보정표); 재료 이름 '고추장 1 크게' → gochujang(이름 보정표); 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `babdodug_sfrysi` | 밥도둑 | 재료 이름 '작은 양파' → onion(이름 보정표); 재료 이름 '색감을 위해 홍고추' → red_chili(이름 보정표) |
| `babdodug_sogogiyaggocujang_keoa8g` | 밥도둑 소고기약고추장 | 재료 이름 '마지막 꿀' → honey(이름 보정표); 재료 이름 '고기양과 동일하게 고추장' → gochujang(이름 보정표) |
| `babdodugingayo_1v9dh1` | 밥도둑인가요? | 재료 이름 '맛을 위해 청양고추' → cheongyang_pepper(이름 보정표) |
| `baecumalijeongol_tgix70` | 배추말이전골 | 재료 이름 '잘 씻은 숙주나물' → mung_bean_sprouts(이름 보정표) |
| `basasag_maneuldeunggalbi_apqst` | 바사삭 마늘등갈비 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `beikeonmaneul_weonpaenpaseuta_xahqx6` | 베이컨마늘 원팬파스타 | 재료 이름 '더하기 위해 페퍼론치노' → peperoncino(이름 보정표); 재료 줄 '시작하면 물 700ml' 뺌(물, 이름 보정표); 재료 이름 '졸아들면 올리브유' → olive_oil(이름 보정표) |
| `bomdongbibimbab_c0p8zj` | 봄동비빔밥 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `bomdongbibimbab_jiinzr` | 봄동비빔밥 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `buldalggyerandubutang_tzkjhp` | 불닭계란두부탕 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요) |
| `camcigimcijjigae_xp9x_l` | 참치김치찌개 | 재료 이름 '큰 감자' → potato(이름 보정표) |
| `coegang_babdodug_bmovfi` | 최강 밥도둑 | 재료 이름 '계란후라이에 다대기' → egg(이름 보정표) |
| `coehwajeongnim_yeondubuoisaelreodeu_nifdrv` | 최화정님 연두부오이샐러드 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `cogcoghago_saekomdalkomhan_bibimgugsu_lkgv_6` | 촉촉하고 새콤달콤한 비빔국수 | 재료 이름 '마지막 참기름' → sesame_oil(이름 보정표) |
| `cueogyi_osambulgogi_x7iwsb` | 추억의 오삼불고기 | 재료 이름 '이때 고추장' → gochujang(이름 보정표); 재료 이름 '마지막 킥 다진생강' → ginger(이름 보정표) |
| `daepaesamgyeob_paseuta_9xmglr` | 대패삼겹 파스타 | 재료 이름 '양파 숨이 죽으면 멸치액젓' → anchovy_fish_sauce(이름 보정표) |
| `daepaesamgyeobdeopbab_cakwdc` | 대패삼겹덮밥 | 재료 이름 '적당히 나오기 시작하면 대파' → green_onion(이름 보정표); 재료 이름 '잘게 찢은 느타리' → oyster_mushroom(이름 보정표); 재료 이름 '재료 잘 모아서 계란후라이' → egg(이름 보정표) |
| `dalggaseumsal_buldalgpaseuta_z52qn6` | 닭가슴살 불닭파스타 | 재료 이름 '양념은 불닭소스' → buldak_sauce(이름 보정표) |
| `ddeogboggi_tqauco` | 떡볶이 | 재료 이름 '굶은 소금' → salt(이름 보정표) |
| `deopbabeun_ireohge_hywuew` | 덮밥은 이렇게 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `deulgireumnaengpaseuta_ukvrse` | 들기름냉파스타 | 재료 이름 '한번에 파스타면' → pasta(이름 보정표) |
| `dwaejigomtang_iwotbj` | 돼지곰탕 | 재료 이름 '생강 작은 조각' → ginger(이름 보정표) |
| `eomugboggeum_zz9stm` | 어묵볶음 | 재료 이름 '올려주는 고추기름' → chili_oil(이름 보정표); 재료 이름 '맛을 올리기 위해 참기름' → sesame_oil(이름 보정표) |
| `euro_jjolmyeon_pcwmvr` | 으로 쫄면 | 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `gajideopbab_hzjm20` | 가지덮밥 | 재료 이름 '하시는 분은 고춧가루' → gochugaru(이름 보정표) |
| `gajigui_dtitg8` | 가지구이 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `ggeutpanwang_dubujorim_bcftjh` | 끝판왕 두부조림 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `ggeutpanwang_dwaejijjigae_d4odtt` | 끝판왕 돼지찌개 | 재료 이름 '돼지고기 앞다리살 찌개용' → pork_shoulder(이름 보정표); 재료 이름 '위해 청양고추' → cheongyang_pepper(이름 보정표) |
| `gguuuudeoghan_keurimpaseuta_y2lcm0` | 꾸우우우덕한 크림파스타 | 재료 이름 '토핑으로 사용할 쪽파' → scallion(이름 보정표) |
| `gimcibibimgugsu_uvpvro` | 김치비빔국수 | 재료 이름 '저는 대식가라 국수' → somen(이름 보정표); 재료 이름 '고소한 맛을 위해 참기름' → sesame_oil(이름 보정표) |
| `gimcijjim_0cqmc2` | 김치찜 | 재료 이름 '돼지갈비찜용' → pork_ribs(이름 보정표) |
| `golbaengibibimbab_e7jghk` | 골뱅이비빔밥 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `gugsu_scrwet` | 국수 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음); 재료 이름 '제일 중요한 시판 냉면육수' → naengmyeon_broth(이름 보정표) |
| `gyerandeopbab_i_fl6b` | 계란덮밥 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `gyeranoibibimbab_mh4ukp` | 계란오이비빔밥 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `hanpantang_pykubc` | 한판탕 | 재료 이름 '전분가루를 처음에' → starch(이름 보정표); 재료 이름 '돼지고기 탕수육용' → pork(이름 보정표) |
| `hanpantang_rsibjb` | 한판탕 | 재료 이름 '돼지고기 등심 카레용' → pork_loin(이름 보정표) |
| `hwanggeumbiyul_jeugseogddeogboggi_xfyulh` | 황금비율 즉석떡볶이 | 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `hwanggeumbiyul_kongnamulmucim_m3oiih` | 황금비율 콩나물무침 | 재료 이름 '대파 흰부분' → green_onion(이름 보정표); 재료 이름 '볼에 담고 대파' → green_onion(이름 보정표) |
| `ihanyinim_mareugeriddapija_2vpmvy` | 이하늬님 마르게리따피자 | 재료 이름 '위에 토마토소스' → tomato_sauce(이름 보정표) |
| `insaengdoenjangjjigae_oitk6c` | 인생된장찌개 | 재료 이름 '감자 작은거' → potato(이름 보정표); 재료 이름 '두르고 된장' → doenjang(이름 보정표) |
| `insaengganjanggugsu_bi0ceo` | 인생간장국수 | 재료 이름 '깨소금이 핵심이에요 영상에서는' → sesame(이름 보정표); 재료 이름 '소면을 삶는 동안 계란' → egg(이름 보정표); 재료 이름 '통깨를 갈아만든 깨소금' → sesame(이름 보정표) |
| `iyeonbogswepeunimyi_gogiboggeumbab_xt2zuu` | 이연복쉐프님의 고기볶음밥 | 재료 이름 '양념 필요없이 굴소스' → oyster_sauce(이름 보정표) |
| `jeonjareinjiro_suyug_4msdff` | 전자레인지로 수육 | 재료 이름 '통 수육' → pork(이름 보정표) |
| `jeontong_doenjangjjigae_aknwi9` | 전통 된장찌개 | 재료 이름 '앙파' → onion(이름 보정표); 재료 이름 '자른대파' → green_onion(이름 보정표); 재료 줄 '뚝배기에 물 400ml' 뺌(물, 이름 보정표); 재료 이름 '멸치육수가 없으니 코인육수' → instant_stock(이름 보정표) |
| `jeugseogddeogboggi_bkurly` | 즉석떡볶이 | 재료 이름 '고추장 크게' → gochujang(이름 보정표); 재료 줄 '올려주고 물 800ml' 뺌(물, 이름 보정표) |
| `jeyugboggeum_ha6w7e` | 제육볶음 | 재료 이름 '고추장 크게' → gochujang(이름 보정표); 재료 이름 '잡기위해 다진마늘' → garlic(이름 보정표) |
| `jeyugboggeum_ruecur` | 제육볶음 | 재료 이름 '양념으로 맛술' → mirin(이름 보정표) |
| `jinsim_coegoyi_dwaejigalbi_qrd7e0` | 진심 최고의 돼지갈비 | 재료 이름 '양파 작은거' → onion(이름 보정표) |
| `jjigae_z4ioaz` | 찌개 | 재료 줄 '이제 물 700ml' 뺌(물, 이름 보정표); 재료 이름 '이제 뚜껑열고 채썬 양파' → onion(이름 보정표); 재료 이름 '채썬 애호박' → zucchini(이름 보정표) |
| `kongnamulojingeojeon_q0wnxl` | 콩나물오징어전 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `koseuteuko_lagalbi_wax2w5` | 코스트코 LA갈비 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `koseuteukonaengdongojingeoreul_hwalyonghan_kongnamulgugbab_hwrloz` | 코스트코냉동오징어를 활용한 콩나물국밥 | 재료 줄 '2인 기준으로 물 1L' 뺌(물, 이름 보정표) |
| `mas_geongang_da_jabeul_su_issneun_dwaejigogisigeumcideopbab_yy3kjx` | 맛 건강 다 잡을 수 있는 돼지고기시금치덮밥 | 재료 이름 '죽으면 진간장' → soy_sauce(이름 보정표); 재료 이름 '가운데로 재료 잘 모아주고 계란' → egg(이름 보정표); 재료 이름 '맛을 위해 참기름' → sesame_oil(이름 보정표) |
| `mecurial_yangpa_kare_osfrbb` | 메추리알 양파 카레 | 재료 이름 '고형카레 큰거' → curry_powder(이름 보정표) |
| `musubun_suyug_nztd5m` | 무수분 수육 | 재료 이름 '양파 큰거' → onion(이름 보정표) |
| `nogjinhan_dwaejigimcijjigae_ntkd3f` | 녹진한 돼지김치찌개 | 재료 이름 '김치 밥공기' → kimchi(이름 보정표) |
| `nuguna_mandeul_su_issneun_weonpaenkeurimpaseuta_pbgzbp` | 누구나 만들 수 있는 원팬크림파스타 | 재료 이름 '동전크기' → pasta(이름 보정표) |
| `ojingeo_deumbbug_neoheun_kongnamulgugbab_qisgbn` | 오징어 듬뿍 넣은 콩나물국밥 | 재료 이름 '이 육수에 콩나물' → soybean_sprouts(이름 보정표) |
| `ojingeokongnamul_sotbab_usafop` | 오징어콩나물 솥밥 | 재료 이름 '30분 불린 쌀' → rice(이름 보정표) |
| `ooojeosgal_boggeumbab_n_qjab` | OOO젓갈 볶음밥 | 재료 이름 '잘게자른 오징어젓갈' → ojingeojeot(이름 보정표) |
| `ramyeon_r7n0tw` | 라면 | 재료 줄 '파란부분 올리브유 5스푼' → green_onion, olive_oil로 나눔(이름 보정표); 재료 이름 '만두 소' → frozen_dumplings(이름 보정표) |
| `rojeddeogboggi_6zduy7` | 로제떡볶이 | cuisine '기타'→'한식'(vocab에 없음, 검수 필요); 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `ryusuyeong_nim_maeun_galbi_nd8fqz` | 류수영 님 매운 갈비 | 재료 이름 '양파 작은거' → onion(이름 보정표) |
| `ryusuyeongnim_deunggalbi_ohiyjy` | 류수영님 등갈비 | 재료 이름 '양념이 등갈비에 다 묻으면 설탕' → sugar(이름 보정표) |
| `ryusuyeongnim_dwaejigimci_haxtkv` | 류수영님 돼지김치 | 재료 이름 '더해줄 김치국물' → kimchi(이름 보정표) |
| `ryusuyeongnim_ggulsaeupija_scabdi` | 류수영님 꿀새우피자 | 재료 이름 '큼지막한 새우' → shrimp_raw(이름 보정표) |
| `ryusuyeongnim_maekomgesalboggeumbab_ybcgwb` | 류수영님 매콤게살볶음밥 | 재료 이름 '기름 두르고 계란' → egg(이름 보정표); 재료 이름 '끄고 마요네즈' → mayonnaise(이름 보정표) |
| `ryusuyeongnim_seupaemsundubujjigae_mqoww9` | 류수영님 스팸순두부찌개 | 재료 이름 '살탕' → sugar(이름 보정표) |
| `ryusuyeongnim_seupaemsundubujjigae_n5bfcu` | 류수영님 스팸순두부찌개 | 재료 이름 '불을 끄고 고춧가루' → gochugaru(이름 보정표); 재료 이름 '마지막 계란' → egg(이름 보정표) |
| `ryusuyeongnim_sundubujjigae_fvo7nq` | 류수영님 순두부찌개 | 재료 이름 '으로 민 뒤 불끄고 고추가루' → gochugaru(이름 보정표) |
| `ryusuyeongnim_uyubeoteopaseuta_43ruep` | 류수영님 우유버터파스타 | 재료 이름 '파스타면 백원동전 크기' → pasta(이름 보정표); 재료 이름 '졸아 들었다 싶으면 마늘' → garlic(이름 보정표) |
| `saelreodeuneun_maseobsda_l_qpzv` | 샐러드는 맛없다? | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `samgyeobsal_gireume_gimci_lxlb2n` | 삼겹살 기름에 김치 | 재료 이름 '김치 밥공기' → kimchi(이름 보정표) |
| `seupaemkongnamuljjim_p0cckn` | 스팸콩나물찜 | 재료 이름 '다른마늘' → garlic(이름 보정표); 재료 이름 '매콤한 맛을 위해 청양고추' → cheongyang_pepper(이름 보정표) |
| `sigboggeumbab_b6kble` | 식볶음밥 | 재료 이름 '숙주 크게' → mung_bean_sprouts(이름 보정표); 재료 이름 '새우는' → shrimp_raw(이름 보정표); 재료 이름 '잘섞이면 숙주' → mung_bean_sprouts(이름 보정표); 재료 이름 '이 위에 팟타이 소스' → pad_thai_sauce(이름 보정표) |
| `siweonhan_mulgugsu_6ktswe` | 시원한 물국수 | 재료 이름 '국수는 배 금방꺼지니' → somen(이름 보정표) |
| `sogalbi_fggzu3` | 소갈비 | 재료 이름 '코스트코에서' → beef_short_ribs(이름 보정표) |
| `sundububeoseosdeopbab_tl2_wx` | 순두부버섯덮밥 | 재료 이름 '전분물(전분' → starch(이름 보정표); 재료 이름 '바꾼 후 고춧가루' → gochugaru(이름 보정표) |
| `sundubujjigae_ym9dqz` | 순두부찌개 | 재료 이름 '위에 계란' → egg(이름 보정표) |
| `wanjeon_gangryeogcuceonhaneun_resipi_ibnida_8shbi0` | 완전 강력추천하는 레시피 입니다 🤗🤗 | 재료 이름 '새우 취향껏' → shrimp_raw(이름 보정표); 재료 이름 '열이 충분히 올라오면 양파' → onion(이름 보정표) |
| `weonpaen_jjajangmyeon_ycsyad` | 원팬 짜장면 | 재료 이름 '취향껏 고춧가루' → gochugaru(이름 보정표) |
| `weonpaen_saeubajilpaseuta_hk_aqu` | 원팬 새우바질파스타 | 재료 이름 '코스트코 새우' → shrimp_raw(이름 보정표) |
| `weonpaenddangkongbeoteopaseuta_sastin` | 원팬땅콩버터파스타 | 재료 이름 '땅콩버터 크게' → peanut_butter(이름 보정표); 재료 이름 '볶다가 맛술' → mirin(이름 보정표); 재료 이름 '부은 후 백원동전크기 파스타면' → pasta(이름 보정표) |
| `weonpaenhaejangpaseuta_qxtybu` | 원팬해장파스타 | 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `weonpaenhaejangpaseuta_vpvdlr` | 원팬해장파스타 | 재료 이름 '고추장 크게' → gochujang(이름 보정표) |
| `weonpaenjabcae_9b_fxs` | 원팬잡채 | 재료 이름 '진강장' → soy_sauce(이름 보정표) |
| `weonpaenpaseuta_pxx1nd` | 원팬파스타 | 재료 줄 '고추기름이 나오면 물 600ml' 뺌(물, 이름 보정표); 재료 이름 '동전크기' → pasta(이름 보정표); 재료 이름 '불을 끄고 올리브유' → olive_oil(이름 보정표) |
| `weonpaenpaseuta_tgucfr` | 원팬파스타 | 재료 이름 '잘 해동한 새우' → shrimp_raw(이름 보정표); 재료 이름 '파스타면 백원동전크기' → pasta(이름 보정표) |
| `yangbaecucasyudeopbab_abl0ir` | 양배추차슈덮밥 | 재료 이름 '하고 날려버릴 다진생강' → ginger(이름 보정표); 재료 이름 '색감과 감칠맛을 끌어올릴 짜장가루' → jjajang_powder(이름 보정표) |
| `yangbaecudubujeon_wf8r_8` | 양배추두부전 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음) |
| `yangpagyerandeopbab_2n81lv` | 양파계란덮밥 | 재료 이름 '없으신 분들은 다시다나 치킨스톡' → chicken_stock(이름 보정표) |
| `yeogdaegeub_kongnamuldeopbab_u8mw1h` | 역대급 콩나물덮밥 | 재료 이름 '가운데에 계란' → egg(이름 보정표) |
| `yeongsang_bosimyeon_asigessjiman_2dp9ic` | 영상 보시면 아시겠지만 | 조리기구 '기타 조리도구'(선택) 제외(vocab에 없음); 재료 이름 '양면이 다 노릇해지면 고춧가루' → gochugaru(이름 보정표) |

## 재료 매핑

- 모든 재료가 매핑된 레시피: 147/169
- 미매칭 재료가 있는 레시피: 22/169 (알레르기가 있는 사용자에게 제외됨)

미매칭 재료(등장 레시피 수). 상표 제품·시판 소스·가공품은 성분을 추측하지 않고 미매칭으로 둔다. 연결하려면 knowledge에 노드나 별칭을 검수해 추가한 뒤 다시 변환한다.

| 재료 이름 | 레시피 수 |
| --- | --- |
| 분말가루 | 5 |
| 000원에 | 1 |
| 갈은 깨 | 1 |
| 갓장아찌 | 1 |
| 라면스프 | 1 |
| 마지막에 | 1 |
| 볶다가 재료 | 1 |
| 볶을때 단단 | 1 |
| 비빌 때 | 1 |
| 스프 | 1 |
| 아니 저는 | 1 |
| 양은 | 1 |
| 양파오이지 채수 | 1 |
| 잘 안뭉쳐서 | 1 |
| 저도 제일 좋아하는 반찬 | 1 |
| 적절 | 1 |
| 제가 제일 좋아하는 식재료 | 1 |
| 파 | 1 |

## 같은 재료 id로 매핑된 줄

원본에서 이름이 달라 따로 적힌 줄이 같은 knowledge id로 매핑된 경우. 한 줄로 합칠지 검수한다(변환은 원본 줄을 그대로 둔다).

| id | 재료 id | 원문 |
| --- | --- | --- |
| `aesuni_ojingeogug_b1h_t` | `gochugaru` | 고운고춧가루 1스푼 / 고운 고춧가루로 1스푼 |
| `agwisuyug_enhnd6` | `soy_sauce` | 진간장 한스푼 / 두꼬집 진간장 1스푼 |
| `bab_3gonggi_ddugddag_halsu_issneun_gamjacamcijjageuli_0_72mg` | `gochujang` | 고추장 1 크게 한큰술 / 고추장 크게 한큰술 / 고추장 |
| `babdodug_sogogiyaggocujang_keoa8g` | `gochujang` | 고추장 300g / 고기양과 동일하게 고추장 300g |
| `babdodug_sogogiyaggocujang_keoa8g` | `ground_beef` | 소고기 다짐육 300g / 다짐육 300g / 소고기다짐육 300g |
| `babdodug_sogogiyaggocujang_keoa8g` | `honey` | 마지막 꿀 2스푼 / 꿀 2스푼 |
| `beikeonmaneul_weonpaenpaseuta_xahqx6` | `olive_oil` | 올리브오일 4스푼 / 졸아들면 올리브유 한스푼 / 올리브유 한스푼 |
| `cogcoghago_saekomdalkomhan_bibimgugsu_lkgv_6` | `pear_drink` | 갈아만든배 1캔 / 갈아만든 배 한캔 |
| `cogcoghago_saekomdalkomhan_bibimgugsu_lkgv_6` | `sesame_oil` | 마지막 참기름 한스푼 / 참기름 한스푼 |
| `cogcoghago_saekomdalkomhan_bibimgugsu_lkgv_6` | `vinegar` | 식초 2스푼 / 사과식초2스푼 |
| `cueogyi_ojingeogug_qhcyx` | `gochugaru` | 고운 고춧가루 가득 1스푼 / 고춧가루 |
| `cueogyi_osambulgogi_x7iwsb` | `ginger` | 다진생강 반스푼 / 마지막 킥 다진생강 반스푼 |
| `cueogyi_osambulgogi_x7iwsb` | `gochujang` | 고추장 2스푼 / 이때 고추장 2스푼 |
| `daepaesamgyeob_paseuta_9xmglr` | `anchovy_fish_sauce` | 멸치액젓 1스푼 / 양파 숨이 죽으면 멸치액젓 한스푼 / 양파 반개 |
| `daepaesamgyeobdeopbab_cakwdc` | `oyster_mushroom` | 느타리버섯 반팩 / 잘게 찢은 느타리 반팩 |
| `daepaesamgyeobdeopbab_cakwdc` | `pork_belly` | 대패삼겹살 100g / 삼겹살 100g / 대패 삼겹살 100g |
| `dalggaseumsal_buldalgpaseuta_z52qn6` | `butter` | 버터 20g / 무염버터 20g |
| `ddeogboggi_jung_coego_pgxsxq` | `egg` | 삶은 달걀 2개 / 달걀 2개 |
| `ddeogboggi_tqauco` | `salt` | 굵은소금 1/3스푼 / 굶은 소금 1/3스푼 / 소금 1/3스푼 |
| `dububibimbab_qanlhk` | `egg` | 달걀 후라이 1개 / 달걀 |
| `dububibimbab_qanlhk` | `soy_sauce` | 진간장 3스푼 / 국간장 1스푼 |
| `dwaejigomtang_iwotbj` | `ginger` | 생강 작은 조각 하나 / 생강 |
| `eomugboggeum_zz9stm` | `chili_oil` | 고추기름 2스푼 / 올려주는 고추기름 2스푼 |
| `eomugboggeum_zz9stm` | `sesame_oil` | 참기름 1스푼 / 참기름 한 스푼 / 맛을 올리기 위해 참기름 한 스푼 |
| `euro_jjolmyeon_pcwmvr` | `egg` | 삶은 달걀 1개 / 달걀 1개 |
| `euro_jjolmyeon_pcwmvr` | `gochujang` | 고추장 크게 1스푼 / 고추장 크게 한스푼 / 고추장 |
| `gajideopbab_hzjm20` | `gochugaru` | 하시는 분은 고춧가루 반스푼 / 고춧가루 반스푼 |
| `gangryeogcuceon_deunggalbi_nqqlq9` | `mirin` | 맛술 2스푼 / 미림 3스푼 |
| `gaseongbiwa_bijueoleul_modu_jabeun_sandeomikongnamulbulgogi_wo4w4` | `mirin` | 맛술(미림) 2스푼 / 미림 |
| `ggeutpanwang_dwaejijjigae_d4odtt` | `cheongyang_pepper` | 다진 청양고추 2개 / 청양고추 2개 / 위해 청양고추 2개 |
| `gimcibibimgugsu_uvpvro` | `sesame_oil` | 고소한 맛을 위해 참기름 1스푼 / 참기름 1스푼 |
| `gugsu_scrwet` | `naengmyeon_broth` | 시판냉면육수 1봉 / 제일 중요한 시판 냉면육수 1봉 |
| `hwanggeumbiyul_jeugseogddeogboggi_xfyulh` | `gochujang` | 고추장 크게 2스푼 / 크게 2스푼 / 고추장 |
| `hwanggeumbiyul_kongnamulmucim_m3oiih` | `green_onion` | 대파 흰부분 1 스푼 / 대파 1스푼 / 볼에 담고 대파 1스푼 |
| `insaengdoenjangjjigae_oitk6c` | `doenjang` | 된장 1스푼 / 2스푼 두르고 된장 1스푼 |
| `insaengganjanggugsu_bi0ceo` | `sesame` | 깨소금이 핵심이에요 영상에서는 2스푼 / 통깨를 갈아만든 깨소금 2스푼 / 깨소금 2스푼 |
| `iyeonbogswepeunimyi_gogiboggeumbab_xt2zuu` | `oyster_sauce` | 굴소스 한스푼 / 양념 필요없이 굴소스 한스푼 |
| `jeontong_doenjangjjigae_aknwi9` | `onion` | 앙파 1/4개 / 양파 1/4개 |
| `jeugseogddeogboggi_bkurly` | `egg` | 삶은 달걀 2개 / 계란 2개 / 달걀 2개 |
| `jeugseogddeogboggi_bkurly` | `gochujang` | 고추장 크게 1스푼 / 고추장 크게 한스푼 / 고추장 |
| `jeyugboggeum_awebqw` | `pork_shoulder` | 돼지앞다리살 500g / 돼지고기 앞다리살 500g / 앞다리살 500g |
| `jeyugboggeum_ha6w7e` | `garlic` | 다진마늘 한스푼 / 잡기위해 다진마늘 한스푼 |
| `jeyugboggeum_ha6w7e` | `gochujang` | 고추장 크게 한 큰술 / 고추장 |
| `jeyugboggeum_ruecur` | `mirin` | 맛술 3스푼 / 양념으로 맛술 3스푼 |
| `jinjeong_babdodug_qfyq2` | `ground_beef` | 소고기다짐육 300g / 다짐육 300g / 소고기 다짐육 300g |
| `mas_geongang_da_jabeul_su_issneun_dwaejigogisigeumcideopbab_yy3kjx` | `sesame_oil` | 참기름 / 참기름 한스푼 / 맛을 위해 참기름 한스푼 |
| `mas_geongang_da_jabeul_su_issneun_dwaejigogisigeumcideopbab_yy3kjx` | `soy_sauce` | 간장 한스푼 / 죽으면 진간장 1스푼 / 진간장 1스푼 |
| `nuguna_mandeul_su_issneun_weonpaenkeurimpaseuta_pbgzbp` | `pasta` | 파스타면 1인분 / 파스타면 / 동전크기 1인분 |
| `ramyeon_r7n0tw` | `olive_oil` | 올리브유 5스푼 / 파란부분 올리브유 5스푼 |
| `rojeddeogboggi_6zduy7` | `gochujang` | 고추장 크게 한스푼 / 고추장 한스푼 |
| `ryusuyeongnim_deunggalbi_ohiyjy` | `sugar` | 설탕 4스푼 / 양념이 등갈비에 다 묻으면 설탕 4스푼 |
| `ryusuyeongnim_maekomgesalboggeumbab_ybcgwb` | `mayonnaise` | 마요네즈 2스푼 / 끄고 마요네즈 2스푼 |
| `ryusuyeongnim_seupaemsundubujjigae_mqoww9` | `gochugaru` | 고춧가루 3스푼 / 고추가루 3스푼 |
| `ryusuyeongnim_seupaemsundubujjigae_mqoww9` | `sugar` | 설탕 반스푼 / 살탕 반스푼 |
| `ryusuyeongnim_seupaemsundubujjigae_n5bfcu` | `gochugaru` | 고춧가루 3스푼 / 불을 끄고 고춧가루 3스푼 |
| `ryusuyeongnim_sundubujjigae_fvo7nq` | `gochugaru` | 고춧가루 3스푼 / 한쪽으로 민 뒤 불끄고 고추가루 3스푼 |
| `ryusuyeongnim_uyubeoteopaseuta_43ruep` | `garlic` | 마늘 1개 / 졸아 들었다 싶으면 마늘 1개 |
| `seupaemkongnamuljjim_p0cckn` | `garlic` | 다른마늘 3스푼 / 다진마늘 3스푼 |
| `sigboggeumbab_b6kble` | `mung_bean_sprouts` | 숙주 크게 한줌 / 숙주 한줌 / 잘섞이면 숙주 한줌 |
| `sogalbi_fggzu3` | `beef_short_ribs` | 코스트코에서 2.5kg / 소갈비 2.5kg |
| `sundububeoseosdeopbab_tl2_wx` | `gochugaru` | 고춧가루 1스푼 / 바꾼 후 고춧가루 한스푼 |
| `sundububeoseosdeopbab_tl2_wx` | `starch` | 전분물(전분1스푼 / 전분 1스푼 |
| `sundubujjigae_skn2sh` | `salt` | 굵은 소금 1/3 스푼 / 굵은소금 1/3스푼 / 소금 1/3 스푼 |
| `teugbyeolhan_gug_k78gle` | `pork_shoulder` | 돼지 앞다리살 400g / 앞다리살 400g |
| `tuumbapaseuta_d93cqw` | `chicken_stock` | 치킨스톡 가루 반스푼 / 치킨스톡 |
| `weonpaen_jjajangmyeon_ycsyad` | `gochugaru` | 취향껏 고춧가루 1스푼 / 고춧가루 1스푼 |
| `weonpaenddangkongbeoteopaseuta_sastin` | `mirin` | 맛술 2스푼 / 볶다가 맛술 2스푼 |
| `weonpaenhaejangpaseuta_qxtybu` | `gochujang` | 고추장 크게 한스푼 / 고추장 |
| `weonpaenhaejangpaseuta_vpvdlr` | `gochujang` | 고추장 크게 1스푼 / 크게 1스푼 / 고추장 |
| `weonpaenjabcae_9b_fxs` | `soy_sauce` | 진간장 4스푼 / 진강장 4스푼 |
| `weonpaenpaseuta_pxx1nd` | `olive_oil` | 올리브유 5스푼 / 불을 끄고 올리브유 한스푼 |
| `weonpaenpaseuta_pxx1nd` | `pasta` | 파스타면 1인분 / 파스타면 / 동전크기 1인분 |
| `yangbaecucasyudeopbab_abl0ir` | `ginger` | 다진생강 1스푼 / 하고 날려버릴 다진생강 1스푼 |
| `yangbaecucasyudeopbab_abl0ir` | `pork_belly` | 삼겹살 500g / 통삼겹 500g |
| `yangpagyerandeopbab_2n81lv` | `chicken_stock` | 없으신 분들은 다시다나 치킨스톡 1/3스푼 / 치킨스톡 1/3스푼 |
| `yeongsang_bosimyeon_asigessjiman_2dp9ic` | `gochugaru` | 고춧가루 1스푼 / 양면이 다 노릇해지면 고춧가루 1스푼 |
