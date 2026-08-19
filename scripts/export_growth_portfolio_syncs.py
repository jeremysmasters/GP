"""Exports data from SF's Growth Portfolio Export REST API.

Endpoint: GET /rest/ecosystem/wholeself/v1/growthPortfolioSyncs

This is a REST endpoint (not OData), so its response shape/pagination
scheme isn't assumed here. First run saves the raw JSON response to
out/growth_portfolio_syncs_raw.json so you can inspect the real structure
(pagination cursor field, record wrapper key, etc.) and adjust the
flattening below if needed.

Usage:
    python -m scripts.export_growth_portfolio_syncs [key=value ...]

    Any key=value args are passed through as query params, e.g.:
    python -m scripts.export_growth_portfolio_syncs fromDate=2026-01-01
"""
from __future__ import annotations

import csv
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, ".")
from src.sf_auth import SFConnectionConfig  # noqa: E402
from src.sf_client import SFClient  # noqa: E402

ENDPOINT = "/rest/ecosystem/wholeself/v1/growthPortfolioSyncs"

# Keys commonly used by SF REST endpoints to wrap a list of records.
# Adjust once you've inspected the raw response.
LIST_WRAPPER_KEYS = ("value", "results", "data", "records", "items")


def _extract_records(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in LIST_WRAPPER_KEYS:
            if isinstance(body.get(key), list):
                return body[key]
    return None


def main() -> None:
    load_dotenv()
    query_params = dict(arg.split("=", 1) for arg in sys.argv[1:] if "=" in arg)

    config = SFConnectionConfig(
        api_host=os.environ["SF_API_HOST"],
        company_id=os.environ["SF_COMPANY_ID"],
        client_id=os.environ["SF_CLIENT_ID"],
        api_user_id=os.environ["SF_API_USER_ID"],
        private_key_path=os.environ["SF_PRIVATE_KEY_PATH"],
        cert_path=os.environ["SF_CERT_PATH"],
    )
    client = SFClient(config)

    body = client.rest_get(ENDPOINT, params=query_params or None)

    os.makedirs("out", exist_ok=True)
    raw_path = "out/growth_portfolio_syncs_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)
    print(f"Wrote raw response to {raw_path}")

    records = _extract_records(body)
    if records is None:
        print(
            "Could not find a list of records under known wrapper keys "
            f"{LIST_WRAPPER_KEYS}. Inspect the raw JSON above and adjust "
            "LIST_WRAPPER_KEYS or _extract_records() in this script."
        )
        return
    if not records:
        print("Endpoint returned zero records.")
        return

    fieldnames = sorted({key for record in records for key in record})
    csv_path = "out/growth_portfolio_syncs.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} records to {csv_path}")


if __name__ == "__main__":
    main()
