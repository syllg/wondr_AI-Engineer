
# Wondr Mini Prototype – Natural Language Banking Insights

This prototype answers natural-language questions over **transactions.csv** and **customer_profiles.csv**.
It supports questions like:
- *How much did I spend on coffee last month?*
- *What’s my biggest spending category this year?*
- *How much did I save in the last 3 months?*
- *Summarize my finances in March 2025*

## Quick Start

```bash
python wondr_nl_prototype.py --transactions transactions.csv --profiles customer_profiles.csv --query "How much did I spend on coffee last month?"
```

Target a specific customer by **name** or **CIF** (contained in the query or via `--customer`):

```bash
python wondr_nl_prototype.py --query "How much did Chelsea Smith spend on coffee last month?"
python wondr_nl_prototype.py --query "What's 100103 biggest spending category this year?" --customer "100103"
```

## Notes

- The parser uses lightweight heuristics to detect date ranges and categories (keywords + fallback from `category_by_system`).
- Spending = **DEBIT**; Income = **CREDIT**; Estimated savings = *Income – Spending*.
- The prototype auto-caps date ranges to the **latest transaction date** to avoid empty future periods.
- A monthly per-customer summary has been exported to: `monthly_customer_summary.csv`.

## Files

- `wondr_nl_prototype.py` – main script (NLQ → answer)
- `monthly_customer_summary.csv` – spend/income/net and top category by month
- `README_wondr_prototype.md` – this guide

## Run the API locally (no Docker)

Prerequisites: Python 3.10+ installed.

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the FastAPI server on Windows/macOS/Linux:

```bash
python fastapi_app.py
```

Environment variables (optional):

- `TX_PATH` – path to transactions CSV (default `transactions.csv`)
- `PROFILES_PATH` – path to profiles CSV (default `customer_profiles.csv`)

Once running, visit:

- API health: `http://127.0.0.1:8000/health`
- Interactive docs: `http://127.0.0.1:8000/docs`
