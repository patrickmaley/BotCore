"""Partial signing keeps a signature Jupiter already attached."""

from __future__ import annotations

import base64
import unittest

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.message import MessageV0

from jup_perps_bot.signer import sign_serialized_transaction


class SignerTests(unittest.TestCase):
    def test_user_signature_does_not_wipe_the_keeper(self) -> None:
        payer = Keypair()
        keeper = Keypair()
        memo = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
        instruction = Instruction(
            memo,
            b"hi",
            [
                AccountMeta(payer.pubkey(), True, True),
                AccountMeta(keeper.pubkey(), True, False),
            ],
        )
        message = MessageV0.try_compile(payer.pubkey(), [instruction], [], Hash.default())
        payload = bytes([0x80]) + bytes(message)
        keeper_sig = keeper.sign_message(payload)
        partial = VersionedTransaction.populate(message, [Signature.default(), keeper_sig])
        encoded = base64.b64encode(bytes(partial)).decode()

        signed = VersionedTransaction.from_bytes(base64.b64decode(sign_serialized_transaction(encoded, payer)))

        self.assertEqual(list(signed.signatures)[1], keeper_sig)
        self.assertEqual(signed.verify_with_results(), [True, True])


if __name__ == "__main__":
    unittest.main()
