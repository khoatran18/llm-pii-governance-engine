# Core Module

Shared infrastructure layer providing reusable clients, builders, and data models consumed by all modules in the project.

---

## 📂 Module Structure

```text
core/
├── dtos/
│   ├── enums.py      # All enumerations: SensitivityTag, SensitivityLevel, UserRole, MaskingRule, etc.
│   └── models.py     # Pydantic data models for pipeline I/O
├── postgres/
│   └── postgres_client.py  # PostgresClient: connection, query, non-query, DB init
├── spark/
│   └── spark_builder.py    # SparkSession factory (Iceberg + JDBC or REST catalog)
└── __init__.py
```

---

## 📦 Sub-packages

### `dtos/` — Data Transfer Objects

Shared Pydantic models and enums used across all modules.

#### Enums (`enums.py`)

| Enum | Values | Used For |
| :--- | :--- | :--- |
| `SensitivityTag` | `RESIDENT_ID`, `PHONE`, `EMAIL`, `HEALTH_INSURANCE_ID`, `NAME`, `ADDRESS`, `SALARY`, `DOB`, `NONE` | Labelling PII column types |
| `SensitivityLevel` | `HIGH`, `MEDIUM`, `LOW`, `NONE` | Classifying severity of PII |
| `UserRole` | `ADMIN`, `ANALYST`, `AUDITOR` | Determining masking policy at query-time |
| `MaskingRule` | `HASH_MASK`, `PARTIAL_MASK`, `REDACTED_MASK`, `NULLIFY_MASK`, `CLEAR_TEXT` | Defining how a column is transformed |
| `DetectionMethod` | `REGEX`, `LLM`, `HYBRID` | Tracking which scanner produced the final result |
| `RegexStatus` | `SUCCESS`, `UNDETERMINED` | Regex scanner confidence outcome |
| `DetectionReason` | *(string enum)* | Human-readable explanation of arbitration decision |

Each `SensitivityTag` also exposes:
- `.sensitivity_level` → auto-derives the `SensitivityLevel` for that tag.
- `.severity_weight` → numeric weight used for arbitration tie-breaking.

#### Models (`models.py`)

Pydantic models define the contracts between pipeline stages:

| Model | Purpose |
| :--- | :--- |
| `TableMetadata` | Registered Iceberg table in the governance metadata store |
| `ColumnMetadata` | Final PII classification result for a single column |
| `ColumnScanInput` | Input sent to the LLM: column name + regex pre-analysis + sample data |
| `TableLLMScanRequest` | Full LLM request payload: determined + undetermined columns |
| `SingleColumnLLMOutput` | Single column result parsed from the LLM's JSON response |
| `TableLLMScanResponse` | Full LLM response, parsed and validated |
| `ColumnScanResult` | Final arbitrated result per column (used to write to DB) |
| `AccessPolicyMetadata` | Maps `role_name × sensitivity_level → masking_rule` |
| `GovernanceAuditLog` | Full audit record per scanned column |

---

### `postgres/` — PostgreSQL Client

`PostgresClient` wraps SQLAlchemy to provide a simple, connection-pooled interface.

#### Key methods

| Method | Description |
| :--- | :--- |
| `connect()` | Creates the SQLAlchemy engine and runs `init_db.sql` on first connection |
| `execute_non_query(sql, params)` | Runs INSERT / UPDATE / DELETE within an auto-commit transaction |
| `execute_query(sql, params)` | Runs SELECT and returns `List[dict]` |
| `check_exist(sql, params)` | Convenience wrapper: returns `True` if the query returns any rows |
| `disconnect()` | Disposes the connection pool |

#### DB Initialization

On first `connect()`, the client automatically runs `init_db.sql` (located next to `postgres_client.py`). This script creates all required tables if they don't exist:

- `tables_metadata`
- `columns_metadata`
- `access_policies`
- `governance_audit_logs`
- `policy_engine_audit_logs`

This means **no manual DB setup is needed** — the schema is bootstrapped automatically on first run.

#### Connection pooling

```python
engine = create_engine(
    connection_string,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # Validates connections before use
)
```

---

### `spark/` — SparkSession Builder

`spark_builder.py` provides factory functions to create a pre-configured `SparkSession` with all Iceberg and S3 (MinIO) settings applied.

#### `get_spark_iceberg_jdbc(config)` *(primary)*

The main builder used across all modules. Configures Spark with:
- **Iceberg JDBC Catalog** — uses PostgreSQL as the Iceberg metastore (no separate Iceberg REST server needed).
- **S3FileIO** — reads and writes Iceberg data files to MinIO via the AWS Java SDK v2 S3 interface.
- **S3A FileSystem** — backward-compatible Hadoop S3A connector for legacy MinIO access paths.

#### `get_spark_iceberg_rest(config)` *(alternative)*

Alternate builder for environments using a dedicated Iceberg REST Catalog (`iceberg-rest` service). Currently not used in production configuration.

#### Packages bundled at runtime

```python
PACKAGES = [
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1",
    "org.apache.hadoop:hadoop-aws:3.3.4",
    "org.postgresql:postgresql:42.7.1",
    "org.apache.iceberg:iceberg-aws-bundle:1.6.1",
]
```
