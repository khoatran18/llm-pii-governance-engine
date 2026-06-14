from pyspark.sql import SparkSession

from src.config.loader import load_config

PACKAGES = [
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "org.postgresql:postgresql:42.7.1",
    "org.apache.iceberg:iceberg-aws-bundle:1.6.1",
]

def get_base_spark(app_name: str):
    return SparkSession.builder.appName(app_name)

def get_spark_iceberg_rest(config: dict):
    spark_cfg = config.get("spark", {})
    minio_cfg = config.get("storage", {}).get("minio", {})
    catalog_name = spark_cfg["iceberg_catalog_name"]
    app_name = spark_cfg["load_job_name"]

    spark = (get_base_spark(app_name)
            .master(spark_cfg["master_url"])
            .config("spark.jars.packages", ",".join(PACKAGES))
            .config("spark.executor.memory", spark_cfg["executor_memory"])
            .config("spark.driver.memory", spark_cfg["driver_memory"])
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
            .config(f"spark.sql.catalog.{catalog_name}", "org.apache.iceberg.spark.SparkSessionCatalog")
            .config(f"spark.sql.catalog.{catalog_name}.type", "rest")
            .config(f"spark.sql.catalog.{catalog_name}.uri", "http://iceberg-rest:8181")
            .config(f"spark.sql.catalog.{catalog_name}.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
            .config(f"spark.sql.catalog.{catalog_name}.warehouse", minio_cfg["bucket_warehouse"])
            .config(f"spark.sql.catalog.{catalog_name}.s3.endpoint", minio_cfg[ "endpoint"])
            .config(f"spark.sql.catalog.{catalog_name}.s3.path-style-access", "true")
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            .config("spark.hadoop.fs.s3a.endpoint", minio_cfg["endpoint"])
            .config("spark.hadoop.fs.s3a.access.key", minio_cfg["access_key"])
            .config("spark.hadoop.fs.s3a.secret.key", minio_cfg["secret_key"])
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
    )

    return spark.getOrCreate()


def get_spark_iceberg_jdbc(config: dict):
    spark_cfg = config.get("spark", {})
    minio_cfg = config.get("storage", {}).get("minio", {})

    postgres_cfg = config.get("database", {}).get("postgres", {})
    catalog_name = spark_cfg["iceberg_catalog_name"]
    app_name = spark_cfg["load_job_name"]

    spark = (get_base_spark(app_name)
                    .master(spark_cfg["master_url"])

                    .config("spark.jars.packages", ",".join(PACKAGES))
                    .config("spark.executor.memory", spark_cfg["executor_memory"])
                    .config("spark.driver.memory", spark_cfg["driver_memory"])
                    .config("spark.executor.cores", spark_cfg["executor_cores"])
                    .config("spark.cores.max", spark_cfg["cores_max"])
                    .config("spark.cleaner.periodicGC.interval", "1min")
                    .config("spark.local.dir", "/tmp/spark-temp")
                    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")

                    # Metadata layer via JDBC
                    .config(f"spark.sql.catalog.{catalog_name}", "org.apache.iceberg.spark.SparkCatalog")
                    .config(f"spark.sql.catalog.{catalog_name}.catalog-impl", "org.apache.iceberg.jdbc.JdbcCatalog")

                    .config(f"spark.sql.catalog.{catalog_name}.uri",postgres_cfg["uri"])
                    .config(f"spark.sql.catalog.{catalog_name}.jdbc.user", postgres_cfg["user"])
                    .config(f"spark.sql.catalog.{catalog_name}.jdbc.password", postgres_cfg["password"])

                    # S3FileIO configuration (Physical storage layer - AWS Java SDK v2)
                    .config(f"spark.sql.catalog.{catalog_name}.warehouse", minio_cfg["bucket_warehouse"])
                    .config(f"spark.sql.catalog.{catalog_name}.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
                    .config(f"spark.sql.catalog.{catalog_name}.s3.endpoint", minio_cfg["endpoint"])
                    .config(f"spark.sql.catalog.{catalog_name}.s3.path-style-access", "true")
                    .config(f"spark.sql.catalog.{catalog_name}.s3.region", minio_cfg["region"])
                    .config(f"spark.sql.catalog.{catalog_name}.s3.access-key-id", minio_cfg["access_key"])
                    .config(f"spark.sql.catalog.{catalog_name}.s3.secret-access-key", minio_cfg["secret_key"])

                    # S3 configuration (Backward compatibility - AWS Java SDK v1)
                    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
                    .config("spark.hadoop.fs.s3a.endpoint", minio_cfg["endpoint"])
                    .config("spark.hadoop.fs.s3a.access.key", minio_cfg["access_key"])
                    .config("spark.hadoop.fs.s3a.secret.key", minio_cfg["secret_key"])
                    .config("spark.hadoop.fs.s3a.path.style.access", "true")
             )

    return spark.getOrCreate()

#
# def get_spark_iceberg_rest(app_name: str):
#     # Đọc lại config để lấy đúng tên catalog từ file yaml/json của bạn
#     # Giả sử config của bạn trả về tên catalog (ví dụ: 'my_catalog' hoặc 'lakehouse')
#     # Ở đây tôi ví dụ tên catalog cấu hình là 'my_catalog'
#
#     SUBMIT_PACKAGES = (
#         "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,"
#         "org.apache.hadoop:hadoop-aws:3.3.4"
#     )
#
#     builder = SparkSession.builder \
#         .appName(app_name) \
#         .config("spark.jars.packages", SUBMIT_PACKAGES) \
#         .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
#
#     # 🌟 ĐIỂM QUAN TRỌNG NHẤT: Trói chặt Session Catalog mặc định vào Iceberg REST
#     # Thay vì để trống khiến Spark tự tạo Hive nhúng, ta ép nó dùng REST luôn
#     builder = builder \
#         .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \
#         .config("spark.sql.catalog.spark_catalog.catalog-impl", "org.apache.iceberg.rest.RESTCatalog") \
#         .config("spark.sql.catalog.spark_catalog.uri", "http://iceberg-rest:8181")
#
#     # 🌟 ĐIỂM THỨ 2: Cấu hình chính xác Custom Catalog trùng với config['spark']['iceberg_catalog_name']
#     # Phải dùng dấu gạch ngang '-' cho catalog-impl và io-impl
#     catalog_name = "my_catalog"  # Hãy thay bằng tên chính xác trong config của bạn nếu cần
#
#     builder = builder \
#         .config(f"spark.sql.catalog.{catalog_name}", "org.apache.iceberg.spark.SparkCatalog") \
#         .config(f"spark.sql.catalog.{catalog_name}.catalog-impl", "org.apache.iceberg.rest.RESTCatalog") \
#         .config(f"spark.sql.catalog.{catalog_name}.uri", "http://iceberg-rest:8181") \
#         .config(f"spark.sql.catalog.{catalog_name}.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
#         .config(f"spark.sql.catalog.{catalog_name}.s3.endpoint", "http://minio:9000") \
#         .config(f"spark.sql.catalog.{catalog_name}.s3.path-style-access", "true")
#
#     # Cấu hình s3a cho core Hadoop
#     builder = builder \
#         .config("spark.hadoop.fs.s3a.access.key", "minio") \
#         .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
#         .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
#         .config("spark.hadoop.fs.s3a.path.style.access", "true") \
#         .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
#
#     return builder.getOrCreate()