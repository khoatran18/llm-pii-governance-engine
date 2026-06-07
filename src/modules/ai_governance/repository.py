import logging
from pathlib import Path
from typing import Any

from src.config.logging import setup_logging
from src.core.dtos.models import ColumnScanResult
from src.core.postgres.postgres_client import PostgresClient
from src.modules.ai_governance.utils import get_all_table_fqn, get_all_table_name, get_table_fqn

setup_logging()
logger = logging.getLogger(__name__)

class GovernanceRepository:
    def __init__(self, pg_client: PostgresClient, config: dict):
        self.config = config
        self.db = pg_client

    def get_registered_table_id(self, table_name: str):
        """
        Check if the table is registered in the database
        """
        table_record = self.db.execute_query(
            "SELECT table_id FROM tables_metadata WHERE table_name = :table_name",
            {"table_name": table_name}
        )
        if not table_record:
            logger.error(f"Table {table_name} is not registered in the database.")
            raise ValueError(f"Table {table_name} is not registered in the database.")

        return table_record[0]["table_id"]

    def save_column_metadata(self, table_id: int, results: ColumnScanResult):
        """
        Upsert column metadata into the database
        """
        save_upsert_column = """
            INSERT INTO columns_metadata (table_id, column_name, sensitivity_tag, sensitivity_level, detection_method, confidence_score, reason)
            VALUES (:table_id, :column_name, :sensitivity_tag, :sensitivity_level, :detection_method, :confidence_score, :reason)
            ON CONFLICT (table_id, column_name) 
            DO UPDATE SET 
                sensitivity_tag = EXCLUDED.sensitivity_tag,
                sensitivity_level = EXCLUDED.sensitivity_level,
                detection_method = EXCLUDED.detection_method,
                confidence_score = EXCLUDED.confidence_score,
                updated_at = CURRENT_TIMESTAMP;
        """
        self.db.execute_non_query(save_upsert_column, {
            "table_id": table_id,
            "column_name": results.column_name,
            "sensitivity_tag": results.sensitivity_tag,
            "sensitivity_level": results.sensitivity_level,
            "detection_method": results.detection_method,
            "confidence_score": results.confidence_score,
            "reason": results.reason
        })

    def save_governance_audit_log(self, table_id: int, table_name: str, results: ColumnScanResult):
        """
        Insert audit log into the database
        """
        sql_insert_audit = """
           INSERT INTO governance_audit_logs
           (table_id, table_name, column_name, detection_method, sensitivity_tag, sensitivity_level, \
            confidence_score, reason)
           VALUES (:table_id, :table_name, :column_name, :detection_method, :sensitivity_tag, :sensitivity_level, \
                   :confidence_score, :reason); 
       """
        self.db.execute_non_query(sql_insert_audit, {
            "table_id": table_id,
            "table_name": table_name,
            "column_name": results.column_name,
            "detection_method": results.detection_method,
            "sensitivity_tag": results.sensitivity_tag,
            "sensitivity_level": results.sensitivity_level,
            "confidence_score": results.confidence_score,
            "reason": results.reason
        })

    def register_table_to_metadata_store(self):
        logger.info("Registering tables to metadata store ...")
        table_names = get_all_table_name(self.config)
        for table_name in table_names:
            logger.info(f"Registering table: {table_name} ...")
            table_fqn = get_table_fqn(self.config, table_name)
            sql_register = """
                   INSERT INTO tables_metadata (table_name, iceberg_path)
                   VALUES (:table_name, :iceberg_path) ON CONFLICT (table_name) DO NOTHING; 
               """
            self.db.execute_non_query(
                sql_register,
                {"table_name": table_name, "iceberg_path": table_fqn}
            )
        logger.info("Tables registered to metadata store.")







