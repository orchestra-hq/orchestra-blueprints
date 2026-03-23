"""
Mocked PostgreSQL data retrieval utility.
No external dependencies. No real database.
Purely in-memory + deterministic demo behavior.
"""

from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging
import os


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Mock data (acts like database tables)
# -------------------------------------------------------------------
MOCK_USERS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": "2024-01-01"},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "created_at": "2024-01-05"},
    {"id": 3, "name": "Charlie", "email": "charlie@test.com", "created_at": "2024-01-10"},
    {"id": 4, "name": "Diana", "email": "diana@example.com", "created_at": "2024-02-01"},
]


# -------------------------------------------------------------------
# Mock cursor / connection
# -------------------------------------------------------------------
class MockCursor:
    def __init__(self, data):
        self.data = data
        self._results = []
        self.description = []

    def execute(self, query: str, params: tuple = ()):
        logger.debug(f"[MOCK] Executing query: {query} | params={params}")

        # Extremely naive "query parsing" for demo purposes
        if "FROM users" not in query:
            self._results = []
            self.description = []
            return

        results = self.data

        if "WHERE id =" in query:
            user_id = params[0]
            results = [u for u in results if u["id"] == user_id]

        if "email LIKE" in query:
            pattern = params[0].replace("%", "")
            results = [u for u in results if pattern in u["email"]]

        if "ORDER BY created_at DESC" in query:
            results = sorted(results, key=lambda x: x["created_at"], reverse=True)

        if "COUNT(*)" in query:
            self._results = [(len(results),)]
            self.description = [("total",)]
            return

        self._results = [tuple(r.values()) for r in results]
        self.description = [(k,) for k in results[0].keys()] if results else []

    def fetchall(self):
        return self._results

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchmany(self, limit: int):
        return self._results[:limit]

    @property
    def rowcount(self):
        return len(self._results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


class MockConnection:
    def cursor(self):
        return MockCursor(MOCK_USERS)

    def commit(self):
        logger.debug("[MOCK] Commit called")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


# -------------------------------------------------------------------
# Mock connector
# -------------------------------------------------------------------
class PostgreSQLConnector:
    """
    Fully mocked PostgreSQL connector.
    Behaves like a DB client but never touches a database.
    """

    def __init__(self, *args, **kwargs):
        logger.info("Initializing mocked PostgreSQL connector")
        self.pool = True  # just a flag to keep interface intact

    @contextmanager
    def get_connection(self):
        yield MockConnection()

    def fetch_all(self, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                if not rows:
                    return None
                columns = [c[0] for c in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [c[0] for c in cursor.description]
                return dict(zip(columns, row))

    def fetch_many(self, query: str, limit: int = 10, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchmany(limit)
                if not rows:
                    return None
                columns = [c[0] for c in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    def execute_query(self, query: str, params: tuple = None) -> bool:
        logger.info(f"[MOCK] Executed write query: {query}")
        return True

    def close(self):
        logger.info("Mock connector closed")


# -------------------------------------------------------------------
# Demo
# -------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("Mocked PostgreSQL Connector Demo")
    logger.info("=" * 60)

    db = PostgreSQLConnector()

    print("\n--- Fetch all users ---")
    print(db.fetch_all("SELECT * FROM users;"))

    print("\n--- Fetch user id=1 ---")
    print(db.fetch_one("SELECT * FROM users WHERE id = %s;", (1,)))

    print("\n--- Fetch 2 most recent users ---")
    print(db.fetch_many("SELECT * FROM users ORDER BY created_at DESC;", limit=2))

    print("\n--- Fetch users from example.com ---")
    print(db.fetch_all("SELECT * FROM users WHERE email LIKE %s;", ("%@example.com",)))

    print("\n--- Execute write query ---")
    print(db.execute_query("DELETE FROM users WHERE id = %s;", (99,)))

    db.close()

    logger.info("=" * 60)
    logger.info("Demo completed (mocked)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
