import os
from pathlib import Path

import pytest
import yaml

from src.core.postgres.postgres_client import PostgresClient
from src.core.spark.spark_builder import get_spark_iceberg_jdbc
from src.llm.factory import LLMFactory
from src.modules.ai_governance.llm_scanner import LLMTableScanner
from src.test.config.test_loader import load_test_config


@pytest.fixture(scope="session")
def test_config():
    config = load_test_config()
    os.environ["AWS_REGION"] = config["storage"]["minio"]["region"]
    return config

@pytest.fixture(scope="session")
def spark_session(test_config):
    spark = get_spark_iceberg_jdbc(test_config)
    yield spark
    spark.stop()

@pytest.fixture(scope="session")
def pg_client(test_config):
    client = PostgresClient(test_config)
    yield client

@pytest.fixture(scope="function")
def policy_yaml(policy_yaml_path = None):
    if not policy_yaml_path:
        policy_yaml_path = Path(__file__).parent / "test_policy.yml"
    with open(policy_yaml_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
    return content

@pytest.fixture(scope="function")
def llm_scanner(test_config):
    llm_provider = LLMFactory.get_llm_provider(test_config)
    max_retries = test_config["llm"].get("max_retries", 3)
    scanner = LLMTableScanner(llm_provider, max_retries)

    return scanner


