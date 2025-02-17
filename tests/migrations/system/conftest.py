from unittest.mock import MagicMock

import pytest

from datastore.migrations import MigrationHandler, setup as migration_setup
from datastore.reader.flask_frontend import FlaskFrontend as ReaderFlaskFrontend
from datastore.reader.flask_frontend.routes import Route
from datastore.shared.di import injector
from datastore.shared.postgresql_backend import ConnectionHandler
from datastore.shared.util import DeletedModelsBehaviour
from datastore.writer.flask_frontend import FlaskFrontend as WriterFlaskFrontend
from datastore.writer.flask_frontend.routes import WRITE_URL
from tests import (  # noqa
    db_connection,
    db_cur,
    json_client,
    make_json_client,
    reset_db_data,
    reset_db_schema,
    reset_di,
    setup_db_connection,
)
from tests.util import assert_response_code, assert_success_response


@pytest.fixture(autouse=True)
def setup(reset_di):  # noqa
    migration_setup()


@pytest.fixture()
def setup_memory_migration(reset_di):  # noqa
    migration_setup(memory_only=True)


@pytest.fixture()
def migration_handler():  # noqa
    yield injector.get(MigrationHandler)


@pytest.fixture()
def connection_handler():  # noqa
    yield injector.get(ConnectionHandler)


@pytest.fixture()
def writer():
    application = WriterFlaskFrontend.create_application()
    with application.test_client() as client:
        yield from make_json_client(client)


@pytest.fixture()
def reader():
    application = ReaderFlaskFrontend.create_application()
    with application.test_client() as client:
        yield from make_json_client(client)


@pytest.fixture()
def write(writer):
    def _write(*events):
        payload = {
            "user_id": 1,
            "information": {},
            "locked_fields": {},
            "events": events,
        }
        response = writer.post(WRITE_URL, payload)
        assert_response_code(response, 201)

    yield _write


@pytest.fixture()
def read_model(reader):
    def _read_model(fqid, position=None):
        payload = {
            "fqid": fqid,
            "get_deleted_models": DeletedModelsBehaviour.ALL_MODELS,
        }
        if position is not None:
            payload["position"] = position

        response = reader.post(Route.GET.URL, payload)
        assert_success_response(response)
        return response.json

    yield _read_model


@pytest.fixture()
def assert_model(reader, read_model, query_single_value):
    def _assert_model(fqid, expected, position=None):
        if position is None:
            assert read_model(fqid) == expected

            # get max position
            position = query_single_value("select max(position) from positions")

        # build model and check
        assert read_model(fqid, position=position) == expected

    yield _assert_model


@pytest.fixture()
def exists_model(reader):
    def _exists_model(fqid, position=None):
        payload = {
            "fqid": fqid,
            "get_deleted_models": DeletedModelsBehaviour.ALL_MODELS,
        }
        if position is not None:
            payload["position"] = position
        response = reader.post(
            Route.GET.URL,
            payload,
        )
        return response.status_code == 200

    yield _exists_model


@pytest.fixture()
def query_single_value(connection_handler):
    def _query_single_value(query, arguments=None):
        with connection_handler.get_connection_context():
            if arguments is None:
                arguments = []
            return connection_handler.query_single_value(query, arguments)

    yield _query_single_value


@pytest.fixture()
def assert_count(query_single_value):
    def _assert_count(table, amount):
        assert query_single_value(f"select count(*) from {table}") == amount

    yield _assert_count


@pytest.fixture()
def assert_finalized(assert_count):
    def _assert_finalized():
        assert_count("migration_keyframes", 0)
        assert_count("migration_keyframe_models", 0)
        assert_count("collectionfields", 0)
        assert_count("events_to_collectionfields", 0)
        assert_count("migration_events", 0)
        assert_count("migration_positions", 0)

    return _assert_finalized


@pytest.fixture()
def set_migration_index_to_1(migration_handler):
    def _set_migration_index_to_1():
        previous_logger = migration_handler.logger.info
        migration_handler.logger.info = i = MagicMock()
        migration_handler.migrate()  # set target migration index to 1
        i.assert_called()
        assert (
            "The datastore has a migration index of -1. Set the migration index to 1."
            in i.call_args.args[0]
        )
        migration_handler.logger.info = previous_logger

    yield _set_migration_index_to_1
