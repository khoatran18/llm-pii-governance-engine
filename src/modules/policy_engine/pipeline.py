import logging

from pyspark.sql import DataFrame

from local.posgres_init_example import PostgresClient
from src.config.logging import setup_logging
from src.core.dtos.enums import UserRole
from src.modules.ai_governance.utils import get_table_fqn
from src.modules.policy_engine.data_masker import DataMasker

setup_logging()
logger = logging.getLogger(__name__)
policy_engine_logger = logging.getLogger("policy_engine")

class PolicyEngine:
    def __init__(self, spark_session, pg_client: PostgresClient, data_masker: DataMasker, config):
        self.spark = spark_session
        self.pg_client = pg_client
        self.masker = data_masker
        self.config = config

    def _get_masking_policies(self, table_name: str, user_role: UserRole, target_columns: list):
        """
        Get masking policies for a specific table and user role
        """
        sql_policy = """
            SELECT t.table_name, c.column_name, ap.masking_rule
            FROM columns_metadata c
                JOIN tables_metadata t ON c.table_id = t.table_id
                JOIN access_policies ap ON c.sensitivity_level = ap.sensitivity_level
            WHERE ap.role_name = :user_role
        """
        params = {
            "user_role": user_role.value,
        }

        if table_name and table_name.strip() != "":
            sql_policy += " AND t.table_name = :table_name"
            params["table_name"] = table_name
        if target_columns:
            sql_policy += " AND c.column_name IN :target_columns"
            params["target_columns"] = tuple(target_columns)

        # policy_engine_logger.info(f"SQL Policy: {sql_policy}")
        return self.pg_client.execute_query(sql_policy, params)

    def _apply_dynamic_masking(self, df_raw: DataFrame, policies: list):
        """
        Get through the policies and apply masking to the data
        Policies: [{'column_name': 'col1', 'masking_rule': 'HASH'}, ...]
        """
        df_secure = df_raw
        actual_cols = df_raw.columns

        column_rule = {
            row['column_name']: row['masking_rule'] for row in policies
        }

        for col_name in actual_cols:
            if col_name in column_rule:
                masking_rule = column_rule[col_name]
                policy_engine_logger.info(f"Applying masking to column {col_name} with rule {masking_rule}")
                df_secure = self.masker.apply_masking(df_secure, col_name, masking_rule)
        return df_secure

    def execute_secure_pipeline(
            self,
            table_name: str,
            selected_columns: list,
            user_role: UserRole,
    ):
        """
        Full secure pipeline
        :param table_name: Name of the table
        :param selected_columns: List of columns to be masked
        :param user_role: Role of the user
        :return: List of masked DataFrame objects
        """
        result_dataframes = []
        table_name_clean = table_name.strip() if table_name else ""

        # If request to scan all tables
        if table_name_clean == "":
            logger.info("Request to scan all tables ...")
            sql_all_tables = "SELECT table_name FROM tables_metadata;"
            tables_rows = self.pg_client.execute_query(sql_all_tables)
            tables_to_process = [row['table_name'] for row in tables_rows]

            actual_select_fields = ["*"]
        # If request to scan specific table
        else:
            tables_to_process = [table_name_clean]
            if selected_columns is None or len(selected_columns) == 0 or "*" in selected_columns:
                actual_select_fields = ["*"]
            else:
                actual_select_fields = selected_columns

        # Iterate through tables
        for t_name in tables_to_process:
            try:
                # Read raw data
                logger.info(f"Processing table: {t_name}")
                table_fqn = get_table_fqn(self.config, t_name)
                df_raw = self.spark.read.format("iceberg") \
                    .option("inferSchema", "false") \
                    .load(table_fqn) \
                    .select(*actual_select_fields)

                # Get masking policies
                policies = self._get_masking_policies(
                    t_name,
                    user_role,
                    selected_columns
                )

                # Apply masking
                df_secure = self._apply_dynamic_masking(df_raw, policies)
                result_dataframes.append(df_secure)
            except Exception as e:
                logger.error(f"Error processing table {t_name}: {e}")
                continue

        return result_dataframes

