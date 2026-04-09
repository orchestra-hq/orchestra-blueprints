"""Unit tests for postgres_connector.py mock implementation."""

import pytest
import sys
from pathlib import Path

# Add the postgres module to the path
postgres_path = Path(__file__).parent.parent.parent / "postgres"
sys.path.insert(0, str(postgres_path))

from postgres_connector import PostgreSQLConnector, MockConnection, MockCursor, MOCK_USERS


class TestMockCursor:
    """Tests for MockCursor class."""

    def test_cursor_executes_fetch_all_query(self):
        """Test that cursor can execute a query and fetch all results."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users;")
        results = cursor.fetchall()
        assert len(results) == 4
        assert results[0] == (1, "Alice", "alice@example.com", "2024-01-01")

    def test_cursor_fetch_by_id(self):
        """Test fetching a user by id with WHERE clause."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users WHERE id = %s;", (2,))
        result = cursor.fetchone()
        assert result == (2, "Bob", "bob@example.com", "2024-01-05")

    def test_cursor_filter_by_email_pattern(self):
        """Test filtering users by email pattern."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users WHERE email LIKE %s;", ("%@example.com",))
        results = cursor.fetchall()
        assert len(results) == 3  # Alice, Bob, Diana
        assert all("example.com" in str(row) for row in results)

    def test_cursor_order_by_desc(self):
        """Test ordering results by created_at in descending order."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC;")
        results = cursor.fetchall()
        assert results[0][3] == "2024-02-01"  # Diana (most recent)
        assert results[-1][3] == "2024-01-01"  # Alice (oldest)

    def test_cursor_count_query(self):
        """Test COUNT query returns count of results."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT COUNT(*) FROM users;")
        result = cursor.fetchone()
        assert result == (4,)

    def test_cursor_fetchmany(self):
        """Test fetching limited number of rows."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users;")
        results = cursor.fetchmany(2)
        assert len(results) == 2

    def test_cursor_rowcount(self):
        """Test that rowcount property returns correct count."""
        cursor = MockCursor(MOCK_USERS)
        cursor.execute("SELECT * FROM users;")
        assert cursor.rowcount == 4

    def test_cursor_context_manager(self):
        """Test that cursor works as context manager."""
        cursor = MockCursor(MOCK_USERS)
        with cursor as c:
            assert c is cursor


class TestMockConnection:
    """Tests for MockConnection class."""

    def test_connection_creates_cursor(self):
        """Test that connection can create a cursor."""
        conn = MockConnection()
        cursor = conn.cursor()
        assert isinstance(cursor, MockCursor)

    def test_connection_commit(self):
        """Test that connection commit doesn't raise error."""
        conn = MockConnection()
        conn.commit()  # Should not raise

    def test_connection_context_manager(self):
        """Test that connection works as context manager."""
        with MockConnection() as conn:
            assert isinstance(conn, MockConnection)


class TestPostgreSQLConnector:
    """Tests for PostgreSQLConnector class."""

    def test_connector_initialization(self):
        """Test that connector initializes successfully."""
        db = PostgreSQLConnector()
        assert db.pool is True

    def test_fetch_all_returns_all_users(self):
        """Test fetching all users returns a list of dictionaries."""
        db = PostgreSQLConnector()
        results = db.fetch_all("SELECT * FROM users;")
        assert len(results) == 4
        assert results[0] == {"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": "2024-01-01"}

    def test_fetch_one_returns_single_user(self):
        """Test fetching a single user by id."""
        db = PostgreSQLConnector()
        result = db.fetch_one("SELECT * FROM users WHERE id = %s;", (1,))
        assert result["name"] == "Alice"
        assert result["id"] == 1

    def test_fetch_one_returns_none_for_no_results(self):
        """Test that fetch_one returns None when no results found."""
        db = PostgreSQLConnector()
        result = db.fetch_one("SELECT * FROM users WHERE id = %s;", (999,))
        assert result is None

    def test_fetch_many_with_limit(self):
        """Test fetching limited number of users."""
        db = PostgreSQLConnector()
        results = db.fetch_many("SELECT * FROM users;", limit=2)
        assert len(results) == 2

    def test_fetch_many_returns_none_for_no_results(self):
        """Test that fetch_many returns None when no results found."""
        db = PostgreSQLConnector()
        result = db.fetch_many("SELECT * FROM users WHERE id = %s;", limit=5, params=(999,))
        assert result is None

    def test_fetch_all_with_filter(self):
        """Test fetching all users filtered by email domain."""
        db = PostgreSQLConnector()
        results = db.fetch_all("SELECT * FROM users WHERE email LIKE %s;", ("%@example.com",))
        assert len(results) == 3
        assert all("example.com" in user["email"] for user in results)

    def test_execute_query_returns_true(self):
        """Test that execute_query returns True."""
        db = PostgreSQLConnector()
        result = db.execute_query("DELETE FROM users WHERE id = %s;", (1,))
        assert result is True

    def test_close_connector(self):
        """Test that close method executes without error."""
        db = PostgreSQLConnector()
        db.close()  # Should not raise
