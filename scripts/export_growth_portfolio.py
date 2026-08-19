"""Exports records from a SuccessFactors Growth Portfolio OData entity to CSV.

Run scripts/discover_growth_entities.py first to find the real entity set
name for your tenant, then pass it here.

Usage:
    python -m scripts.export_growth_portfolio <EntitySetName> [output.csv]
"""
from __future__ import annotations

import csv
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, ".")
from src.sf_auth import SFConnectionConfig  # noqa: E402
from src.sf_client import SFClient  # noqa: E402


def main() -> None:
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.export_growth_portfolio <EntitySetName> [output.csv]")
        sys.exit(1)

    entity_set = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else f"out/{entity_set}.csv"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    config = SFConnectionConfig(
        api_host=os.environ["SF_API_HOST"],
        company_id=os.environ["SF_COMPANY_ID"],
        client_id=os.environ["SF_CLIENT_ID"],
        api_user_id=os.environ["SF_API_USER_ID"],
        private_key_path=os.environ["SF_PRIVATE_KEY_PATH"],
        cert_path=os.environ["SF_CERT_PATH"],
    )
    client = SFClient(config)

    records = list(client.query_entity(entity_set))
    if not records:
        print(f"No records returned from {entity_set}.")
        return

    fieldnames = sorted({key for record in records for key in record})
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
