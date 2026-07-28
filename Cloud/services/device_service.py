import time
import uuid
import hashlib
from typing import Optional, List
from models.schemas import CloudDevice, DeviceTrustState
from repositories.device_repository import device_repo
from repositories.audit_repository import audit_repo

class DeviceService:
    def register_device(
        self,
        user_id: str,
        device_name: str,
        platform: str,
        architecture: str,
        os_version: str,
        public_key: str,
        device_id: Optional[str] = None,
        app_version: str = "1.0.0"
    ) -> CloudDevice:
        dev_id = device_id or f"dev_{uuid.uuid4().hex[:16]}"
        key_bytes = public_key.encode("utf-8")
        fingerprint_hash = hashlib.sha256(key_bytes).hexdigest()
        fingerprint = f"SHA256:{fingerprint_hash[:16]}:{fingerprint_hash[16:32]}"

        device = CloudDevice(
            device_id=dev_id,
            user_id=user_id,
            device_name=device_name,
            platform=platform,
            architecture=architecture,
            os_version=os_version,
            app_version=app_version,
            public_key=public_key,
            public_key_fingerprint=fingerprint,
            trust_state=DeviceTrustState.TRUSTED,
            created_at=time.time(),
            updated_at=time.time()
        )
        saved = device_repo.save_device(device)
        audit_repo.log_event("DEVICE_REGISTERED", "register_device", "success", user_id=user_id, device_id=dev_id)
        return saved

    def get_device(self, device_id: str) -> Optional[CloudDevice]:
        return device_repo.get_device(device_id)

    def list_user_devices(self, user_id: str) -> List[CloudDevice]:
        return device_repo.list_devices_for_user(user_id)

    def update_device_trust(self, device_id: str, trust_state: DeviceTrustState) -> bool:
        success = device_repo.update_trust_state(device_id, trust_state)
        if success:
            audit_repo.log_event(
                "DEVICE_TRUST_UPDATED",
                "update_trust",
                "success",
                device_id=device_id,
                details={"new_trust_state": trust_state.value}
            )
        return success

    def rename_device(self, device_id: str, new_name: str) -> bool:
        success = device_repo.rename_device(device_id, new_name)
        if success:
            audit_repo.log_event("DEVICE_RENAMED", "rename_device", "success", device_id=device_id, details={"new_name": new_name})
        return success

    def revoke_device(self, device_id: str) -> bool:
        return self.update_device_trust(device_id, DeviceTrustState.REVOKED)

device_service = DeviceService()
