import json
import time
from typing import Optional, List
from models.schemas import CloudDevice, DeviceTrustState
from database.connection import db_manager

class DeviceRepository:
    def get_device(self, device_id: str) -> Optional[CloudDevice]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_devices WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return CloudDevice(
                device_id=row["device_id"],
                user_id=row["user_id"],
                device_name=row["device_name"],
                platform=row["platform"],
                architecture=row["architecture"],
                os_version=row["os_version"],
                app_version=row["app_version"],
                public_key=row["public_key"],
                public_key_fingerprint=row["public_key_fingerprint"],
                trust_state=DeviceTrustState(row["trust_state"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def list_devices_for_user(self, user_id: str) -> List[CloudDevice]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cloud_devices WHERE user_id = ? ORDER BY created_at ASC", (user_id,))
            rows = cursor.fetchall()
            devices = []
            for row in rows:
                devices.append(CloudDevice(
                    device_id=row["device_id"],
                    user_id=row["user_id"],
                    device_name=row["device_name"],
                    platform=row["platform"],
                    architecture=row["architecture"],
                    os_version=row["os_version"],
                    app_version=row["app_version"],
                    public_key=row["public_key"],
                    public_key_fingerprint=row["public_key_fingerprint"],
                    trust_state=DeviceTrustState(row["trust_state"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                ))
            return devices

    def save_device(self, device: CloudDevice) -> CloudDevice:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_devices (
                    device_id, user_id, device_name, platform, architecture, os_version,
                    app_version, public_key, public_key_fingerprint, trust_state, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    device_name = excluded.device_name,
                    platform = excluded.platform,
                    architecture = excluded.architecture,
                    os_version = excluded.os_version,
                    app_version = excluded.app_version,
                    public_key = excluded.public_key,
                    public_key_fingerprint = excluded.public_key_fingerprint,
                    trust_state = excluded.trust_state,
                    updated_at = excluded.updated_at
            """, (
                device.device_id,
                device.user_id,
                device.device_name,
                device.platform,
                device.architecture,
                device.os_version,
                device.app_version,
                device.public_key,
                device.public_key_fingerprint,
                device.trust_state.value,
                device.created_at,
                device.updated_at
            ))
            conn.commit()
        return device

    def update_trust_state(self, device_id: str, new_state: DeviceTrustState) -> bool:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cloud_devices SET trust_state = ?, updated_at = ? WHERE device_id = ?",
                (new_state.value, time.time(), device_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def rename_device(self, device_id: str, new_name: str) -> bool:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cloud_devices SET device_name = ?, updated_at = ? WHERE device_id = ?",
                (new_name, time.time(), device_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_device(self, device_id: str) -> bool:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cloud_devices WHERE device_id = ?", (device_id,))
            conn.commit()
            return cursor.rowcount > 0

    def count_devices(self) -> int:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cloud_devices")
            return cursor.fetchone()["count"]

device_repo = DeviceRepository()
