"""
JARVIS Product 1.6 - Knowledge Permission Engine.
Enforces multi-tenant document access controls, user ownership, and plugin permission scope guards.
"""

from typing import List, Optional
from .models import Document, DocumentPermissions


class KnowledgePermissionEngine:
    @staticmethod
    def can_read_document(
        document: Document,
        user_id: str,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> bool:
        perms: DocumentPermissions = document.permissions

        # 1. Owner always has full access
        if document.owner == user_id or perms.owner_id == user_id:
            return True

        # 2. Check public document status
        if perms.is_public:
            return True

        # 3. Explicit user allowlist
        if user_id in perms.allowed_users:
            return True

        # 4. Role-based access control (RBAC)
        if user_roles:
            for role in user_roles:
                if role in perms.allowed_roles:
                    return True

        # 5. Plugin permission scope check
        if plugin_id and plugin_id in perms.allowed_plugins:
            return True

        return False

    @staticmethod
    def filter_accessible_document_ids(
        documents: List[Document],
        user_id: str,
        user_roles: Optional[List[str]] = None,
        plugin_id: Optional[str] = None,
    ) -> List[str]:
        accessible_ids = []
        for doc in documents:
            if KnowledgePermissionEngine.can_read_document(doc, user_id, user_roles, plugin_id):
                accessible_ids.append(doc.document_id)
        return accessible_ids
