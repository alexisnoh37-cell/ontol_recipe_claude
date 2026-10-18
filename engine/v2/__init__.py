"""추천 v2 (docs/plan.md 부록 G, decisions D7·D8).

v1(engine/*.py)을 바꾸지 않고 나란히 둔다. v1 모듈은 import해 재사용만 한다.
형태 3가지(random·pantry·dish), v2 필터(절대 불선호는 definite만 제외), Jev 재정렬(Reranker Protocol로 주입).
"""
