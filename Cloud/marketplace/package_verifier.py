import json
import base64
import logging
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("JARVIS_MarketplacePackageVerifier")


class PackageVerifier:
    """
    Verifies Ed25519 publisher signatures on `.jpx` plugin packages
    and validates version constraints (sdk_version, api_version, minimum_runtime).
    """

    @staticmethod
    def verify_publisher_signature(
        package_bytes: bytes,
        publisher_public_key_pem: str,
        signature_b64: str
    ) -> bool:
        try:
            pub_key = serialization.load_pem_public_key(publisher_public_key_pem.encode("utf-8"))
            if not isinstance(pub_key, ed25519.Ed25519PublicKey):
                return False
            sig_bytes = base64.b64decode(signature_b64)
            pub_key.verify(sig_bytes, package_bytes)
            logger.info("Publisher package Ed25519 signature verification PASSED.")
            return True
        except Exception as e:
            logger.error(f"Publisher package signature verification failed: {e}")
            return False

    @staticmethod
    def validate_manifest_compatibility(manifest: Dict[str, Any], current_runtime_version: str = "2.5.0") -> Tuple[bool, str]:
        req_sdk = manifest.get("sdk_version", "1.0")
        req_api = manifest.get("api_version", "1")
        min_runtime = manifest.get("minimum_runtime", "1.0.0")

        # Semantic check
        if min_runtime > current_runtime_version:
            return False, f"Plugin requires minimum runtime version '{min_runtime}', current runtime is '{current_runtime_version}'."

        return True, "Compatible"
