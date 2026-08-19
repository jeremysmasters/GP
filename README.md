# SAP SuccessFactors Growth Portfolio export

Pulls data out of a SAP SuccessFactors OData API using the OAuth2 SAML
Bearer Assertion flow, targeting the Growth Portfolio feature in Career
Development.

## Known demo tenant values

- Company ID: `SFCPART000185`
- Login host: `pmsalesdemo8.successfactors.com`
- API host: `api40sales.sapsf.com`

## One-time admin setup (Admin Center, requires admin access)

1. **Company System and Logo Settings** -- copy the exact API server URL for
   `SF_API_HOST`. Don't assume it matches the login host numbering; verify.
2. **Manage OAuth2 Client Applications** -> Register New Client Application.
   - Give it a name/description.
   - Use the "Generate X.509 Certificate" option so SF creates the key pair
     for you. **Download the private key immediately** -- SF does not store
     or let you re-download it later.
   - Save. Copy the resulting **API Key** -- this is `SF_CLIENT_ID`.
3. Pick or create a **technical/API user** account in the system. This
   user's `userId` is `SF_API_USER_ID`.
4. **Manage Permission Roles** -> create/edit a role that grants:
   - Generic **OData API** permission
   - Metadata Framework / entity-level read permission covering whatever
     entity backs Growth Portfolio (see discovery step below)
   Assign this role to the technical user (via the role's Grant Permission
   target population).
5. If the tenant enforces IP allowlisting for API access, add your
   machine's/service's egress IP.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

mkdir -p secrets
# place the downloaded private key and matching public cert here:
#   secrets/sf_private_key.pem
#   secrets/sf_public_cert.pem

cp .env.example .env
# fill in SF_API_HOST, SF_COMPANY_ID=SFCPART000185, SF_CLIENT_ID, SF_API_USER_ID
```

## Find the real entity name

The exact OData entity backing "Growth Portfolio" isn't guessed in this
repo -- confirm it against your tenant's live metadata:

```bash
python -m scripts.discover_growth_entities growth
```

This greps `$metadata` for entity types containing "growth". Try other
keywords (`career`, `aspiration`, `cdp`) if nothing matches.

## Export

**Growth Portfolio Export API (confirmed endpoint):**

```bash
python -m scripts.export_growth_portfolio_syncs
# writes out/growth_portfolio_syncs_raw.json (raw response, for inspection)
# and out/growth_portfolio_syncs.csv (if a record list is found)
```

This calls `GET /rest/ecosystem/wholeself/v1/growthPortfolioSyncs`. It's a
REST endpoint, not OData, so its exact response/pagination shape wasn't
guessed here -- the script dumps the raw JSON first so you can confirm the
structure (record wrapper key, any sync/continuation cursor) and the
flattening logic can be tightened once you've seen real output. Pass query
params as `key=value` args, e.g. `fromDate=2026-01-01`.

**Generic OData fallback (if you need other entities beyond the Export API):**

```bash
python -m scripts.export_growth_portfolio <EntitySetName>
# writes out/<EntitySetName>.csv
```

## Layout

- `src/sf_auth.py` -- builds and signs the SAML assertion, exchanges it for
  a bearer token at `/oauth/token`.
- `src/sf_client.py` -- OData v2 client (metadata fetch/search, paged entity
  queries) plus a generic `rest_get` for non-OData endpoints.
- `scripts/discover_growth_entities.py` -- OData metadata keyword search.
- `scripts/export_growth_portfolio_syncs.py` -- calls the Growth Portfolio
  Export REST API directly.
- `scripts/export_growth_portfolio.py` -- generic OData entity export.

## Notes

- Access tokens from this flow are short-lived (tenant-configured, often
  ~30 min); `SFClient` fetches one lazily and does not currently refresh
  mid-run. For long exports, re-instantiate `SFClient` per batch if needed.
- Never commit `.env` or anything under `secrets/` -- both are gitignored.
