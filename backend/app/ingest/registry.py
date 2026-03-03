from app.ingest.base import SourceConnector
from app.ingest.connectors.fixture_local import FixtureLocalConnector


CONNECTORS = {
    FixtureLocalConnector.name: FixtureLocalConnector,
}


def get_connector(name: str) -> SourceConnector:
    connector_cls = CONNECTORS.get(name)
    if not connector_cls:
        raise ValueError(f"Unknown connector: {name}")
    return connector_cls()
