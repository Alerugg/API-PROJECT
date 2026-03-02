from app.ingest.base import SourceConnector


class FixtureLocalConnector(SourceConnector):
    name = "fixture_local"


CONNECTORS = {
    FixtureLocalConnector.name: FixtureLocalConnector,
}


def get_connector(name: str) -> SourceConnector:
    connector_cls = CONNECTORS.get(name)
    if not connector_cls:
        raise ValueError(f"Unknown connector: {name}")
    return connector_cls()
