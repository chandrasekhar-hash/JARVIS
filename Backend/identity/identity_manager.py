import platform
import time
from typing import Optional, Dict, Any, Tuple
from identity.identity_models import (
    UserProfile,
    DeviceProfile,
    DeviceTrustState,
    SecurityStatus
)
from identity.crypto_utils import crypto_utils
from identity.identity_storage import identity_storage, SCHEMA_VERSION
from tools.telemetry import log_structured, backend_log

class LocalIdentityManager:
    """
    Local Identity Manager orchestrating local-first user profiles, Ed25519 device identities,
    and device trust states without requiring password authentication.
    """

    def __init__(self):
        self._current_user: Optional[UserProfile] = None
        self._current_device: Optional[DeviceProfile] = None

    def initialize(self) -> Tuple[UserProfile, DeviceProfile]:
        """
        Initializes local identity and device identity on backend boot.
        Auto-provisions local user and Ed25519 device profile if first run.
        """
        # 1. Initialize or load Ed25519 keypair
        priv_pem, pub_pem, fingerprint = crypto_utils.get_or_create_ed25519_keypair()

        # 2. Get or create primary user profile
        user = identity_storage.get_primary_user_profile()
        if not user:
            user_id = crypto_utils.generate_uuid("usr")
            user = UserProfile(
                user_id=user_id,
                display_name="J.A.R.V.I.S. Local User",
                locale="en-US",
                timezone="UTC"
            )
            identity_storage.save_user_profile(user)
            log_structured(backend_log, "INFO", f"[IdentityManager] Created default local user profile '{user_id}'")

        self._current_user = user

        # 3. Get or create primary device profile
        device = identity_storage.get_primary_device_profile()
        if not device:
            device_id = crypto_utils.generate_uuid("dev")
            device_name = f"{platform.node() or 'JARVIS-Node'}"
            device = DeviceProfile(
                device_id=device_id,
                device_name=device_name,
                platform=platform.system(),
                architecture=platform.machine(),
                os_version=platform.version(),
                app_version="1.0.0",
                public_key=pub_pem,
                public_key_fingerprint=fingerprint,
                trust_state=DeviceTrustState.TRUSTED
            )
            identity_storage.save_device_profile(device)
            log_structured(backend_log, "INFO", f"[IdentityManager] Created default device profile '{device_id}' ({fingerprint})")
        else:
            # Update public key & fingerprint in case key location changed
            device.public_key = pub_pem
            device.public_key_fingerprint = fingerprint
            identity_storage.save_device_profile(device)

        self._current_device = device

        log_structured(
            backend_log,
            "INFO",
            f"[IdentityManager] Identity system initialized. User: '{user.user_id}' | Device: '{device.device_id}' ({device.trust_state.value})"
        )
        return user, device

    def get_user_profile(self) -> UserProfile:
        if not self._current_user:
            self.initialize()
        return self._current_user

    def update_user_profile(self, display_name: str = None, email: str = None, avatar_url: str = None, preferences: Dict[str, Any] = None) -> UserProfile:
        user = self.get_user_profile()
        if display_name is not None:
            user.display_name = display_name
        if email is not None:
            user.email = email
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if preferences:
            user.ai_defaults.update(preferences)

        user.updated_at = time.time()
        identity_storage.save_user_profile(user)
        self._current_user = user
        log_structured(backend_log, "INFO", f"[IdentityManager] Updated profile for user '{user.user_id}'")
        return user

    def get_device_profile(self) -> DeviceProfile:
        if not self._current_device:
            self.initialize()
        return self._current_device

    def update_device_trust_state(self, trust_state: DeviceTrustState) -> DeviceProfile:
        device = self.get_device_profile()
        device.trust_state = trust_state
        device.updated_at = time.time()
        identity_storage.save_device_profile(device)
        self._current_device = device
        log_structured(backend_log, "INFO", f"[IdentityManager] Updated trust state for device '{device.device_id}' to '{trust_state.value}'")
        return device

    def get_security_status(self) -> SecurityStatus:
        user = self.get_user_profile()
        device = self.get_device_profile()
        active_sessions = identity_storage.list_active_sessions(user.user_id)

        return SecurityStatus(
            zero_trust_enabled=True,
            local_first_mode=True,
            active_sessions_count=len(active_sessions),
            active_devices_count=1,
            device_key_fingerprint=device.public_key_fingerprint,
            current_schema_version=SCHEMA_VERSION,
            crypto_algorithm="Ed25519"
        )

identity_manager = LocalIdentityManager()
