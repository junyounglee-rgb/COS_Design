"""YAML config load/save for quest_tool."""
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "quests_path": "",
    "items_path": "",
    "keywords_path": "",
    "dialog_groups_path": "",
    "nday_mission_events_path": "",   # 추가
}


def load_config(config_path: str) -> dict:
    """config_path YAML load. File not found -> DEFAULT_CONFIG."""
    p = Path(config_path)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **data}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict, config_path: str) -> None:
    """Save config dict to YAML file."""
    p = Path(config_path)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
