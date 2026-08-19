"""Minimal OData v2 client for SAP SuccessFactors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import requests

from .sf_auth import SFConnectionConfig, get_access_token


@dataclass
class SFClient:
    config: SFConnectionConfig
    _token: str | None = None

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            self._token = get_access_token(self.config)
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def get_metadata(self) -> str:
        """Raw $metadata XML -- use this to find real entity/field names."""
        resp = requests.get(
            f"{self.config.base_url}/odata/v2/$metadata",
            headers=self._headers(),
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text

    def find_entities(self, keyword: str) -> list[str]:
        """Search $metadata for EntityType names containing keyword (case-insensitive)."""
        from lxml import etree

        xml = self.get_metadata().encode("utf-8")
        root = etree.fromstring(xml)
        ns = {"edm": "http://schemas.microsoft.com/ado/2008/09/edm"}
        matches = []
        for entity_type in root.iter("{http://schemas.microsoft.com/ado/2008/09/edm}EntityType"):
            name = entity_type.get("Name", "")
            if keyword.lower() in name.lower():
                matches.append(name)
        return sorted(set(matches))

    def query_entity(
        self,
        entity_set: str,
        select: list[str] | None = None,
        filter_: str | None = None,
        page_size: int = 200,
    ) -> Iterator[dict[str, Any]]:
        """Yields records from an OData entity set, paging via $skiptoken."""
        url = f"{self.config.base_url}/odata/v2/{entity_set}"
        params: dict[str, Any] = {"$format": "json", "$top": page_size}
        if select:
            params["$select"] = ",".join(select)
        if filter_:
            params["$filter"] = filter_

        while url:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=60)
            resp.raise_for_status()
            body = resp.json()["d"]
            results = body.get("results", body if isinstance(body, list) else [])
            for record in results:
                record.pop("__metadata", None)
                yield record

            next_url = body.get("__next")
            url = next_url
            params = {}  # __next already carries the full query string
