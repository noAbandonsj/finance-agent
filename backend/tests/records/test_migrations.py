from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, inspect, text

from ai_finance.records.database import Database


BACKEND_ROOT = Path(__file__).parents[2]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def upgrade_database(database_url: str) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def test_initial_migration_creates_business_tables(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "app.db")

    upgrade_database(database_url)

    database = Database(database_url)
    try:
        assert set(inspect(database.engine).get_table_names()) == {
            "alembic_version",
            "analysis_event",
            "analysis_result",
            "analysis_run",
            "tool_call_record",
            "watchlist_item",
        }
    finally:
        database.dispose()


def test_initial_migration_has_required_columns_constraints_and_indexes(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "app.db")
    upgrade_database(database_url)
    database = Database(database_url)

    try:
        inspector = inspect(database.engine)
        expected_columns = {
            "analysis_run": {
                "id",
                "thread_id",
                "user_query",
                "symbol",
                "status",
                "model_name",
                "prompt_version",
                "started_at",
                "finished_at",
                "data_cutoff",
                "error_code",
                "error_message",
            },
            "analysis_event": {
                "id",
                "run_id",
                "sequence",
                "event_type",
                "message",
                "payload_json",
                "terminal",
                "created_at",
            },
            "tool_call_record": {
                "id",
                "run_id",
                "tool_name",
                "arguments_json",
                "result_json",
                "provider",
                "market_time",
                "retrieved_at",
                "duration_ms",
                "success",
                "error_code",
            },
            "analysis_result": {
                "id",
                "run_id",
                "report_markdown",
                "created_at",
            },
            "watchlist_item": {
                "symbol",
                "display_name",
                "security_type",
                "note",
                "created_at",
            },
        }
        for table_name, column_names in expected_columns.items():
            assert {column["name"] for column in inspector.get_columns(table_name)} == column_names

        columns = {
            table_name: {column["name"]: column for column in inspector.get_columns(table_name)}
            for table_name in expected_columns
        }
        assert isinstance(columns["analysis_run"]["id"]["type"], String)
        assert columns["analysis_run"]["id"]["type"].length == 36
        assert columns["analysis_run"]["id"]["nullable"] is False
        assert isinstance(columns["analysis_run"]["user_query"]["type"], Text)
        assert isinstance(columns["analysis_run"]["started_at"]["type"], DateTime)
        assert columns["analysis_run"]["finished_at"]["nullable"] is True
        assert isinstance(columns["analysis_event"]["sequence"]["type"], Integer)
        assert isinstance(columns["analysis_event"]["payload_json"]["type"], JSON)
        assert columns["analysis_event"]["payload_json"]["nullable"] is True
        assert isinstance(columns["analysis_event"]["terminal"]["type"], Boolean)
        assert columns["analysis_event"]["terminal"]["nullable"] is False
        assert isinstance(columns["tool_call_record"]["duration_ms"]["type"], Integer)
        assert columns["tool_call_record"]["result_json"]["nullable"] is True
        assert isinstance(columns["tool_call_record"]["success"]["type"], Boolean)
        assert isinstance(columns["analysis_result"]["report_markdown"]["type"], Text)
        assert columns["analysis_result"]["report_markdown"]["nullable"] is False
        assert columns["watchlist_item"]["note"]["nullable"] is True

        expected_primary_keys = {
            "analysis_run": ("id",),
            "analysis_event": ("id",),
            "tool_call_record": ("id",),
            "analysis_result": ("id",),
            "watchlist_item": ("symbol",),
        }
        for table_name, column_names in expected_primary_keys.items():
            primary_key = inspector.get_pk_constraint(table_name)
            assert tuple(primary_key["constrained_columns"]) == column_names

        expected_indexes = {
            "analysis_run": {"ix_analysis_run_status_started_at": ("status", "started_at")},
            "analysis_event": {"ix_analysis_event_run_id_sequence": ("run_id", "sequence")},
            "tool_call_record": {"ix_tool_call_record_run_id": ("run_id",)},
            "analysis_result": {"ix_analysis_result_run_id": ("run_id",)},
        }
        for table_name, expected_table_indexes in expected_indexes.items():
            indexes = inspector.get_indexes(table_name)
            assert {
                index["name"]: tuple(index["column_names"]) for index in indexes
            } == expected_table_indexes
            assert all(not index["unique"] for index in indexes)

        event_uniques = {
            item["name"]: tuple(item["column_names"])
            for item in inspector.get_unique_constraints("analysis_event")
        }
        assert event_uniques == {"uq_analysis_event_run_id_sequence": ("run_id", "sequence")}
        result_uniques = {
            item["name"]: tuple(item["column_names"])
            for item in inspector.get_unique_constraints("analysis_result")
        }
        assert result_uniques == {"uq_analysis_result_run_id": ("run_id",)}

        expected_foreign_keys = {
            "analysis_event": "fk_analysis_event_run_id",
            "tool_call_record": "fk_tool_call_record_run_id",
            "analysis_result": "fk_analysis_result_run_id",
        }
        for table_name, constraint_name in expected_foreign_keys.items():
            foreign_keys = inspector.get_foreign_keys(table_name)
            assert len(foreign_keys) == 1
            foreign_key = foreign_keys[0]
            assert foreign_key["name"] == constraint_name
            assert foreign_key["referred_table"] == "analysis_run"
            assert foreign_key["constrained_columns"] == ["run_id"]
            assert foreign_key["referred_columns"] == ["id"]
            assert foreign_key["options"]["ondelete"] == "CASCADE"
    finally:
        database.dispose()


def test_database_enables_sqlite_integrity_and_busy_timeout(tmp_path: Path) -> None:
    database = Database(sqlite_url(tmp_path / "app.db"))
    try:
        with database.engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
            assert connection.scalar(text("PRAGMA busy_timeout")) == 5000
    finally:
        database.dispose()
