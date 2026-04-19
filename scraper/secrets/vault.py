"""HashiCorp Vault client using Kubernetes ServiceAccount auth."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import hvac

logger = logging.getLogger(__name__)

DEFAULT_SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"


class VaultError(RuntimeError):
    pass


class VaultClient:
    def __init__(
        self,
        addr: str,
        role: str,
        k8s_mount: str = "kubernetes",
        sa_token_path: str = DEFAULT_SA_TOKEN_PATH,
        kv_mount: str = "secret",
    ):
        self._kv_mount = kv_mount
        self._client = hvac.Client(url=addr)
        jwt = Path(sa_token_path).read_text().strip()
        self._client.auth.kubernetes.login(role=role, jwt=jwt, mount_point=k8s_mount)
        if not self._client.is_authenticated():
            raise VaultError("Vault authentication failed")
        logger.info("Authenticated to Vault at %s via kubernetes/%s role=%s", addr, k8s_mount, role)

    def read_kv(self, path: str) -> Dict[str, Any]:
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._kv_mount, raise_on_deleted_version=True
            )
        except Exception as e:
            raise VaultError(f"Failed to read secret {self._kv_mount}/{path}: {e}") from e
        return resp["data"]["data"]

    def get(self, path: str, key: str) -> str:
        data = self.read_kv(path)
        if key not in data:
            raise VaultError(f"Key '{key}' not found at {self._kv_mount}/{path}")
        return data[key]


_default: Optional[VaultClient] = None


def get_default_client() -> VaultClient:
    """Build (once) a VaultClient from environment variables."""
    global _default
    if _default is not None:
        return _default

    addr = os.environ.get("VAULT_ADDR")
    role = os.environ.get("VAULT_ROLE")
    if not addr or not role:
        raise VaultError("VAULT_ADDR and VAULT_ROLE must be set")

    _default = VaultClient(
        addr=addr,
        role=role,
        k8s_mount=os.environ.get("VAULT_K8S_MOUNT", "kubernetes"),
        sa_token_path=os.environ.get("VAULT_SA_TOKEN_PATH", DEFAULT_SA_TOKEN_PATH),
        kv_mount=os.environ.get("VAULT_KV_MOUNT", "secret"),
    )
    return _default
