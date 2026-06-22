# Gen test data with 20 columns, 5000 rows
import csv
import json
import logging
import random
import shutil
from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession

from src.config.logging import setup_logging
from src.core.dtos.enums import SensitivityTag
from src.core.spark.spark_builder import get_spark_iceberg_jdbc
from src.modules.ingestion.generator import rand, make_cccd, make_phone, make_email, make_bhyt_no, make_full_name, \
    make_address, make_salary, make_dob, make_id, make_ip, make_device_fp, make_amount
from src.test.config.test_loader import load_test_config

setup_logging()
logger = logging.getLogger(__name__)
test_logger = logging.getLogger("test")


OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "test"
seed = 42
random.seed(seed)

def make_status_code(): return rand(["200", "400", "404", "500"]), SensitivityTag.NONE
def make_is_active(): return rand(["true", "false"]), SensitivityTag.NONE
def make_retry_count(): return str(random.randint(0, 5)), SensitivityTag.NONE

GENERATOR_MAPPING = {
    "RESIDENT_ID": make_cccd,
    "PHONE": make_phone,
    "EMAIL": make_email,
    "HEALTH_INSURANCE_ID": make_bhyt_no,
    "NAME": make_full_name,
    "ADDRESS": make_address,
    "SALARY": make_salary,
    "DOB": make_dob,
    # For SensitiveTag.NONE
    "sys_record_id": lambda: make_id("SYS"),
    "device_ip_address": make_ip,
    "user_agent_hash": make_device_fp,
    "status_code": make_status_code,
    "is_active": make_is_active,
    "retry_count": make_retry_count,
    "tx_amount": make_amount
}

NOISE_GENERATOR = [
    lambda: make_id("NOISE"),
    make_ip,
    make_device_fp,
    make_amount
]

def normalize_value_and_tag(item) -> tuple:
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], SensitivityTag):
        return item
    return item, SensitivityTag.NONE

def generate_column_data(column_name: str, target_tag: str, match_percentage: int, total_rows: int) -> list:
    valid_count = int(total_rows * (match_percentage / 100))
    noise_count = total_rows - valid_count

    column_values = []

    # Generate valid values
    for _ in range(valid_count):
        if column_name in GENERATOR_MAPPING:
            column_values.append(GENERATOR_MAPPING[column_name]())
        else:
            gen_fn = GENERATOR_MAPPING.get(target_tag, make_ip)
            if gen_fn.__name__ == "make_cccd":
                dob = make_dob()
                column_values.append(gen_fn(dob))
            elif gen_fn.__name__ == "make_email":
                name = make_full_name()
                column_values.append(gen_fn(name))
            else:
                column_values.append(gen_fn())

    # Generate noise values
    for _ in range(noise_count):
        column_values.append(random.choice(NOISE_GENERATOR)())

    random.shuffle(column_values)

    return column_values

