"""
Configuration loader for Migration Guardian
"""

import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "auto_generate": True,
    "require_review": True,
    "block_dangerous": False,
    "analyze_data_impact": True,
    "generate_rollback": True,
    "staging_test_required": True,
    
    "monitored_paths": [
        "app/*/models/*.py",
        "app/*/models/**/*.py",
        "app/core/models/*.py",
        "app/shared/models/*.py"
    ],
    
    "module_detection": {
        "enabled": True,
        "extract_module_name": True,
        "prefix_migrations_with_module": True
    },
    
    "dangerous_operations": [
        "DROP TABLE",
        "DROP COLUMN",
        "DROP CONSTRAINT",
        "ALTER COLUMN.*NOT NULL",
        "DELETE FROM",
        "TRUNCATE"
    ],
    
    "safety_thresholds": {
        "max_affected_rows_auto": 1000,
        "require_backup_above_rows": 10000,
        "require_staged_migration_above": 100000
    },
    
    "naming_convention": {
        "format": "{timestamp}_{module}_{description}",
        "timestamp": "%Y_%m_%d_%H%M",
        "dangerous_suffix": "_DANGEROUS",
        "staged_suffix": "_staged",
        "module_separator": "_"
    },
    
    "cross_module_detection": {
        "enabled": True,
        "warn_on_cross_dependencies": True,
        "generate_dependency_graph": True
    },
    
    "auto_backup": {
        "enabled": True,
        "location": ".claude/db_backups/",
        "before_dangerous_ops": True,
        "include_module_name": True
    }
}


def load_config() -> Dict[str, Any]:
    """Load configuration from migration_guardian_config.json"""
    config_path = Path("hooks/migration_guardian_config.json")
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                user_config = json.load(f)
                
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            
            # Deep merge user config with defaults
            for key, value in user_config.items():
                if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                    config[key].update(value)
                else:
                    config[key] = value
                    
            return config
            
        except Exception as e:
            print(f"⚠️  Error loading migration_guardian_config.json, using defaults: {e}")
            
    return DEFAULT_CONFIG