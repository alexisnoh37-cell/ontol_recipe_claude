# 자취요리신 레시피 데이터

공개 YouTube 정보에서 `Making simple Korean food`(자취요리신) 채널의 레시피 영상 100개를 정리한 데이터셋이다.

## 구성

- `recipes/simplecooking/*.yaml`: 영상 1개당 레시피 YAML 1개
- `index.csv`: 검토한 130개 영상의 수집·건너뜀 내역
- `ingredient_names.csv`: 정규화 재료명별 등장 횟수와 원문 예시
- `classification.csv`: 요리권역, 음식 유형, 대표 조리법 분류
- `validate.py`: YAML 구조 및 값 검증
- `build_recipes.py`: 공개 메타데이터에서 결과물을 다시 생성하는 스크립트
- `metadata/`: 수집 근거로 사용한 공개 설명·게시일·자막 메타데이터
- `REPORT.md`: 수집 결과와 사람 검토 항목

## 검증

```powershell
python validate.py
```

정상 결과: `검증 통과: 100개 YAML 파일`

## 판단 원칙

- 광고·제품 구매·이벤트 안내가 포함된 영상은 제외했다.
- 설명란에 구조화 가능한 `[재료]`, `[만드는 법]`이 없는 영상은 제외했다.
- 물은 `ingredients`에서 제외했다.
- 설명란과 공개 한국어 자막을 확인하되, `raw_text`와 영상 제목만 원문을 보존했다.
- 한 영상에 여러 레시피가 있으면 첫 번째 레시피만 구조화하고 `note`에 표시했다.
- 인분을 확인할 수 없으면 `null`, 시간을 확인할 수 없으면 추정값과 `시간 추정` 메모를 사용했다.
- 위 불확실성 규칙 때문에 현재 100개 모두 `confidence: low`이다.
