from internal.database import create_backend
import json

cfg = None
with open("configs/db.json", "r") as f:
    cfg = json.load(f)
    f.close()

backend = create_backend(cfg)
engine = backend["engine"]
SessionLocal = backend["SessionLocal"]
get_connection = backend["get_connection"]


# SQLAlchemy session 사용 예 (FastAPI dependency 스타일)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
