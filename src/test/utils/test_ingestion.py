import pytest

from src.modules.ingestion.ingestion_execute import ingestion_execution


def test_data_ingestion(test_config):
    print("Test data ingestion")

    test_csv_folder = f"{test_config['spark']['csv_folder']}"
    test_table_name = test_config["test_suite"]["table_name"]
    expected_rows = test_config["test_suite"]["total_rows"]

    try:
        ingestion_execution(csv_folder=test_csv_folder)
    except Exception as e:
        pytest.fail(f"Failed to ingest data from {test_csv_folder}")

# pytest src/test/utils/test_ingestion.py -v -s
