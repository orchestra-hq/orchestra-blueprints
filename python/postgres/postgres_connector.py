"""
PostgreSQL data retrieval utility with connection pooling.
"""

import psycopg2
from psycopg2 import pool, sql
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging
import os
import sys


# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLConnector:
    """
    A PostgreSQL connector class that manages database connections and queries.
    """
    
    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5432, pool_size: int = 5):
        """
        Initialize PostgreSQL connector with connection pooling.
        
        Args:
            host: Database host
            database: Database name
            user: Database user
            password: Database password
            port: Database port
            pool_size: Connection pool size
        """
        self.pool = None
        self.host = host
        self.database = database
        logger.info(f"Initializing PostgreSQL connector for {database} on {host}:{port}")
        
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                1,
                pool_size,
                host=host,
                database=database,
                user=user,
                password=password,
                port=port
            )
            logger.info(f"✓ Connection pool created successfully for {database}")
        except psycopg2.Error as e:
            logger.error(f"✗ Error creating connection pool: {e}")
            logger.warning("Database connection failed - running in demo mode")
    
    @contextmanager
    def get_connection(self):
        """Context manager to get a connection from the pool."""
        conn = None
        try:
            if self.pool is None:
                logger.debug("Pool is None, returning mock connection")
                yield None
                return
            
            conn = self.pool.getconn()
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Connection error: {e}")
            yield None
        finally:
            if conn and self.pool:
                self.pool.putconn(conn)
    
    def fetch_all(self, query: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all records from a query.
        
        Args:
            query: SQL query
            params: Query parameters for parameterized queries
        
        Returns:
            List of dictionaries or None on error
        """
        logger.debug(f"Executing fetch_all query: {query}")
        
        if self.pool is None:
            logger.error("Connection pool not available")
            return None
            
        try:
            with self.get_connection() as conn:
                if conn is None:
                    return None
                
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    logger.info(f"✓ Fetched {len(results)} records")
                    return results
        except psycopg2.Error as e:
            logger.error(f"✗ Query execution error: {e}")
            return None
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a single record from a query.
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            Dictionary with single record or None
        """
        logger.debug(f"Executing fetch_one query: {query}")
        
        if self.pool is None:
            logger.error("Connection pool not available")
            return None
            
        try:
            with self.get_connection() as conn:
                if conn is None:
                    return None
                
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    result = cursor.fetchone()
                    if result:
                        columns = [desc[0] for desc in cursor.description]
                        logger.info("✓ Fetched 1 record")
                        return dict(zip(columns, result))
                    logger.info("No records found")
                    return None
        except psycopg2.Error as e:
            logger.error(f"✗ Query execution error: {e}")
            return None
    
    def fetch_many(self, query: str, limit: int = 10, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch multiple records from a query.
        
        Args:
            query: SQL query
            limit: Number of records to fetch
            params: Query parameters
        
        Returns:
            List of dictionaries or None on error
        """
        try:
            with self.get_connection() as conn:
                if conn is None:
                    return None
                
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchmany(limit)]
        except psycopg2.Error as e:
            logger.error(f"Query execution error: {e}")
            return None
    
    def execute_query(self, query: str, params: tuple = None) -> bool:
        """
        Execute a query that doesn't return results (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                if conn is None:
                    return False
                
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    conn.commit()
                    logger.info(f"Query executed successfully. Rows affected: {cursor.rowcount}")
                    return True
        except psycopg2.Error as e:
            logger.error(f"Query execution error: {e}")
            return False
    
    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("✓ Connection pool closed")


def main():
    """Demonstrate PostgreSQL connector usage."""
    
    logger.info("=" * 60)
    logger.info("PostgreSQL Connector Demo")
    logger.info("=" * 60)
    
    # Get database credentials from environment or use defaults
    host = os.getenv("POSTGRES_HOST", "localhost")
    database = os.getenv("POSTGRES_DATABASE", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    
    logger.info(f"Database Config: {user}@{host}:{port}/{database}")
    
    # Initialize connector
    db = PostgreSQLConnector(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port,
        pool_size=5
    )
    
    if db.pool is None:
        logger.warning("⚠ Database connection unavailable - demo mode (no actual queries will run)")
        logger.info("To connect to a real database, set these environment variables:")
        logger.info("  POSTGRES_HOST, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT")
        print("\n--- Demo Mode Examples ---\n")
    else:
        logger.info("✓ Database connection successful!")
    
    # Example 1: Fetch multiple records
    print("\n--- Example 1: Fetch all users ---")
    logger.info("Attempting to fetch users...")
    users = db.fetch_all("SELECT id, name, email FROM users LIMIT 5;")
    if users:
        for user in users:
            print(user)
    else:
        print("[Demo] Would fetch user records here")
    
    # Example 2: Fetch single record
    print("\n--- Example 2: Fetch single user ---")
    logger.info("Attempting to fetch single user with ID=1...")
    user = db.fetch_one("SELECT * FROM users WHERE id = %s;", (1,))
    if user:
        print(user)
    else:
        print("[Demo] Would fetch a single user record here")
    
    # Example 3: Fetch limited records
    print("\n--- Example 3: Fetch 3 records ---")
    logger.info("Attempting to fetch 3 most recent users...")
    limited_users = db.fetch_many("SELECT id, name, email FROM users ORDER BY created_at DESC;", limit=3)
    if limited_users:
        for user in limited_users:
            print(user)
    else:
        print("[Demo] Would fetch limited user records here")
    
    # Example 4: Fetch with parameterized query
    print("\n--- Example 4: Fetch by email domain ---")
    logger.info("Attempting to fetch users from example.com...")
    users_by_domain = db.fetch_all(
        "SELECT * FROM users WHERE email LIKE %s;",
        ('%@example.com',)
    )
    if users_by_domain:
        print(f"Found {len(users_by_domain)} users in example.com domain")
    else:
        print("[Demo] Would fetch users from example.com here")
    
    # Example 5: Aggregation
    print("\n--- Example 5: User statistics ---")
    logger.info("Attempting to fetch user statistics...")
    stats = db.fetch_one(
        "SELECT COUNT(*) as total, AVG(id) as avg_id, MAX(created_at) as latest FROM users;"
    )
    if stats:
        print(stats)
    else:
        print("[Demo] Would show user statistics here")
    
    # Close the pool
    logger.info("Closing database connection...")
    db.close()
    
    logger.info("=" * 60)
    logger.info("Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
