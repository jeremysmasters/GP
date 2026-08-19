"""OAuth2 SAML Bearer Assertion flow for SAP SuccessFactors OData/API access.

Flow: build an unsigned SAML assertion naming the OAuth client as issuer and
the API technical user as subject, sign it with the private key that matches
the X.509 cert registered against the OAuth client in Admin Center, then
exchange the signed, base64-encoded assertion for a bearer access token at
POST https://{host}/oauth/token.

Attribute names/structure follow SAP's documented SAML Bearer flow for SF
OAuth clients (Admin Center > Manage OAuth2 Client Applications). Verify
against your tenant's API reference guide if the token endpoint rejects the
assertion -- minor attribute requirements have varied across SF releases.
"""
from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from lxml import etree
from lxml.builder import ElementMaker
from signxml import XMLSigner, methods

SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
NSMAP = {"saml2": SAML_NS}
E = ElementMaker(namespace=SAML_NS, nsmap=NSMAP)


@dataclass
class SFConnectionConfig:
    api_host: str  # e.g. "apisalesdemo2.successfactors.com"
    company_id: str
    client_id: str
    api_user_id: str
    private_key_path: str
    cert_path: str

    @property
    def base_url(self) -> str:
        return f"https://{self.api_host}"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_assertion_xml(config: SFConnectionConfig, validity_minutes: int = 5) -> bytes:
    now = datetime.now(timezone.utc)
    not_before = now - timedelta(minutes=1)
    not_on_or_after = now + timedelta(minutes=validity_minutes)
    assertion_id = f"_{uuid.uuid4().hex}"
    recipient = f"{config.base_url}/oauth/token"

    assertion = E.Assertion(
        E.Issuer(config.client_id),
        E.Subject(
            E.NameID(config.api_user_id),
            E.SubjectConfirmation(
                E.SubjectConfirmationData(
                    NotOnOrAfter=_iso(not_on_or_after),
                    Recipient=recipient,
                ),
                Method="urn:oasis:names:tc:SAML:2.0:cm:bearer",
            ),
        ),
        E.Conditions(
            E.AudienceRestriction(E.Audience("www.successfactors.com")),
            NotBefore=_iso(not_before),
            NotOnOrAfter=_iso(not_on_or_after),
        ),
        E.AuthnStatement(
            E.AuthnContext(
                E.AuthnContextClassRef("urn:oasis:names:tc:SAML:2.0:ac:classes:X509")
            ),
            AuthnInstant=_iso(now),
        ),
        E.AttributeStatement(
            E.Attribute(
                E.AttributeValue(config.company_id),
                Name="company_id",
            ),
            E.Attribute(
                E.AttributeValue("false"),
                Name="sso_startpage",
            ),
        ),
        ID=assertion_id,
        IssueInstant=_iso(now),
        Version="2.0",
    )
    return etree.tostring(assertion, xml_declaration=True, encoding="UTF-8")


def sign_assertion(assertion_xml: bytes, private_key_path: str, cert_path: str) -> bytes:
    with open(private_key_path, "rb") as f:
        key = f.read()
    with open(cert_path, "rb") as f:
        cert = f.read()

    root = etree.fromstring(assertion_xml)
    signed_root = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    ).sign(root, key=key, cert=cert)
    return etree.tostring(signed_root)


def get_access_token(config: SFConnectionConfig, timeout: int = 30) -> str:
    """Runs the full SAML Bearer flow and returns a bearer access token."""
    assertion_xml = build_assertion_xml(config)
    signed_xml = sign_assertion(assertion_xml, config.private_key_path, config.cert_path)
    assertion_b64 = base64.b64encode(signed_xml).decode("ascii")

    resp = requests.post(
        f"{config.base_url}/oauth/token",
        data={
            "client_id": config.client_id,
            "company_id": config.company_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:saml2-bearer",
            "assertion": assertion_b64,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
