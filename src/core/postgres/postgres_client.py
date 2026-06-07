import logging
import os
from pathlib import Path

from numba.core.ir import Raise
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.config.loader import load_config
from src.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class PostgresClient:
    def __init__(self, config):
        postgres_cfg = config.get("database", {}).get("postgres", {})

        self.connection_string = f"postgresql://{postgres_cfg['user']}:{postgres_cfg['password']}@{postgres_cfg['host']}:{postgres_cfg['port']}/{postgres_cfg['database']}"
        self.engine = None
        self._is_initialized = False

    def _initialize_db(self):
        init_sql_file = Path(__file__).parent / "init_db.sql"
        if not init_sql_file.exists():
            logger.error(f"Critical Error: Init SQL file not found at {init_sql_file}")
            raise FileNotFoundError(f"Missing required initialization script: {init_sql_file}")
        try:
            with open(init_sql_file, "r", encoding="utf-8") as f:
                sql_script = f.read()
            with self.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text(sql_script), {})
            self._is_initialized = True
            logger.info("SQL script executed successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise e

    def connect(self):
        self.engine = create_engine(
            self.connection_string,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        if not self._is_initialized:
            self._initialize_db()
        return self.engine

    def execute_non_query(self, sql_script: str, params: dict = {}) -> bool:
        """
        Execute a non-query SQL script, not returning any results.
        (CREATE TABLE, INSERT, UPDATE, DELETE, etc.))
        """
        if not self.engine:
            logger.info("Connecting to Postgres ...")
            self.connect()

        try:
            with self.engine.connect() as conn:
                with conn.begin(): # Commit if successful, Rollback if unsuccessful
                    conn.execute(text(sql_script), params)
            logger.info("SQL script executed successfully.")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error executing SQL script: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def execute_query(self, sql_script: str, params: dict = {}) -> list:
        """
        Use for SELECT queries
        Return a list of dictionaries
        """
        if not self.engine:
            logger.info("Connecting to Postgres ...")
            self.connect()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_script), params)
            return [dict(row) for row in result.mappings()]
        except SQLAlchemyError as e:
            logger.error(f"Error executing SQL script: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    def check_exist(self, sql_script: str, params: dict = {}):
        rows = self.execute_query(sql_script, params)
        return len(rows) > 0

    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            logger.info("Postgres connection closed.")