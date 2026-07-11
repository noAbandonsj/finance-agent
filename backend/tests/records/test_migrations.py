from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

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
                "market_view",
                "horizon",
                "confidence",
                "summary",
                "supporting_evidence_json",
                "opposing_evidence_json",
                "risks_json",
                "invalidation_conditions_json",
                "full_result_json",
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

        assert {index["name"] for index in inspector.get_indexes("analysis_run")} == {
            "ix_analysis_run_status_started_at"
        }
        assert {index["name"] for index in inspector.get_indexes("analysis_event")} == {
            "ix_analysis_event_run_id_sequence"
        }
        assert {index["name"] for index in inspector.get_indexes("tool_call_record")} == {
            "ix_tool_call_record_run_id"
        }
        assert {index["name"] for index in inspector.get_indexes("analysis_result")} == {
            "ix_analysis_result_run_id"
        }

        event_uniques = inspector.get_unique_constraints("analysis_event")
        assert {tuple(item["column_names"]) for item in event_uniques} == {("run_id", "sequence")}
        result_uniques = inspector.get_unique_constraints("analysis_result")
        assert {tuple(item["column_names"]) for item in result_uniques} == {("run_id",)}

        for table_name in ("analysis_event", "tool_call_record", "analysis_result"):
            foreign_keys = inspector.get_foreign_keys(table_name)
            assert len(foreign_keys) == 1
            assert foreign_keys[0]["referred_table"] == "analysis_run"
            assert foreign_keys[0]["constrained_columns"] == ["run_id"]
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
