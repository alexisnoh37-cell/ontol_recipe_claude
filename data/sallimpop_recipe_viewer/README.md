# 살림팝 레시피 뷰어

살림팝 공개 레시피 데이터셋을 카드, 검색, 필터, 상세 화면으로 살펴보는 정적 웹 뷰어입니다.

## 데이터 갱신

```powershell
python build_viewer.py
```

원본 YAML은 `../sallimpop_recipe_dataset/recipes/sallimpop/`에서 읽고, 브라우저용 데이터는 `dist/recipes-data.js`로 생성합니다.

## 로컬 실행

```powershell
python -m http.server 8765 --directory dist
```

그다음 `http://127.0.0.1:8765`를 엽니다. `recipes-data.js`를 사용하므로 `dist/index.html`을 직접 열어도 주요 기능이 작동합니다.
