import json
import os
from typing import Dict, Optional
from dataclasses import dataclass


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


def _read_env_pair(block: dict) -> tuple[str, str]:
    username_env = block.get('username_env')
    password_env = block.get('password_env')
    if not username_env or not password_env:
        raise ValueError("block requires 'username_env' and 'password_env' keys")

    username = os.environ.get(username_env)
    password = os.environ.get(password_env)
    if not username or not password:
        raise ValueError(
            f"env vars {username_env!r} and/or {password_env!r} are not set"
        )
    return username, password


def _resolve_http_credentials(data: dict) -> Optional[Dict[str, str]]:
    block = data.get('http_credentials')
    if not block:
        return None

    username, password = _read_env_pair(block)
    return {'username': username, 'password': password}


def _resolve_login(data: dict) -> Optional[LoginConfig]:
    if 'login' not in data:
        return None
    block = data['login']

    username, password = _read_env_pair(block)

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
