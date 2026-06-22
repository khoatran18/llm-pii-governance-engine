# LLM Module

This module provides a **provider-agnostic LLM abstraction layer** used by the AI Governance pipeline to perform semantic PII classification on Iceberg table columns.

---

## 📂 Module Structure

```text
llm/
├── base.py       # Abstract base class: BaseLLMProvider
├── factory.py    # LLMFactory: instantiates the correct provider from config
├── providers.py  # Concrete implementations: OpenAIProvider, DeepSeekProvider
├── prompts.py    # Centralized prompt templates (GovernanceLLMPrompts)
└── __init__.py
```

---

## ⚙️ Design

The module follows the **Factory + Strategy** pattern:

```
app_config.yml          LLMFactory              BaseLLMProvider (ABC)
 llm.provider: "deepseek"  ──▶  DeepSeekProvider ──▶  get_response(prompt) -> str
                            or   OpenAIProvider
```

- **`BaseLLMProvider`** — Abstract base class defining the interface (`get_response`). Reads shared config (model, temperature, max_tokens).
- **`LLMFactory.get_llm_provider(config)`** — Reads `config["llm"]["provider"]` and returns the appropriate provider instance. Adding a new provider only requires a new class + one `elif` in the factory.
- **`providers.py`** — Both `OpenAIProvider` and `DeepSeekProvider` use the `openai` Python SDK. DeepSeek is accessed via a compatible OpenAI-format endpoint (`https://api.deepseek.com/v1`).

---

## 📝 Prompt Engineering (`prompts.py`)

The `GovernanceLLMPrompts` class centralises all prompt templates.

### `BATCH_TABLE_SCAN_PROMPT`

The main prompt used to scan a full table. It is structured in two semantic categories:

| Category | Content |
| :--- | :--- |
| **CATEGORY 1 — DETERMINED** | Columns already classified by Regex with high confidence. Sent as **anchor context** for the LLM to understand the table domain. |
| **CATEGORY 2 — UNDETERMINED** | Columns where Regex failed or scored below threshold. The LLM must classify these using semantic reasoning. |

**Key prompt design choices:**
- **Data-First Rule:** The LLM is explicitly instructed to prioritize actual sample data patterns over column names — because column names can be obfuscated (e.g., `c01`, `val_02`, `m_val`).
- **Conservative Classification:** Default is `NONE` unless data provides clear, unambiguous PII evidence.
- **Majority Vote Rule:** If fewer than 50% of sample rows match a PII pattern, the column must be tagged `NONE`.
- **Confidence Gate:** LLM must only assign a tag if its `confidence_score > 0.7`.
- **Multilingual Awareness:** Prompts explicitly account for Vietnamese column names and mixed Vietnamese/English data (`ngay_sinh`, `ho_ten`, `bac_si`, etc.).
- **Structured JSON output:** The LLM is required to return a pure JSON object (no markdown wrappers) matching the `TableLLMScanResponse` schema.

---

## 🔧 Configuration

Controlled via `src/config/app_config.yml`:

```yaml
llm:
  provider: "deepseek"       # Options: "openai", "deepseek"
  model: "deepseek-chat"
  temperature: 0.0           # 0.0 = deterministic, important for governance
  max_tokens: 2048
  max_retries: 3
  openai_api_key: "${OPENAPI_API_KEY}"
  deepseek_api_key: "${DEEPSEEK_API_KEY}"
```

> **Why `temperature: 0.0`?** Governance classification must be **deterministic and reproducible**. A temperature of 0 ensures the LLM always produces the same output for the same input, making audit trails reliable.

---

## ➕ Adding a New LLM Provider

1. Create a new class in `providers.py` that extends `BaseLLMProvider` and implements `get_response`.
2. Add a new `elif` branch in `LLMFactory.get_llm_provider()`.
3. Update `app_config.yml` to set the new `provider` name and add the corresponding API key.

No other changes are needed — the rest of the system consumes only the `BaseLLMProvider` interface.
