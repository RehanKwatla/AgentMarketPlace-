"""Cryptographic EVM Wallet Challenge Generation and Signature Verifier."""
import re
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from backend.shared.constants import NETWORK_BASE_SEPOLIA, CHAIN_ID_BASE_SEPOLIA
from backend.shared.errors import (
    WalletVerificationFailedError,
    AgentEconomyBaseException,
)


def normalize_address(address: str) -> str:
    """Normalize and validate an Ethereum address into checksum format.
    Raises exception if the address format is invalid.
    """
    cleaned = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", cleaned):
        raise AgentEconomyBaseException(
            f"Invalid EVM address format: '{address}'. Must be a 42-character 0x-prefixed hex string.",
            error_code="INVALID_ADDRESS_FORMAT"
        )
    return Web3.to_checksum_address(cleaned)


def format_challenge_text(address: str, nonce: str) -> str:
    """Format standardized EIP-191 challenge string for wallet verification."""
    return (
        f"Agentica Pay-Per-Call Agent Economy\n"
        f"Verify ownership of EVM wallet for account linkage.\n\n"
        f"Wallet: {address}\n"
        f"Network: {NETWORK_BASE_SEPOLIA}\n"
        f"Chain ID: {CHAIN_ID_BASE_SEPOLIA}\n"
        f"Nonce: {nonce}\n\n"
        f"Notice: Signing this message does not authorize any payment, gas fee, or transaction."
    )


def verify_signature(address: str, signature: str, challenge_text: str) -> bool:
    """Verify cryptographic signature against the expected EVM address using EIP-191 personal_sign."""
    try:
        norm_addr = normalize_address(address)
        signable = encode_defunct(text=challenge_text)
        recovered_address = Account.recover_message(signable, signature=signature)
        return normalize_address(recovered_address).lower() == norm_addr.lower()
    except Exception as e:
        raise WalletVerificationFailedError(f"Signature recovery failed: {str(e)}")
