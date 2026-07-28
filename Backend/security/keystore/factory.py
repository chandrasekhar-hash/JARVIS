import sys
import logging
from typing import Dict, Type, Optional
from Backend.security.keystore.base import BaseKeyStore

logger = logging.getLogger("JARVIS_KeystoreFactory")


class KeystoreFactory:
    """
    Extensible Provider Factory for Keystore implementations.
    Decouples KeystoreManager from hardcoded OS platform checks.
    Supports registration of hardware/cloud providers (Secure Enclave, TPM, HSM, Cloud KMS).
    """

    _providers: Dict[str, Type[BaseKeyStore]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseKeyStore]):
        cls._providers[name] = provider_cls
        logger.info(f"Registered keystore provider '{name}' ({provider_cls.__name__})")

    @classmethod
    def get_provider(cls, name: str) -> Optional[BaseKeyStore]:
        provider_cls = cls._providers.get(name)
        if provider_cls:
            try:
                inst = provider_cls()
                return inst
            except Exception as e:
                logger.warning(f"Failed to instantiate provider '{name}': {e}")
        return None

    @classmethod
    def get_preferred_provider(cls) -> BaseKeyStore:
        """
        Determines and instantiates preferred keystore provider for current platform.
        Falls back to EncryptedFileFallback if native OS provider is unavailable.
        """
        platform = sys.platform

        if platform == "darwin":
            provider = cls.get_provider("MacOSKeychain")
            if provider:
                return provider

        elif platform == "win32":
            provider = cls.get_provider("WindowsDPAPI")
            if provider:
                return provider

        elif platform.startswith("linux"):
            provider = cls.get_provider("LinuxSecretService")
            if provider:
                return provider

        # Fallback provider
        fallback = cls.get_provider("EncryptedFileFallback")
        if fallback:
            return fallback

        raise RuntimeError("No suitable keystore provider available.")
