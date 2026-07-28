from abc import ABC, abstractmethod
from typing import Optional


class BaseKeyStore(ABC):
    """
    Abstract Base Class for OS Secure Credential Keystore Providers.
    Application code interacts via high-level cryptographic operations.
    Plaintext private keys are never exposed as string variables across module boundaries.
    """

    @abstractmethod
    def store_private_key(self, key_id: str, private_key_bytes: bytes) -> bool:
        """Stores Ed25519 private key bytes securely in provider."""
        pass

    @abstractmethod
    def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Signs raw data bytes using the specified stored private key."""
        pass

    @abstractmethod
    def get_public_key_pem(self, key_id: str) -> Optional[str]:
        """Derives and returns public key PEM string for specified key ID."""
        pass

    @abstractmethod
    def key_exists(self, key_id: str) -> bool:
        """Returns True if the key ID exists in the keystore."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Deletes the specified key from the keystore."""
        pass

    @abstractmethod
    def get_provider_type(self) -> str:
        """Returns identifier string of provider (e.g. MacOSKeychain, WindowsDPAPI)."""
        pass
