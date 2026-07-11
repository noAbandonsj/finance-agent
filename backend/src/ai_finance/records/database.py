from collections.abc import Iterator
from contextlib import contextmanager
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def configure_sqlite_connection(
    dbapi_connection: SQLiteConnection, _connection_record: object
) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        event.listen(self.engine, "connect", configure_sqlite_connection)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session_factory() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()
