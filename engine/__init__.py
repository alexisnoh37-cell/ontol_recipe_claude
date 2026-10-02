"""레시피 추천 엔진 (순수 Python).

표준 라이브러리와 pyyaml만 import한다. DB 드라이버, SQLAlchemy, FastAPI, Streamlit,
그리고 이 저장소의 kb/·storage/·api/·app/ 패키지에 의존하지 않는다
(tests/logic/test_engine_purity.py가 강제). 데이터는 리포지토리 인터페이스로 주입받는다.
엔진 본체는 Phase 1에서 구현한다.
"""
