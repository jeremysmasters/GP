"""Lists $metadata entity types matching a keyword (default: growth).

The exact OData entity name backing the Growth Portfolio feature isn't
guessed here -- run this against your real tenant to find it.

Usage:
    python -m scripts.discover_growth_entities [keyword]
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

sys.path.insert(0, ".")
from src.sf_auth import SFConnectionConfig  # noqa: E402
from src.sf_client import SFClient  # noqa: E402
import os  # noqa: E402


def main() -> None:
    load_dotenv()
    keyword = sys.argv[1] if len(sys.argv) > 1 else "growth"

    config = SFConnectionConfig(
        api_host=os.environ["SF_API_HOST"],
        company_id=os.environ["SF_COMPANY_ID"],
        client_id=os.environ["SF_CLIENT_ID"],
        api_user_id=os.environ["SF_API_USER_ID"],
        private_key_path=os.environ["SF_PRIVATE_KEY_PATH"],
        cert_path=os.environ["SF_CERT_PATH"],
    )
    client = SFClient(config)

    matches = client.find_entities(keyword)
    if not matches:
        print(f"No entity types matched '{keyword}'.")
        return

    print(f"Entity types matching '{keyword}':")
    for name in matches:
        print(f"  {name}")


if __name__ == "__main__":
    main()
