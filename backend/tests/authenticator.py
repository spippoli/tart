"""A software WebAuthn authenticator for the passkey tests: it answers the API's options
as a browser with a platform passkey would, with ES256 keys and "none" attestation.

    authenticator = Authenticator()
    credential = authenticator.create(options, origin)   # `navigator.credentials.create`
    credential = authenticator.get(options, origin)      # `navigator.credentials.get`

Each response is the `PublicKeyCredential` in WebAuthn's JSON form, as the
frontend sends it.
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn import base64url_to_bytes
from webauthn.helpers import bytes_to_base64url

USER_PRESENT = 0x01
USER_VERIFIED = 0x04
ATTESTED_CREDENTIAL_DATA = 0x40


@dataclass
class _Credential:
    id: bytes
    key: ec.EllipticCurvePrivateKey
    rp_id: str
    user_handle: bytes
    sign_count: int = 0


@dataclass
class Authenticator:
    verifies_user: bool = True
    """False for an authenticator that checks presence only, without a PIN or biometric."""
    credentials: list[_Credential] = field(default_factory=list)

    def _flags(self) -> int:
        return USER_PRESENT | (USER_VERIFIED if self.verifies_user else 0)

    def create(self, options: dict[str, Any], origin: str) -> dict[str, Any]:
        rp_id = options["rp"]["id"]
        credential = _Credential(
            id=secrets.token_bytes(16),
            key=ec.generate_private_key(ec.SECP256R1()),
            rp_id=rp_id,
            user_handle=base64url_to_bytes(options["user"]["id"]),
        )
        self.credentials.append(credential)
        numbers = credential.key.public_key().public_numbers()
        public_key = cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32), -3: numbers.y.to_bytes(32)}
        )
        auth_data = (
            hashlib.sha256(rp_id.encode()).digest()
            + bytes([self._flags() | ATTESTED_CREDENTIAL_DATA])
            + credential.sign_count.to_bytes(4)
            + bytes(16)  # AAGUID
            + len(credential.id).to_bytes(2)
            + credential.id
            + public_key
        )
        client_data = _client_data("webauthn.create", options["challenge"], origin)
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {
            "id": bytes_to_base64url(credential.id),
            "rawId": bytes_to_base64url(credential.id),
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "attestationObject": bytes_to_base64url(attestation),
                "transports": ["internal", "hybrid"],
            },
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform",
        }

    def get(
        self, options: dict[str, Any], origin: str, credential: _Credential | None = None
    ) -> dict[str, Any]:
        """Sign in with `credential`, or with the last one created for the options' site."""
        rp_id = options["rpId"]
        if credential is None:
            credential = next(c for c in reversed(self.credentials) if c.rp_id == rp_id)
        credential.sign_count += 1
        auth_data = (
            hashlib.sha256(rp_id.encode()).digest()
            + bytes([self._flags()])
            + credential.sign_count.to_bytes(4)
        )
        client_data = _client_data("webauthn.get", options["challenge"], origin)
        signature = credential.key.sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        return {
            "id": bytes_to_base64url(credential.id),
            "rawId": bytes_to_base64url(credential.id),
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": bytes_to_base64url(credential.user_handle),
            },
            "clientExtensionResults": {},
            "authenticatorAttachment": "platform",
        }


def _client_data(kind: str, challenge: str, origin: str) -> bytes:
    return json.dumps(
        {"type": kind, "challenge": challenge, "origin": origin, "crossOrigin": False}
    ).encode()
