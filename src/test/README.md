# Test Suite

This directory contains all tests for the LLM PII Governance Engine, organized by concern.

---

## 📂 Test Structure

```text
test/
├── config/               # Shared test configuration (pytest settings, env overrides)
├── utils/                # Shared test utilities and helper functions
├── conftest.py           # Global pytest fixtures (config, Spark session, DB client)
├── scanner_isolation/    # Unit tests: Regex & LLM scanners in isolation
├── policy_engine/        # Unit & compliance tests for masking logic
├── e2e/                  # End-to-end scoring tests (full pipeline)
├── performance/          # Latency & throughput benchmarks
└── test_generator/       # Helpers for generating synthetic test data
```

---

## 🧪 Test Suites

### `scanner_isolation/` — Scanner Unit Tests

Tests each scanner independently, without Spark or database dependencies.

| File | What it tests |
| :--- | :--- |
| `test_regex_scanner.py` | Regex pattern matching, confidence score calculation, edge cases (empty data, mixed data) |
| `test_llm_scanner.py` | LLM prompt construction, response parsing, retry logic, mock LLM provider |

```bash
pytest src/test/scanner_isolation/
```

---

### `policy_engine/` — Masking Compliance Tests

Validates that masking rules are applied correctly and consistently per role.

| File | What it tests |
| :--- | :--- |
| `test_masking_compliance.py` | All masking rules (`HASH_MASK`, `PARTIAL_MASK`, `REDACTED_MASK`, `NULLIFY_MASK`) against known inputs |
| `test_dynamic_update.py` | Behaviour when policies are updated dynamically in the DB |

```bash
pytest src/test/policy_engine/
```

---

### `e2e/` — End-to-End Scoring Tests

Runs the full AI Governance pipeline (scan → metadata write → compare) on a controlled dataset and measures the scanner's accuracy (precision, recall, F1).

| File | What it tests |
| :--- | :--- |
| `test_e2e_score.py` | Full pipeline scoring against a labelled ground-truth dataset |

```bash
pytest src/test/e2e/
```

---

### `performance/` — Latency & Throughput Benchmarks

Measures the performance characteristics of the system under load.

| File | What it measures |
| :--- | :--- |
| `test_governance_duration.py` | End-to-end governance scan duration per table |
| `test_get_mask_columns_latency.py` | Latency of policy lookup queries from PostgreSQL |
| `test_policy_overhead.py` | Overhead introduced by masking on Spark DataFrame operations |

```bash
pytest src/test/performance/
```

---

## 🚀 Running Tests

### All tests

```bash
pytest src/test/
```

### With verbose output

```bash
pytest src/test/ -v
```

### A specific file

```bash
pytest src/test/scanner_isolation/test_regex_scanner.py
```

### With coverage (if pytest-cov is installed)

```bash
pytest src/test/ --cov=src --cov-report=term-missing
```

---

## ⚙️ Fixtures (`conftest.py`)

The root `conftest.py` provides shared fixtures available to all test suites:

| Fixture | Scope | Depends On | Description |
| :--- | :--- | :--- | :--- |
| `test_config` | `session` | — | Loads the **test** config via `load_test_config()` and sets `AWS_REGION` env var. Used by most other fixtures. |
| `spark_session` | `session` | `test_config` | Creates a `SparkSession` with Iceberg + JDBC catalog configured against the test environment. Automatically stopped after the session. |
| `prod_config` | `session` | — | Loads the **production** app config via `load_config()`. Used by tests that need to run against the production environment (e.g. e2e scoring). |
| `pg_client` | `session` | `test_config` | Creates a `PostgresClient` connected to the test database. Shared across all tests in the session. |
| `policy_yaml` | `function` | — | Loads `test_policy.yml` (or a custom path) as a Python dict. Used by policy engine tests to inject masking policy fixtures without hitting the DB. |
| `llm_scanner` | `function` | `test_config` | Instantiates a `LLMTableScanner` backed by the configured LLM provider. Used by scanner isolation tests to call the real LLM API against controlled inputs. |

