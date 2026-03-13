"""Configuration loader for GitHub Gaant."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import find_dotenv, load_dotenv

from .models import Config


def _load_env_file() -> None:
    """Load .env file from current working directory or parent directories."""
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)


def find_config_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find config.yaml in current directory or parents."""
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path
    while current != current.parent:
        config_path = current / "config.yaml"
        if config_path.exists():
            return config_path
        current = current.parent
    
    return None


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file and environment."""
    # Load .env file
    _load_env_file()
    
    # Find config file
    if config_path is None:
        config_path = find_config_file()
    
    if config_path is None or not config_path.exists():
        raise FileNotFoundError(
            "config.yaml not found. Run 'gaant init' to create one."
        )
    
    # Load YAML
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    
    return Config(**data)


def get_github_token() -> str:
    """Get GitHub token from environment."""
    _load_env_file()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN not set. Add it to .env file or set environment variable."
        )
    return token


def save_config(config: Config, config_path: Path) -> None:
    """Save configuration to YAML file."""
    data = {
        "repo": config.repo,
        "project_number": config.project_number,
        "date_fields": {
            "start": config.date_fields.start,
            "end": config.date_fields.end,
        },
        "output_file": config.output_file,
        "include_closed": config.include_closed,
    }
    
    if config.labels_filter:
        data["labels_filter"] = config.labels_filter
    
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
