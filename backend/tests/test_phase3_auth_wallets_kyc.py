"""Comprehensive Pytest Suite for DI-06 Phase 3: Authentication, Multi-Wallet, and KYC."""
import json
import time
import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.session import SessionLocal, init_db
from backend.database.models import UserModel, KycRecordModel, WalletLinkModel
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    CHAIN_ID_BASE_SEPOLIA,
    KycStatus,
    WalletRole,
    WalletType,
)
from backend.kyc.mock_provider import MockKycProvider

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized for tests."""
    init_db()


def create_test_user(email: str = "testuser@agentica.io", password: str = "SecurePass123!", role: str = "user"):
    """Helper to create and verify a test user, returning token and user dict."""
    # Delete if exists
    with SessionLocal() as db:
        existing = db.query(UserModel).filter(UserModel.email == email.lower()).first()
        if existing:
            db.delete(existing)
            db.commit()

    # Signup
    signup_resp = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert signup_resp.status_code == 201, signup_resp.text
    signup_data = signup_resp.json()
    verification_token = signup_data.get("verification_token")

    # Verify Email
    verify_resp = client.post("/api/v1/auth/verify-email", json={"token": verification_token})
    assert verify_resp.status_code == 200

    # Login
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    login_data = login_resp.json()

    # If role needs update
    if role != "user":
        with SessionLocal() as db:
            user = db.query(UserModel).filter(UserModel.email == email.lower()).first()
            user.role = role
            db.commit()

    return {
        "user_id": login_data["user"]["id"],
        "email": email,
        "token": login_data["access_token"],
        "headers": {"Authorization": f"Bearer {login_data['access_token']}"},
    }


# ============================================================================
# Task 1: Authentication & Session Tests
# ============================================================================

def test_signup_and_email_verification():
    """Test user registration, verification token consumption, and duplicate prevention."""
    test_email = f"signup_{int(time.time())}@agentica.io"

    # 1. Sign up
    res = client.post("/api/v1/auth/signup", json={"email": test_email, "password": "Password123!"})
    assert res.status_code == 201
    data = res.json()
    token = data["verification_token"]
    assert token is not None

    # 2. Duplicate registration rejected
    dup_res = client.post("/api/v1/auth/signup", json={"email": test_email, "password": "Password123!"})
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 3. Verify email with single-use token
    verify_res = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_res.status_code == 200
    assert verify_res.json()["is_verified"] is True

    # 4. Token reuse fails
    reuse_res = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert reuse_res.status_code == 400


def test_login_success_and_invalid_credentials():
    """Test login with valid/invalid credentials and safe error messages."""
    test_email = f"login_{int(time.time())}@agentica.io"
    user_data = create_test_user(email=test_email, password="MySecretPassword123!")

    # Valid Login
    login_res = client.post("/api/v1/auth/login", json={"email": test_email, "password": "MySecretPassword123!"})
    assert login_res.status_code == 200
    body = login_res.json()
    assert "access_token" in body
    assert body["user"]["email"] == test_email

    # Invalid Password returns generic error (no credential enumeration)
    bad_res = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPassword"})
    assert bad_res.status_code == 400
    assert "Invalid email or password" in bad_res.json()["detail"]


def test_logout_and_session_revocation():
    """Test instant token revocation upon logout."""
    test_email = f"logout_{int(time.time())}@agentica.io"
    user_data = create_test_user(email=test_email)
    headers = user_data["headers"]

    # Access protected profile
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Accessing profile with revoked token must fail with HTTP 401
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert "revoked" in revoked_res.json()["detail"].lower()


def test_password_reset_flow():
    """Test password recovery flow using single-use reset token."""
    test_email = f"reset_{int(time.time())}@agentica.io"
    create_test_user(email=test_email, password="OldPassword123!")

    # 1. Request password reset
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": test_email})
    assert forgot_res.status_code == 200
    reset_token = forgot_res.json()["reset_token"]
    assert reset_token is not None

    # 2. Reset password
    reset_res = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewSecurePassword456!"
    })
    assert reset_res.status_code == 200

    # 3. Old password fails
    old_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "OldPassword123!"})
    assert old_login.status_code == 400

    # 4. New password succeeds
    new_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "NewSecurePassword456!"})
    assert new_login.status_code == 200


# ============================================================================
# Task 2: Multi-Wallet Management Tests
# ============================================================================

def test_wallet_challenge_and_eip191_signature_verification():
    """Test EVM wallet challenge issuance and cryptographic signature verification."""
    user = create_test_user(email=f"wallet_{int(time.time())}@agentica.io")
    acct = Account.create()

    # 1. Request Challenge
    chal_res = client.post("/api/v1/wallets/challenge", json={
        "address": acct.address,
        "wallet_type": "metamask"
    })
    assert chal_res.status_code == 200
    chal_data = chal_res.json()
    assert chal_data["network"] == NETWORK_BASE_SEPOLIA
    assert chal_data["chain_id"] == CHAIN_ID_BASE_SEPOLIA
    nonce = chal_data["nonce"]
    challenge_text = chal_data["challenge_text"]

    # 2. Sign Challenge using EIP-191 personal_sign
    signable = encode_defunct(text=challenge_text)
    signed = acct.sign_message(signable)
    sig_hex = signed.signature.hex()

    # 3. Link Wallet
    link_res = client.post(
        "/api/v1/wallets/link",
        headers=user["headers"],
        json={
            "address": acct.address,
            "signature": sig_hex,
            "nonce": nonce,
            "role": "identity",
            "wallet_type": "metamask",
            "is_primary": True
        }
    )
    assert link_res.status_code == 201
    wallet_data = link_res.json()
    assert wallet_data["address"].lower() == acct.address.lower()
    assert wallet_data["role"] == "identity"
    assert wallet_data["is_primary"] is True


def test_wallet_replay_protection():
    """Ensure challenge nonces cannot be replayed."""
    user = create_test_user(email=f"replay_wlt_{int(time.time())}@agentica.io")
    acct = Account.create()

    # Generate and sign challenge
    chal_res = client.post("/api/v1/wallets/challenge", json={"address": acct.address})
    chal_data = chal_res.json()
    signed = acct.sign_message(encode_defunct(text=chal_data["challenge_text"]))

    # First link succeeds
    res1 = client.post("/api/v1/wallets/link", headers=user["headers"], json={
        "address": acct.address,
        "signature": signed.signature.hex(),
        "nonce": chal_data["nonce"],
        "role": "payment",
        "wallet_type": "metamask"
    })
    assert res1.status_code == 201

    # Second link with same nonce fails
    res2 = client.post("/api/v1/wallets/link", headers=user["headers"], json={
        "address": acct.address,
        "signature": signed.signature.hex(),
        "nonce": chal_data["nonce"],
        "role": "payment",
        "wallet_type": "metamask"
    })
    assert res2.status_code == 400
    assert "used" in res2.json()["detail"].lower()


def test_wallet_duplicate_linking_conflict():
    """Ensure a wallet address cannot be linked to two different accounts."""
    user1 = create_test_user(email=f"u1_{int(time.time())}@agentica.io")
    user2 = create_test_user(email=f"u2_{int(time.time())}@agentica.io")
    acct = Account.create()

    # Link to user1
    chal1 = client.post("/api/v1/wallets/challenge", json={"address": acct.address}).json()
    sig1 = acct.sign_message(encode_defunct(text=chal1["challenge_text"])).signature.hex()
    link1 = client.post("/api/v1/wallets/link", headers=user1["headers"], json={
        "address": acct.address,
        "signature": sig1,
        "nonce": chal1["nonce"],
        "role": "identity"
    })
    assert link1.status_code == 201

    # User2 attempts to link the same address
    chal2 = client.post("/api/v1/wallets/challenge", json={"address": acct.address}).json()
    sig2 = acct.sign_message(encode_defunct(text=chal2["challenge_text"])).signature.hex()
    link2 = client.post("/api/v1/wallets/link", headers=user2["headers"], json={
        "address": acct.address,
        "signature": sig2,
        "nonce": chal2["nonce"],
        "role": "identity"
    })
    assert link2.status_code == 400
    assert "already linked" in link2.json()["detail"].lower()


def test_wallet_role_management_and_unlinking():
    """Test updating wallet roles, setting primary, and safe unlinking."""
    user = create_test_user(email=f"roles_{int(time.time())}@agentica.io")
    acct1 = Account.create()
    acct2 = Account.create()

    # Link acct1 as identity
    c1 = client.post("/api/v1/wallets/challenge", json={"address": acct1.address}).json()
    s1 = acct1.sign_message(encode_defunct(text=c1["challenge_text"])).signature.hex()
    w1 = client.post("/api/v1/wallets/link", headers=user["headers"], json={
        "address": acct1.address, "signature": s1, "nonce": c1["nonce"], "role": "identity"
    }).json()

    # Link acct2 as payment
    c2 = client.post("/api/v1/wallets/challenge", json={"address": acct2.address}).json()
    s2 = acct2.sign_message(encode_defunct(text=c2["challenge_text"])).signature.hex()
    w2 = client.post("/api/v1/wallets/link", headers=user["headers"], json={
        "address": acct2.address, "signature": s2, "nonce": c2["nonce"], "role": "payment"
    }).json()

    # List wallets
    list_res = client.get("/api/v1/wallets", headers=user["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

    # Change role of acct2 to receiving
    patch_res = client.patch(f"/api/v1/wallets/{w2['id']}", headers=user["headers"], json={"role": "receiving"})
    assert patch_res.status_code == 200
    assert patch_res.json()["role"] == "receiving"

    # Safe unlinking: user cannot unlink sole identity wallet when other wallets exist
    unlink_id_res = client.delete(f"/api/v1/wallets/{w1['id']}", headers=user["headers"])
    assert unlink_id_res.status_code == 400
    assert "cannot unlink your primary identity wallet" in unlink_id_res.json()["detail"].lower()

    # Unlink receiving wallet succeeds
    unlink_rec_res = client.delete(f"/api/v1/wallets/{w2['id']}", headers=user["headers"])
    assert unlink_rec_res.status_code == 200


# ============================================================================
# Task 3: Provider-Neutral KYC Lifecycle Tests
# ============================================================================

def test_kyc_lifecycle_and_mock_simulation():
    """Test deterministic KYC lifecycle from NOT_STARTED to PENDING to VERIFIED with [SIMULATED] badge."""
    user = create_test_user(email=f"kyc_{int(time.time())}@agentica.io")

    # 1. Initial status is NOT_STARTED
    status1 = client.get("/api/v1/kyc/status", headers=user["headers"]).json()
    assert status1["status"] == "NOT_STARTED"
    assert status1["is_simulated"] is True
    assert "SIMULATED" in status1["simulation_disclaimer"]

    # 2. Initiate session -> PENDING
    init_res = client.post("/api/v1/kyc/initiate", headers=user["headers"], json={"country": "US"})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["status"] == "PENDING"
    assert "hosted-session" in init_data["session_url"]

    # 3. Simulate provider decision: VERIFIED
    mock_res = client.post("/api/v1/kyc/mock-decision", headers=user["headers"], json={
        "event_id": f"evt_{int(time.time())}",
        "provider_reference_id": init_data["provider_reference_id"],
        "user_id": user["user_id"],
        "decision": "VERIFIED",
        "reason": "Test automatic biometric simulation",
        "timestamp": int(time.time()),
    })
    assert mock_res.status_code == 200
    assert mock_res.json()["status"] == "VERIFIED"

    # 4. Check status and audit trail
    status2 = client.get("/api/v1/kyc/status", headers=user["headers"]).json()
    assert status2["status"] == "VERIFIED"
    assert len(status2["audit_history"]) >= 2  # NOT_STARTED->PENDING, PENDING->VERIFIED
    assert status2["audit_history"][0]["to_status"] == "VERIFIED"


def test_kyc_state_machine_invalid_transitions():
    """Test that illegal KYC status transitions are rejected by the state machine."""
    user = create_test_user(email=f"kyc_illegal_{int(time.time())}@agentica.io")

    # User is currently NOT_STARTED. Transitioning directly to VERIFIED without PENDING is forbidden.
    mock_res = client.post("/api/v1/kyc/mock-decision", headers=user["headers"], json={
        "event_id": "evt_illegal",
        "provider_reference_id": "mock_illegal",
        "user_id": user["user_id"],
        "decision": "VERIFIED",
        "timestamp": int(time.time()),
    })
    assert mock_res.status_code == 400
    assert "Invalid KYC status transition" in mock_res.json()["detail"]


def test_kyc_webhook_hmac_verification():
    """Test provider webhook HMAC signature verification and rejection of forged webhooks."""
    user = create_test_user(email=f"webhook_{int(time.time())}@agentica.io")
    # Initiate to PENDING first
    client.post("/api/v1/kyc/initiate", headers=user["headers"], json={"country": "US"})

    mock_provider = MockKycProvider()
    payload = {
        "event_id": f"evt_{int(time.time())}",
        "provider_reference_id": "ref_123",
        "user_id": user["user_id"],
        "decision": "VERIFIED",
        "reason": "Verified biometric check",
        "timestamp": int(time.time()),
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # 1. Valid HMAC signature succeeds
    valid_sig = mock_provider.sign_payload(raw_body)
    res_valid = client.post(
        "/api/v1/kyc/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-KYC-Signature": valid_sig}
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["new_status"] == "VERIFIED"

    # 2. Forged signature fails
    res_invalid = client.post(
        "/api/v1/kyc/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-KYC-Signature": "sha256=forged_bad_signature_00000"}
    )
    assert res_invalid.status_code == 400
    assert "invalid webhook signature" in res_invalid.json()["detail"].lower()



# ============================================================================
# Task 4: Access Policy Integration Tests
# ============================================================================

def test_access_policy_public_browsing():
    """Policy: Browsing services and public policy is unauthenticated."""
    res = client.get("/api/v1/policy/public-browse")
    assert res.status_code == 200
    assert res.json()["access"] == "granted"

    # Catalog browsing is public
    services_res = client.get("/api/v1/services")
    assert services_res.status_code == 200


def test_access_policy_buyer_task_submission():
    """Policy: Buyer task gate requires authenticated user with a verified payment wallet."""
    user = create_test_user(email=f"gate_buyer_{int(time.time())}@agentica.io")

    # 1. Unauthenticated request rejected
    res_no_auth = client.post("/api/v1/policy/buyer-task-gate")
    assert res_no_auth.status_code == 401

    # 2. Authenticated user without payment wallet rejected
    res_no_wallet = client.post("/api/v1/policy/buyer-task-gate", headers=user["headers"])
    assert res_no_wallet.status_code == 403
    assert "payment" in res_no_wallet.json()["detail"].lower()

    # 3. Authenticated user links payment wallet -> access granted
    acct = Account.create()
    chal = client.post("/api/v1/wallets/challenge", json={"address": acct.address}).json()
    sig = acct.sign_message(encode_defunct(text=chal["challenge_text"])).signature.hex()
    client.post("/api/v1/wallets/link", headers=user["headers"], json={
        "address": acct.address, "signature": sig, "nonce": chal["nonce"], "role": "payment"
    })

    res_with_wallet = client.post("/api/v1/policy/buyer-task-gate", headers=user["headers"])
    assert res_with_wallet.status_code == 200
    assert res_with_wallet.json()["access"] == "granted"


def test_access_policy_seller_registration():
    """Policy: Seller registration requires KYC verification."""
    user = create_test_user(email=f"gate_seller_{int(time.time())}@agentica.io")

    # 1. Unverified KYC rejected
    res_unverified = client.post("/api/v1/policy/seller-registration-gate", headers=user["headers"])
    assert res_unverified.status_code == 403
    assert "KYC verification required" in res_unverified.json()["detail"]

    # 2. Complete mock KYC -> access granted
    client.post("/api/v1/kyc/initiate", headers=user["headers"], json={"country": "US"})
    client.post("/api/v1/kyc/mock-decision", headers=user["headers"], json={
        "event_id": "evt_seller_kyc",
        "provider_reference_id": "mock_ref",
        "user_id": user["user_id"],
        "decision": "VERIFIED",
        "timestamp": int(time.time()),
    })

    res_verified = client.post("/api/v1/policy/seller-registration-gate", headers=user["headers"])
    assert res_verified.status_code == 200
    assert res_verified.json()["access"] == "granted"


def test_access_policy_admin_controls():
    """Policy: Administrative actions require admin role."""
    user = create_test_user(email=f"gate_admin_user_{int(time.time())}@agentica.io", role="user")
    admin = create_test_user(email=f"gate_admin_adm_{int(time.time())}@agentica.io", role="admin")

    # Normal user rejected
    res_user = client.post("/api/v1/policy/admin-gate", headers=user["headers"])
    assert res_user.status_code == 403

    # Admin granted
    res_admin = client.post("/api/v1/policy/admin-gate", headers=admin["headers"])
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "admin"


# ============================================================================
# Task 5: Zero Secret Exposure & Feature Regression Tests
# ============================================================================

def test_zero_secret_exposure():
    """Ensure private keys, seed phrases, and passwords are never exposed."""
    user = create_test_user(email=f"privacy_{int(time.time())}@agentica.io")

    # Profile endpoint must never return password hash or keys
    profile = client.get("/api/v1/auth/me", headers=user["headers"]).json()
    assert "password" not in profile
    assert "password_hash" not in profile
    assert "private_key" not in profile
    assert "seed" not in profile

    # Wallet listings must never return private keys
    wallets = client.get("/api/v1/wallets", headers=user["headers"]).json()
    for w in wallets:
        assert "private_key" not in w
        assert "seed" not in w


def test_regression_buyer_seller_payment_ledger():
    """Ensure existing buyer DAG, seller microservices, and ledger endpoints remain operational."""
    # 1. Health check
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    # 2. Service registry list
    services = client.get("/api/v1/services")
    assert services.status_code == 200
    assert services.json()["total"] >= 9

    # 3. Ledger records
    ledger = client.get("/api/v1/ledger/records")
    assert ledger.status_code in [200, 404]  # 200 if records exist or empty list
