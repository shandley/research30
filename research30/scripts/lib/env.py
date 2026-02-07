"""Environment and config management for research30 skill."""

import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".config" / "research30"
CONFIG_FILE = CONFIG_DIR / ".env"


def load_env_file(path: Path) -> Dict[str, str]:
    """Load environment variables from a file."""
    env = {}
    if not path.exists():
        return env

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                if key and value:
                    env[key] = value
    return env


def get_config() -> Dict[str, Any]:
    """Load configuration from environment and config file.

    NCBI_API_KEY is optional — increases PubMed rate limit from 3/sec to 10/sec.
    S2_API_KEY is optional — enables Semantic Scholar as a source.
    """
    file_env = load_env_file(CONFIG_FILE)

    config = {
        'NCBI_API_KEY': os.environ.get('NCBI_API_KEY') or file_env.get('NCBI_API_KEY'),
        'S2_API_KEY': os.environ.get('S2_API_KEY') or file_env.get('S2_API_KEY'),
    }

    return config
