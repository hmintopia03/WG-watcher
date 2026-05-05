import sqlite3
from pathlib import Path


class SeenListingsDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> "SeenListingsDB":
        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_listings (
                listing_id TEXT PRIMARY KEY,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.connection:
            self.connection.close()

    def has_seen(self, listing_id: str) -> bool:
        cursor = self._connection.execute(
            "SELECT 1 FROM seen_listings WHERE listing_id = ? LIMIT 1",
            (listing_id,),
        )
        return cursor.fetchone() is not None

    def mark_seen(self, listing_id: str) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO seen_listings (listing_id) VALUES (?)",
            (listing_id,),
        )
        self._connection.commit()

    @property
    def _connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("Database connection is not open")
        return self.connection
