import time
from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CloudUserModel(Base):
    __tablename__ = "cloud_users"

    user_id = Column(String(64), primary_key=True)
    display_name = Column(String(128), nullable=False, default="JARVIS Cloud User")
    email = Column(String(256), nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(Float, nullable=False, default=time.time)
    updated_at = Column(Float, nullable=False, default=time.time)
    preferences_json = Column(Text, nullable=False, default="{}")


class CloudDeviceModel(Base):
    __tablename__ = "cloud_devices"

    device_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("cloud_users.user_id"), nullable=False)
    device_name = Column(String(128), nullable=False)
    platform = Column(String(64), nullable=False)
    architecture = Column(String(64), nullable=False)
    os_version = Column(String(64), nullable=False)
    app_version = Column(String(64), nullable=False, default="1.0.0")
    public_key = Column(Text, nullable=False)
    public_key_fingerprint = Column(String(128), nullable=False)
    trust_state = Column(String(32), nullable=False, default="trusted")
    created_at = Column(Float, nullable=False, default=time.time)
    updated_at = Column(Float, nullable=False, default=time.time)


class CloudSessionModel(Base):
    __tablename__ = "cloud_sessions"

    session_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(Float, nullable=False)
    refresh_expires_at = Column(Float, nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)
    status = Column(String(32), nullable=False, default="active")
    ip_address = Column(String(64), nullable=True, default="127.0.0.1")
    user_agent = Column(Text, nullable=True, default="JARVIS Cloud Client")


class CloudAuditLogModel(Base):
    __tablename__ = "cloud_audit_logs"

    log_id = Column(String(64), primary_key=True)
    event_type = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=True)
    device_id = Column(String(64), nullable=True)
    action = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    details_json = Column(Text, nullable=False, default="{}")
    timestamp = Column(Float, nullable=False, default=time.time)


class CloudConfigurationModel(Base):
    __tablename__ = "cloud_configurations"

    config_key = Column(String(128), primary_key=True)
    config_value = Column(Text, nullable=False)
    updated_at = Column(Float, nullable=False, default=time.time)


class CloudContextSnapshotModel(Base):
    __tablename__ = "cloud_context_snapshots"

    snapshot_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False)
    context_type = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False, default=1.0)
    snapshot_json = Column(Text, nullable=False, default="{}")
    expires_at = Column(Float, nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)


class CloudNotificationModel(Base):
    __tablename__ = "cloud_notifications"

    notification_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    target_device_id = Column(String(64), nullable=True)
    title = Column(String(128), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, default="info")
    status = Column(String(32), nullable=False, default="unread")
    created_at = Column(Float, nullable=False, default=time.time)


class CloudRemoteJobModel(Base):
    __tablename__ = "cloud_remote_jobs"

    job_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False)
    origin_device_id = Column(String(64), nullable=False)
    execution_node_id = Column(String(64), nullable=True)
    task_type = Column(String(64), nullable=False)
    priority = Column(Integer, nullable=False, default=5)
    status = Column(String(32), nullable=False, default="QUEUED")
    retry_count = Column(Integer, nullable=False, default=0)
    trace_id = Column(String(64), nullable=False)
    created_at = Column(Float, nullable=False, default=time.time)
    updated_at = Column(Float, nullable=False, default=time.time)
