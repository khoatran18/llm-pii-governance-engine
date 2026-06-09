import logging
import subprocess

from src.config.loader import load_config
from src.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def main():
    try:
        config = load_config()
        logger.info("Config loaded successfully.")
    except Exception as e:
        logger.error("Failed to load config.", exc_info=True)
        return

    logger.info("Starting Spark job...")
    container_name = config["spark"]["master_container_name"]
    master_url = config["spark"]["master_url"]
    cmd = [
        "docker",  "exec", container_name, "/bin/bash",
        "/opt/spark/bin/spark-submit", "--master", master_url,
        "--deploy-mode", "client",
        "--packages", ",".join([
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1",
            "org.apache.iceberg:iceberg-aws-bundle:1.6.1",
            "org.apache.hadoop:hadoop-aws:3.3.4",
            "org.postgresql:postgresql:42.7.1"
        ]),
        "/app/src/modules/ingestion/ingestion_main.py"
    ]

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
    main()