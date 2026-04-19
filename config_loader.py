import json
import os
from typing import Dict, Optional
from dataclasses import dataclass

from scraper.secrets import VaultError, get_default_client


@dataclass
class FormConfig:
    """Form filling configuration."""
    enabled: bool = True
    fill_delay: int = 100
    defaults: Dict[str, str] = None  # selector -> value mapping

    def __post_init__(self):
        if self.defaults is None:
            self.defaults = {}


@dataclass
class LoginConfig:
    """Login flow configuration. Presence of this block enables login handling."""
    login_url: str
    username: str
    password: str
    username_selector: str = "#username"
    password_selector: str = "input[type='password']"
    submit_selector: str = "button[type='submit']"
    post_login_wait_ms: int = 3000
    storage_state_path: str = "/tmp/storage_state.json"
    reuse_storage_state: bool = True


@dataclass
class Config:
    """Main configuration class."""
    start_url: str
    max_depth: int
    max_clicks_per_page: int
    wait_timeout: int = 30000
    network_idle_timeout: int = 2000
    http_credentials: Dict[str, str] = None
    form_filling: FormConfig = None
    exclude_patterns: list = None
    login: Optional[LoginConfig] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = ["logout", "delete", "remove", "login", "signin"]


def _fetch_vault_pair(
    vault_path: str,
    username_key: str,
    password_key: str,
) -> tuple[str, str]:
    client = get_default_client()
    data = client.read_kv(vault_path)
    if username_key not in data or password_key not in data:
        raise VaultError(
            f"Vault secret {vault_path} missing keys '{username_key}' and/or '{password_key}'"
        )
    return data[username_key], data[password_key]


def _resolve_http_credentials(data: dict) -> Optional[Dict[str, str]]:
    block = data.get('http_credentials')
    if not block:
        return None

    vault_path = block.get('vault_path') or os.environ.get('VAULT_HTTP_CREDENTIALS_PATH')
    if vault_path:
        username, password = _fetch_vault_pair(
            vault_path,
            block.get('username_key', 'username'),
            block.get('password_key', 'password'),
        )
        return {'username': username, 'password': password}

    # Legacy plaintext (discouraged outside local dev)
    if 'username' in block and 'password' in block:
        return {'username': block['username'], 'password': block['password']}
    raise ValueError("http_credentials must provide 'vault_path' or explicit username/password")


def _resolve_login(data: dict) -> Optional[LoginConfig]:
    if 'login' not in data:
        return None
    block = data['login']

    vault_path = block.get('vault_path') or os.environ.get('VAULT_LOGIN_PATH')
    if not vault_path:
        raise ValueError(
            "login block requires 'vault_path' (or VAULT_LOGIN_PATH env) to resolve credentials"
        )

    username, password = _fetch_vault_pair(
        vault_path,
        block.get('username_key', 'app_username'),
        block.get('password_key', 'app_password'),
    )

    if not block.get('login_url'):
        raise ValueError("login block requires 'login_url'")

    return LoginConfig(
        login_url=block['login_url'],
        username=username,
        password=password,
        username_selector=block.get('username_selector', "#username"),
        password_selector=block.get('password_selector', "input[type='password']"),
        submit_selector=block.get('submit_selector', "button[type='submit']"),
        post_login_wait_ms=block.get('post_login_wait_ms', 3000),
        storage_state_path=block.get('storage_state_path', "/tmp/storage_state.json"),
        reuse_storage_state=block.get('reuse_storage_state', True),
    )


def load_config(config_path: str) -> Config:
    """Load configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    form_data = data.get('form_filling', {})
    form_config = FormConfig(
        enabled=form_data.get('enabled', True),
        fill_delay=form_data.get('fill_delay', 100),
        defaults=form_data.get('defaults', {}),
    )

    return Config(
        start_url=data['start_url'],
        max_depth=data.get('max_depth', 3),
        max_clicks_per_page=data.get('max_clicks_per_page', 20),
        wait_timeout=data.get('wait_timeout', 30000),
        network_idle_timeout=data.get('network_idle_timeout', 2000),
        http_credentials=_resolve_http_credentials(data),
        form_filling=form_config,
        exclude_patterns=data.get('exclude_patterns'),
        login=_resolve_login(data),
    )