def main():
    test_config = load_test_config()
    test_data_config = test_config["test_suite"]

    table_name = test_data_config["table_name"]
    total_rows = test_data_config["total_rows"]
    columns_config = test_data_config["columns_config"]

    test_logger.info(f"Generating test data for table: {table_name}")

    columns_data_store = {}
    actual_tag_distribution = {}

    for col in columns_config:
        col_name = col["column_name"]
        target_tag = col["sensitivity_tag"]
        match_pct = col["match_percentage"]

        raw_column_items = generate_column_data(col_name, target_tag, match_pct, total_rows)
        columns_data_store[col_name] = raw_column_items

    fieldnames = [col["column_name"] for col in columns_config]
    csv_rows = []

    for row_idx in range(total_rows):
        row_data = {}
        for col in columns_config:
            col_name = col["column_name"]
            raw_item = columns_data_store[col_name][row_idx]
            val, _ = normalize_value_and_tag(raw_item)

            if isinstance(val, (date, )):
                val = val.isoformat()
            row_data[col_name] = val
        csv_rows.append(row_data)

    csv_path = OUTPUT_DIR / f"{table_name}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    columns_metadata = []
    for col in columns_config:
        tag_enum = SensitivityTag[col["sensitivity_tag"]]
        columns_metadata.append({
            "column_name": col["column_name"],
            "sensitivity_tag": tag_enum,
            "sensitivity_level": tag_enum.sensitivity_level
        })

    metadata = {
        "table_name": f"{table_name}.csv",
        "total_columns": len(fieldnames),
        "total_rows": total_rows,
        "columns": columns_metadata
    }

    meta_path = OUTPUT_DIR / "metadata" / f"{table_name}_metadata.json"
    if not meta_path.parent.exists():
        meta_path.parent.mkdir(parents=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    test_logger.info(f"Test data generated successfully: {csv_path}")

# For 5 000 000 rows
def generate_column_data_stream(columns_config, total_rows: int) -> dict:
    """
    Chuẩn bị trước mảng phân phối (Mask) True/False để giữ nguyên cơ chế
    tính chỉ số chuẩn (match_percentage chính xác 100%) mà không làm tăng bộ nhớ.
    """
    column_masks = {}
    for col in columns_config:
        col_name = col["column_name"]
        match_pct = col["match_percentage"]

        valid_count = int(total_rows * (match_pct / 100))
        noise_count = total_rows - valid_count

        mask = [True] * valid_count + [False] * noise_count
        random.shuffle(mask)
        column_masks[col_name] = mask

    return column_masks


def generate_row_stream(columns_config, column_masks: dict, total_rows: int):
    """
    Sử dụng yield để sinh dữ liệu thực tế và nhả ra theo từng dòng (Stream),
    kèm log tiến độ sau mỗi 10.000 dòng.
    """
    for row_idx in range(total_rows):
        # Thêm log tiến độ cứ mỗi 10.000 dòng
        if (row_idx + 1) % 10000 == 0:
            test_logger.info(f"Generated {row_idx + 1}/{total_rows} rows...")

        row_data = {}
        for col in columns_config:
            col_name = col["column_name"]
            target_tag = col["sensitivity_tag"]

            is_valid = column_masks[col_name][row_idx]

            if is_valid:
                if col_name in GENERATOR_MAPPING:
                    raw_item = GENERATOR_MAPPING[col_name]()
                else:
                    gen_fn = GENERATOR_MAPPING.get(target_tag, make_ip)
                    if gen_fn.__name__ == "make_cccd":
                        dob = make_dob()
                        raw_item = gen_fn(dob)  # ĐÃ SỬA: Xóa bỏ dòng append lỗi ở đây
                    elif gen_fn.__name__ == "make_email":
                        name = make_full_name()
                        raw_item = gen_fn(name)
                    else:
                        raw_item = gen_fn()
            else:
                raw_item = random.choice(NOISE_GENERATOR)()

            val, _ = normalize_value_and_tag(raw_item)
            if isinstance(val, (date,)):
                val = val.isoformat()

            row_data[col_name] = val

        yield row_data


def main_stream():
    test_config = load_test_config()
    test_data_config = test_config["test_suite"]

    table_name = test_data_config["table_name"]
    total_rows = test_data_config["total_rows"]
    columns_config = test_data_config["columns_config"]

    test_logger.info(f"Generating test data for table: {table_name} (Streaming Mode)")

    column_masks = generate_column_data_stream(columns_config, total_rows)

    fieldnames = [col["column_name"] for col in columns_config]
    csv_path = OUTPUT_DIR / f"{table_name}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        buffer = []
        for row_data in generate_row_stream(columns_config, column_masks, total_rows):
            buffer.append(row_data)

            # Giữ buffer 20.000 dòng để tối ưu I/O ghi file xuống đĩa
            if len(buffer) >= 20000:
                writer.writerows(buffer)
                buffer = []

        if buffer:
            writer.writerows(buffer)

    # --- Phần sinh metadata phía dưới giữ nguyên ---
    columns_metadata = []
    for col in columns_config:
        tag_enum = SensitivityTag[col["sensitivity_tag"]]
        columns_metadata.append({
            "column_name": col["column_name"],
            "sensitivity_tag": tag_enum,
            "sensitivity_level": tag_enum.sensitivity_level
        })

    metadata = {
        "table_name": f"{table_name}.csv",
        "total_columns": len(fieldnames),
        "total_rows": total_rows,
        "columns": columns_metadata
    }

    meta_path = OUTPUT_DIR / "metadata" / f"{table_name}_metadata.json"
    if not meta_path.parent.exists():
        meta_path.parent.mkdir(parents=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    test_logger.info(f"Test data generated successfully: {csv_path}")


def main_stream_spark():
    test_config = load_test_config()
    test_data_config = test_config["test_suite"]

    table_name = test_data_config["table_name"]
    total_rows = test_data_config["total_rows"]
    columns_config = test_data_config["columns_config"]

    test_logger.info(f"Generating test data for table: {table_name} (Spark Processing Mode)")

    # 1. Khởi tạo Spark Session với cấu hình tối ưu tài nguyên theo yêu cầu
    spark = get_spark_iceberg_jdbc(test_config)

    # 2. Sinh mảng trạng thái (giữ nguyên cơ chế chỉ số chuẩn của bạn)
    column_masks = generate_column_data_stream(columns_config, total_rows)

    # 3. Tạo một Python generator cung cấp dữ liệu theo dòng
    row_generator = generate_row_stream(columns_config, column_masks, total_rows)

    # Đường dẫn file đích (Giữ nguyên logic đường dẫn cũ của bạn)
    csv_path = OUTPUT_DIR / f"{table_name}.csv"

    # Đường dẫn tạm thời để Spark ghi song song
    temp_spark_dir = OUTPUT_DIR / f"{table_name}_spark_tmp"

    try:
        # 4. Nạp generator vào Spark DataFrame
        # Spark sẽ tự tạo Schema dựa trên cấu trúc dict của row_data
        df = spark.createDataFrame(row_generator)

        # 5. Coalesce về 1 để gom thành 1 file duy nhất và ghi ra thư mục tạm
        test_logger.info(f"Spark is writing data to temporary directory...")
        df.coalesce(1).write.mode("overwrite").option("header", "true").csv(str(temp_spark_dir))

        # 6. Xử lý đổi tên file của Spark về đúng đường dẫn csv_path nguyên bản
        # Tìm file dạng part-00000...csv nằm trong thư mục tạm của Spark
        spark_part_file = next(temp_spark_dir.glob("part-*.csv"))

        # Nếu file cũ đã tồn tại thì xóa đi trước khi đè file mới vào
        if csv_path.exists():
            csv_path.unlink()

        # Di chuyển và đổi tên thành file đích chuẩn của bạn
        shutil.move(str(spark_part_file), str(csv_path))
        test_logger.info(f"Successfully moved and renamed Spark output to: {csv_path}")

    finally:
        # Dọn dẹp thư mục tạm của Spark và tắt Session
        if temp_spark_dir.exists():
            shutil.rmtree(temp_spark_dir)
        spark.stop()

    # --- 100% Phần sinh metadata phía dưới giữ nguyên của bạn ---
    fieldnames = [col["column_name"] for col in columns_config]
    columns_metadata = []
    for col in columns_config:
        tag_enum = SensitivityTag[col["sensitivity_tag"]]
        columns_metadata.append({
            "column_name": col["column_name"],
            "sensitivity_tag": tag_enum,
            "sensitivity_level": tag_enum.sensitivity_level
        })

    metadata = {
        "table_name": f"{table_name}.csv",
        "total_columns": len(fieldnames),
        "total_rows": total_rows,
        "columns": columns_metadata
    }

    meta_path = OUTPUT_DIR / "metadata" / f"{table_name}_metadata.json"
    if not meta_path.parent.exists():
        meta_path.parent.mkdir(parents=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    test_logger.info(f"Test data and metadata generated successfully!")

def test_generator():
    main_stream()


