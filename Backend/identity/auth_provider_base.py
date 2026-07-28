from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from identity.identity_models import AuthProviderEnum, TokenPair

class BaseAuthProvider(ABC):
    """
    Abstract Authentication Provider Interface following SOLID principles.
    Enables future pluggable authentication providers (Google, GitHub, Apple, Microsoft, OAuth).
    """

    @property
    @abstractmethod
    def provider_name(self) -> AuthProviderEnum:
        pass

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticates credentials and returns (success, user_id, error_message).
        """
        pass

class OAuthProviderPlaceholder(BaseAuthProvider):
    """
    Interface placeholder for generic OAuth authentication.
    """

    def __init__(self, provider_type: AuthProviderEnum = AuthProviderEnum.OAUTH):
        self._provider_type = provider_type

    @property
    def provider_name(self) -> AuthProviderEnum:
        return self._provider_type

    def authenticate(self, credentials: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        return False, None, f"Cloud provider '{self._provider_type.value}' is not configured in local-first mode."

class GoogleAuthProvider(OAuthProviderPlaceholder):
    def __init__(self):
        super().__init__(AuthProviderEnum.GOOGLE)

class GitHubAuthProvider(OAuthProviderPlaceholder):
    def __init__(self):
        super().__init__(AuthProviderEnum.GITHUB)

class AppleAuthProvider(OAuthProviderPlaceholder):
    def __init__(self):
        super().__init__(AuthProviderEnum.APPLE)

class MicrosoftAuthProvider(OAuthProviderPlaceholder):
    def __init__(self):
        super().__init__(AuthProviderEnum.MICROSOFT)
