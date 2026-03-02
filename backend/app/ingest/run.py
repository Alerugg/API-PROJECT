import argparse

from app import db
from app.ingest.registry import get_connector


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ingest connector")
    parser.add_argument("connector", help="Connector name (example: fixture_local)")
    parser.add_argument("--path", default="backend/data/fixtures", help="Folder containing JSON fixture files")
    args = parser.parse_args()

    db.init_engine()
    connector = get_connector(args.connector)

    with db.SessionLocal() as session:
        stats = connector.run(session, args.path)
        session.commit()

    print(
        f"ingest complete connector={args.connector} files_seen={stats.files_seen} "
        f"files_skipped={stats.files_skipped} inserted={stats.records_inserted} updated={stats.records_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
