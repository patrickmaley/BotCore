"""Sign a Jupiter transaction without dropping signatures already on it."""

from __future__ import annotations

import base64


class SignerError(RuntimeError):
    pass


def load_keypair(path: str):
    """Load a Solana CLI keypair file (a JSON array of 64 bytes)."""
    import json

    from solders.keypair import Keypair

    with open(path, encoding="utf-8") as handle:
        data = json.loads(handle.read())
    if not isinstance(data, list) or len(data) != 64:
        raise SignerError("keypair file must be a JSON array of 64 bytes")
    return Keypair.from_bytes(bytes(data))


def sign_serialized_transaction(serialized_tx_base64: str, keypair) -> str:
    """Add the wallet signature and keep any keeper signature already present."""
    from solders.transaction import Transaction, VersionedTransaction

    raw = base64.b64decode(serialized_tx_base64)
    try:
        transaction = VersionedTransaction.from_bytes(raw)
    except Exception:
        transaction = None
    if transaction is not None and transaction.version() == 0:
        return _sign_versioned(transaction, keypair)
    legacy = Transaction.from_bytes(raw)
    blockhash = legacy.message.recent_blockhash
    legacy.sign([keypair], blockhash)
    return base64.b64encode(bytes(legacy)).decode()


def _sign_versioned(transaction, keypair) -> str:
    from solders.transaction import VersionedTransaction

    message = transaction.message
    required = message.header.num_required_signatures
    signers = list(message.account_keys)[:required]
    try:
        index = signers.index(keypair.pubkey())
    except ValueError as exc:
        raise SignerError("keypair is not a required signer on this transaction") from exc
    payload = bytes([0x80]) + bytes(message)
    signatures = list(transaction.signatures)
    signatures[index] = keypair.sign_message(payload)
    signed = VersionedTransaction.populate(message, signatures)
    return base64.b64encode(bytes(signed)).decode()
