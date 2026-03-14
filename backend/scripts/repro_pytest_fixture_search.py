import os
import traceback
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app import db
from app.main import create_app
from app.auth import middleware
from app.auth.service import hash_api_key
from app.models import ApiKey, ApiPlan, Base
from app.routes import catalog
from app.ingest.registry import get_connector


def _auth_headers(key: str = "test-key") -> dict[str, str]:
    with db.SessionLocal() as session:
        plan = session.execute(select(ApiPlan).where(ApiPlan.name == "free")).scalar_one_or_none()
        if plan is None:
            plan = ApiPlan(name="free", monthly_quota_requests=5000, burst_rpm=60)
            session.add(plan)
            session.flush()

        api_key = session.execute(select(ApiKey).where(ApiKey.prefix == key[:8])).scalar_one_or_none()
        if api_key is None:
            session.add(
                ApiKey(
                    key_hash=hash_api_key(key),
                    prefix=key[:8],
                    plan_id=plan.id,
                    is_active=True,
                    scopes=["read:catalog"],
                )
            )
            session.commit()

    return {"X-API-Key": key}


def run():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        database_url = f"sqlite+pysqlite:///{db_path}"
        os.environ["DATABASE_URL"] = database_url

        if db.engine is not None:
            db.engine.dispose()
        db.init_engine(database_url)

        os.environ["PUBLIC_API_ENABLED"] = "false"
        app = create_app(database_url=database_url)
        app.config["RATE_LIMIT_PER_MINUTE"] = 5
        app.config["CACHE_TTL_SECONDS"] = 60
        catalog._RATE_LIMIT_BUCKETS.clear()
        catalog._CACHE.clear()
        middleware._RATE_WINDOWS.clear()
        Base.metadata.drop_all(bind=db.engine)
        Base.metadata.create_all(bind=db.engine)

        connector = get_connector("fixture_local")
        with db.SessionLocal() as session:
            connector.run(session, "data/fixtures")
            session.commit()

        print(f"DATABASE_URL env: {os.environ.get('DATABASE_URL')}")
        print(f"db.engine.url: {db.engine.url if db.engine else None}")
        bind = getattr(db.SessionLocal, 'kw', {}).get('bind') if db.SessionLocal else None
        print(f"SessionLocal bind: {bind.url if bind is not None else None}")

        with app.test_client() as test_client:
            try:
                response = test_client.get("/api/search?q=pika&game=pokemon", headers=_auth_headers())
                print(f"status code: {response.status_code}")
                print(response.get_data(as_text=True))
            except Exception:
                print("traceback completo:")
                traceback.print_exc()


if __name__ == "__main__":
    run()
