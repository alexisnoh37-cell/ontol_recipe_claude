# 살림팝 YouTube 레시피 데이터셋

- 채널: [살림팝](https://www.youtube.com/@%EC%82%B4%EB%A6%BC%ED%8C%9D)
- 검토 범위: 사전 분류한 유지 후보 259개
- YAML 수집: 169개
- 건너뜀: 90개
- 수집일: 2026-10-16

공개 영상 제목, 설명란, 한국어 자막에서 확인되는 정보만 사용했습니다. 추정한 시간·난이도·맛 수치와 자동 자막 기반 단계는 `note`에 표시했고, 모든 레코드는 사람 검수 전 상태인 `draft`입니다.

## 구성

- `recipes/sallimpop/*.yaml`: 영상별 레시피
- `index.csv`: 후보 259개 전체의 수집·건너뜀 결과
- `ingredient_names.csv`: 정규화 재료명 빈도와 원문 예시
- `classification.csv`: 수집 YAML의 요리권·요리 유형·주 조리법
- `validate.py`: 구조 검증기
- `REPORT.md`: 수집 결과와 검수 항목

## 검증

```powershell
python validate.py
```
