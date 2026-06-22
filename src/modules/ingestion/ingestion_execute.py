import argparse
import logging
import subprocess
import sys

from src.config.loader import load_config
from src.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def ingestion_execution(csv_folder: str = None, config: dict = None):
    logger.info("Starting Ingestion Execution...")
    if not config:
        try:
            config = load_config()
            logger.info("Config loaded successfully.")
        except Exception as e:
            logger.error("Failed to load config.", exc_info=True)
            return

    logger.info("Starting Spark job...")
    container_name = config["spark"]["master_container_name"]
    master_url = config["spark"]["master_url"]
    d_memory = config["spark"].get("driver_memory", "1g")
    e_memory = config["spark"].get("executor_memory", "1g")
    e_cores = str(config["spark"].get("executor_cores", 1))
    c_max = str(config["spark"].get("cores_max", 2))
    e_instances = str(config["spark"].get("executor_instances", 2))

    cmd = [
        "docker",  "exec", container_name, "/bin/bash",
        "/opt/spark/bin/spark-submit", "--master", master_url,
        "--deploy-mode", "client",
        "--driver-memory", d_memory,
        "--executor-memory", e_memory,
        "--executor-cores", e_cores,
        "--total-executor-cores", c_max,
        "--num-executors", e_instances,
        "--packages", ",".join([
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1",
            "org.apache.iceberg:iceberg-aws-bundle:1.6.1",
            "org.apache.hadoop:hadoop-aws:3.3.4",
            "org.postgresql:postgresql:42.7.1"
        ]),
        "/app/src/modules/ingestion/ingestion_main.py"
    ]

    if csv_folder:
        logger.info(f"Running Spark job with CSV folder: {csv_folder}")
        cmd.extend(["--csv_folder", csv_folder])

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    ) as proc:
        for line in proc.stdout:
            logger.info(line.strip())
    if proc.returncode != 0:
        logger.error(f"Spark job failed with exit code {proc.returncode}")
        raise Exception(f"Spark job failed with exit code {proc.returncode}")
    logger.info("Spark job completed successfully.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion Main")
    parser.add_argument("--csv_folder", type=str, default=None, help="Path to the CSV folder")

    args = parser.parse_args()
    ingestion_execution(csv_folder=args.csv_folder)