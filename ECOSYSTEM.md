# J.A.R.V.I.S. Ecosystem & Developer Platform Architecture

This document details the **Ecosystem & Developer Platform Subsystem (`sdk/`, `Backend/plugins/`, `Backend/autonomous/`, `Cloud/marketplace/`, `Cloud/webhooks/`, `Cloud/routes/developer_routes.py`)** implemented in **Phase 9**.

---

## 1. Overview & Objectives

Phase 9 transforms J.A.R.V.I.S. into an **Open Developer Ecosystem, Plugin Marketplace, and Automation Platform**:
- **Isolated Plugin Sandboxing**: Subprocess-isolated sandbox (`PluginSandbox`) enforcing memory quotas (max 256MB), CPU limits, and execution timeouts.
- **Capability Permission Model**: Restricts plugin capabilities (`fs:read`, `net:outbound`, `system:exec`, `speech:tts`) via explicit manifest declarations and permission enforcement (`PermissionEngine`).
- **6-State Plugin Lifecycle**: `INSTALLING` → `INSTALLED` → `ENABLED` → `DISABLED` → `UPDATING` → `UNINSTALLED` with async lifecycle hook callbacks (`on_install`, `on_enable`, `on_disable`, `on_upgrade`, `on_uninstall`).
- **Official Developer SDK & CLI (`jarvis-sdk`)**: Python SDK with `@jarvis_plugin` and `@jarvis_tool` decorators, `PluginTestHarness`, and `jarvis-plugin` CLI packaging tool.
- **Cloud Plugin Marketplace**: Discover, publish, rate, and install verified Ed25519-signed `.jpx` plugin packages with manifest version checks (`sdk_version`, `api_version`, `minimum_runtime`).
- **Outbound Webhooks**: System event dispatching (`task_completed`, `device_connected`, `sync_delta`) with HMAC-SHA256 signature verification and exponential backoff retry queues with Dead-Letter Queues (DLQ).
- **Durable DAG Workflow Engine**: Multi-step automation engine (Triggers → Conditions → Actions) with node execution state logging for restart resumption.
- **Public Developer API & Keys**: Developer portal issuing `jrv_live_...` API keys with OAuth2 scope validation and structured audit logging.
- **React Marketplace UI**: Dashboard component `MarketplaceView.jsx` for store browsing, plugin management, permission auditing, and API key management.

---

## 2. Directory & Module Structure

```text
sdk/
└── python/
    └── jarvis_sdk/                     # Official Python Developer SDK
        ├── plugin.py                   # @jarvis_plugin, @jarvis_tool decorators
        ├── capabilities.py             # Capabilities enum
        ├── testing.py                  # PluginTestHarness & LocalDevServer
        └── cli.py                      # jarvis-plugin CLI packaging tool

Backend/
├── plugins/
│   ├── sandbox.py                      # Subprocess Sandbox & Resource Quota Enforcer
│   ├── permissions.py                  # Capability Permission Engine
│   ├── lifecycle.py                    # 6-state Lifecycle Manager & Hook Runner
│   └── installer.py                    # Signed Package (.jpx) Installer
│
└── autonomous/
    └── workflow_engine.py              # Declarative DAG Automation Engine

Cloud/
├── alembic/
│   └── versions/
│       └── b2c3d4e5f6a7_add_phase9_ecosystem_tables.py
│
├── models/
│   └── orm.py                          # CloudPluginModel, CloudWebhookSubscriptionModel, CloudDeveloperKeyModel
│
├── marketplace/
│   ├── service.py                      # Marketplace Service (search, ratings, downloads)
│   └── package_verifier.py             # Ed25519 package signature & compatibility verifier
│
├── webhooks/
│   ├── service.py                      # Webhook Service & HMAC-SHA256 signer
│   └── retry_queue.py                  # Retry Queue & Dead-Letter Queue (DLQ)
│
└── routes/
    ├── marketplace_routes.py           # Marketplace REST endpoints
    ├── webhook_routes.py               # Webhook subscription REST endpoints
    └── developer_routes.py             # Public Developer API REST endpoints

frontend/
└── src/
    └── component/
        └── MarketplaceView.jsx         # React Marketplace Store & Manager UI
```

---

## 3. Quickstart: Authoring a Plugin with `jarvis-sdk`

```python
from jarvis_sdk import jarvis_plugin, jarvis_tool, BaseJarvisPlugin, Capabilities

@jarvis_plugin(
    plugin_id="plg_github_assistant",
    name="GitHub Copilot Assistant",
    version="1.0.0",
    sdk_version="1.0",
    api_version="1",
    minimum_runtime="1.0.0",
    capabilities=[Capabilities.FS_READ, Capabilities.NET_OUTBOUND]
)
class GitHubAssistantPlugin(BaseJarvisPlugin):
    
    @jarvis_tool(name="summarize_pr", description="Summarizes a GitHub Pull Request")
    def summarize_pr(self, pr_number: int) -> str:
        return f"PR #{pr_number} summary: Refactored authentication subsystem."
```
