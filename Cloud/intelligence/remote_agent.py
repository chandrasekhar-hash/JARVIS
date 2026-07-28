import time
import json
import logging
from typing import Dict, Any, Optional, Set
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("JARVIS_RemoteAgentService")


class RemoteAgentService:
    """
    Cryptographic Remote Agent Execution Service.
    Enforces Zero-Trust remote command execution:
    - Ed25519 payload signature verification against originating device public key
    - Nonce and timestamp validation for replay attack prevention
    - Capability-based authorization checks before target device relay
    """

    def __init__(self, replay_ttl_seconds: float = 300.0):
        self.replay_ttl = replay_ttl_seconds
        self._used_nonces: Set[str] = set()

    def verify_remote_command_payload(
        self,
        command_payload: Dict[str, Any],
        public_key_pem: str,
        signature_bytes: bytes,
        required_capability: str = "desktop_execution"
    ) -> bool:
        """
        Cryptographically verifies incoming remote command payload signature, nonce, and capabilities.
        """
        # 1. Check timestamp and nonce for replay protection
        ts = command_payload.get("timestamp", 0)
        nonce = command_payload.get("nonce")
        now = time.time()

        if abs(now - ts) > self.replay_ttl:
            logger.error(f"Remote command rejected: Timestamp out of bounds ({abs(now - ts):.1f}s difference).")
            return False

        if not nonce or nonce in self._used_nonces:
            logger.error(f"Remote command rejected: Nonce '{nonce}' already used or missing (Replay attack).")
            return False
        self._used_nonces.add(nonce)

        # 2. Check capabilities
        capabilities = command_payload.get("capabilities", [])
        if required_capability not in capabilities and "all" not in capabilities:
            logger.error(f"Remote command rejected: Missing required capability '{required_capability}'.")
            return False

        # 3. Verify Ed25519 signature
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            if not isinstance(pub_key, ed25519.Ed25519PublicKey):
                logger.error("Remote command rejected: Provided public key is not Ed25519.")
                return False

            canonical_data = json.dumps(command_payload, sort_keys=True).encode("utf-8")
            pub_key.verify(signature_bytes, canonical_data)
            logger.info(f"Cryptographic Ed25519 verification successful for command '{command_payload.get('action')}' (nonce: {nonce}).")
            return True
        except Exception as e:
            logger.error(f"Cryptographic Ed25519 signature verification failed: {e}")
            return False


remote_agent_service = RemoteAgentService()
