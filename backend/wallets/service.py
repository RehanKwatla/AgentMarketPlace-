"""Service Layer for Linking, Managing, and Unlinking EVM Wallets."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.database.models import WalletChallengeModel, WalletLinkModel
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    CHAIN_ID_BASE_SEPOLIA,
    WalletRole,
    WalletType,
)
from backend.shared.errors import (
    WalletVerificationFailedError,
    WalletAlreadyLinkedError,
    WalletNotFoundError,
    WalletRoleViolationError,
    AgentEconomyBaseException,
)
from .verifier import normalize_address, format_challenge_text, verify_signature


class WalletService:
    """Multi-wallet verification and role assignment service."""

    @staticmethod
    def issue_challenge(db: Session, raw_address: str, wallet_type: WalletType) -> WalletChallengeModel:
        """Generate short-lived (5 min), single-use challenge for wallet ownership verification."""
        checksum_address = normalize_address(raw_address)
        nonce = f"chn_{secrets.token_hex(16)}"
        challenge_text = format_challenge_text(checksum_address, nonce)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        challenge = WalletChallengeModel(
            nonce=nonce,
            address=checksum_address,
            challenge_text=challenge_text,
            expires_at=expires_at,
            used=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)
        return challenge

    @staticmethod
    def link_wallet(
        db: Session,
        user_id: str,
        raw_address: str,
        signature: str,
        nonce: str,
        role: WalletRole = WalletRole.IDENTITY,
        wallet_type: WalletType = WalletType.METAMASK,
        is_primary: bool = False,
    ) -> WalletLinkModel:
        """Verify signature against challenge, validate single-use, check conflict policy, and link wallet."""
        checksum_address = normalize_address(raw_address)

        # 1. Fetch challenge
        challenge = db.query(WalletChallengeModel).filter(
            WalletChallengeModel.nonce == nonce,
            WalletChallengeModel.used == False
        ).first()

        if not challenge:
            raise WalletVerificationFailedError("Challenge nonce is invalid or has already been used.")

        # Check address match
        if challenge.address.lower() != checksum_address.lower():
            raise WalletVerificationFailedError("Challenge address does not match signature submission.")

        # Check challenge expiration
        now = datetime.now(timezone.utc)
        exp = challenge.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise WalletVerificationFailedError("Challenge nonce has expired. Please request a new challenge.")

        # 2. Cryptographically verify signature
        if not verify_signature(checksum_address, signature, challenge.challenge_text):
            raise WalletVerificationFailedError("Cryptographic signature does not match wallet address.")

        # Mark challenge consumed immediately (replay protection)
        challenge.used = True

        # 3. Conflict Policy: Check if address is linked to ANOTHER user
        conflict = db.query(WalletLinkModel).filter(
            WalletLinkModel.address == checksum_address,
            WalletLinkModel.user_id != user_id
        ).first()

        if conflict:
            raise WalletAlreadyLinkedError(checksum_address)

        # 4. Check if current user already has this address linked
        existing = db.query(WalletLinkModel).filter(
            WalletLinkModel.user_id == user_id,
            WalletLinkModel.address == checksum_address
        ).first()

        # If user has no existing wallets with this role, make it primary automatically
        same_role_count = db.query(WalletLinkModel).filter(
            WalletLinkModel.user_id == user_id,
            WalletLinkModel.role == role.value
        ).count()
        if same_role_count == 0:
            is_primary = True

        if is_primary:
            # Clear primary flag on other wallets of this role for this user
            db.query(WalletLinkModel).filter(
                WalletLinkModel.user_id == user_id,
                WalletLinkModel.role == role.value
            ).update({"is_primary": False})

        if existing:
            existing.role = role.value
            existing.wallet_type = wallet_type.value
            existing.is_primary = is_primary
            existing.verified_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing

        # Create new link
        wallet_id = f"wlt_{uuid.uuid4().hex[:12]}"
        link = WalletLinkModel(
            id=wallet_id,
            user_id=user_id,
            address=checksum_address,
            role=role.value,
            wallet_type=wallet_type.value,
            is_primary=is_primary,
            network=NETWORK_BASE_SEPOLIA,
            chain_id=CHAIN_ID_BASE_SEPOLIA,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def get_user_wallets(db: Session, user_id: str) -> List[WalletLinkModel]:
        """List all linked wallets for the user."""
        return db.query(WalletLinkModel).filter(WalletLinkModel.user_id == user_id).all()

    @staticmethod
    def update_wallet(
        db: Session,
        user_id: str,
        wallet_id: str,
        new_role: Optional[WalletRole] = None,
        is_primary: Optional[bool] = None,
    ) -> WalletLinkModel:
        """Update role or primary status of a linked wallet."""
        wallet = db.query(WalletLinkModel).filter(
            WalletLinkModel.id == wallet_id,
            WalletLinkModel.user_id == user_id
        ).first()

        if not wallet:
            raise WalletNotFoundError(wallet_id)

        target_role = new_role.value if new_role else wallet.role

        if is_primary:
            # Clear primary flag on existing wallets of same role
            db.query(WalletLinkModel).filter(
                WalletLinkModel.user_id == user_id,
                WalletLinkModel.role == target_role
            ).update({"is_primary": False})
            wallet.is_primary = True

        if new_role:
            wallet.role = new_role.value

        db.commit()
        db.refresh(wallet)
        return wallet

    @staticmethod
    def unlink_wallet(db: Session, user_id: str, wallet_id: str) -> None:
        """Safely unlink a wallet. Prevents unlinking if it is the only identity wallet."""
        wallet = db.query(WalletLinkModel).filter(
            WalletLinkModel.id == wallet_id,
            WalletLinkModel.user_id == user_id
        ).first()

        if not wallet:
            raise WalletNotFoundError(wallet_id)

        # Safety policy: if user has only 1 identity wallet and unlinks it, check policy
        if wallet.role == WalletRole.IDENTITY.value:
            identity_count = db.query(WalletLinkModel).filter(
                WalletLinkModel.user_id == user_id,
                WalletLinkModel.role == WalletRole.IDENTITY.value
            ).count()
            if identity_count <= 1:
                total_wallets = db.query(WalletLinkModel).filter(
                    WalletLinkModel.user_id == user_id
                ).count()
                if total_wallets > 1:
                    raise WalletRoleViolationError(
                        "Cannot unlink your primary identity wallet while other wallets remain. "
                        "Designate another identity wallet first."
                    )

        db.delete(wallet)
        db.commit()
