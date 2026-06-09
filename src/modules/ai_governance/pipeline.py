import logging

from src.config.logging import setup_logging
from src.core.dtos.models import ColumnScanResult
from src.core.postgres.postgres_client import PostgresClient
from src.llm.base import BaseLLMProvider
from src.modules.ai_governance.llm_scanner import LLMTableScanner
from src.modules.ai_governance.regex_scanner import calculate_regex_confidence_score
from src.modules.ai_governance.governance_repository import GovernanceRepository
from src.modules.ai_governance.table_sampler import IcebergTableSampler
from src.modules.ai_governance.utils import build_llm_request_payload, arbitrate_hybrid_results, llm_logger

setup_logging()
logger = logging.getLogger(__name__)

class AIGovernancePipeline:
    """
    Pipeline for AI Governance
    """
    def __init__(
            self,
            iceberg_sampler: IcebergTableSampler,
            llm_scanner: LLMTableScanner,
            pg_client: PostgresClient,
            config: dict,
    ):
        self.iceberg_sampler = iceberg_sampler
        self.llm_scanner = llm_scanner
        self.repo = GovernanceRepository(pg_client, config)
        self.confidence_threshold = config["governance"]["confidence_threshold"]
        self.regex_sample_size = config["governance"]["regex_sample_size"]
        self.llm_sample_size = config["governance"]["llm_sample_size"]

    def execute_pipeline(self, table_name, table_fqn):
        logger.info(f"Executing AI Governance pipeline for table: {table_fqn}")

        # Register table metadata
        self.repo.register_table_to_metadata_store()

        # 1. Extract schema and sample data from Iceberg table
        logger.info(f"Extracting schema and sample data for table: {table_fqn} ...")
        iceberg_table_regex = self.iceberg_sampler.extract_table_schema_and_sampler(table_fqn, self.regex_sample_size)
        iceberg_table_llm = self.iceberg_sampler.extract_table_schema_and_sampler(table_fqn, self.llm_sample_size)

        table_id = self.repo.get_registered_table_id(table_name)

        # 2. Process regex and LLM outputs by column
        logger.info("Processing regex and LLM outputs by column ...")
        regex_processed_output = []
        regex_map_by_column = {}

        for col_id, col in enumerate(iceberg_table_regex):
            col_name = col["column_name"]
            # Regex processing and init llm input payload
            regex_json = calculate_regex_confidence_score(col_name, col["sample_data"], threshold=self.confidence_threshold)
            regex_json["sample_data"] = iceberg_table_llm[col_id]["sample_data"]

            regex_processed_output.append(regex_json)
            regex_map_by_column[col_name] = regex_json

        # 3. Create payload to LLM
        logger.info("Creating payload to LLM ...")
        llm_request_payload = build_llm_request_payload(table_name=table_name, regex_outputs=regex_processed_output)

        llm_logger.info("\n" + "=" * 40 + " [RAW LLM PAYLOAD] " + "=" * 40)
        llm_logger.info(llm_request_payload.model_dump_json(indent=2))
        llm_logger.info("=" * 100 + "\n")

        llm_response = self.llm_scanner.scan_table(llm_request_payload)

        if not llm_response or not llm_response.columns:
            logger.error("LLM response is empty or missing columns")
            raise RuntimeError("LLM response is empty or missing columns")

        llm_map_by_column = {col.column_name: col for col in llm_response.columns}

        # 4. Merge regex and LLM outputs
        logger.info("Merging regex and LLM outputs ...")
        for col_name, corresponding_regex in regex_map_by_column.items():
            corresponding_llm = llm_map_by_column.get(col_name)

            scan_result: ColumnScanResult = arbitrate_hybrid_results(
                column_name=col_name,
                regex_info=corresponding_regex,
                llm_output=corresponding_llm,
                confidence_score_threshold=self.confidence_threshold,
            )

            # Write to database
            self.repo.save_column_metadata(
                table_id=table_id,
                results=scan_result,
            )

            self.repo.save_governance_audit_log(
                table_id=table_id,
                table_name=table_name,
                results=scan_result,
            )


