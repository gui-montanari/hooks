"""
Configuration management for test automation
"""

import json
from pathlib import Path
from typing import Dict, Any

from .logger import logger


class Config:
    """Manages test automation configuration"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        config_path = Path(__file__).parent.parent.parent / 'test_automation_config.json'
        
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            logger.info(f"Loaded test automation config from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Use default config
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "test_generator": {
                "enabled": True,
                "auto_generate": True,
                "test_framework": "pytest",
                "templates": {
                    "endpoint": "hooks/test_automation/templates/endpoint_test.py.tmpl",
                    "service": "hooks/test_automation/templates/service_test.py.tmpl",
                    "model": "hooks/test_automation/templates/model_test.py.tmpl"
                },
                "naming": {
                    "test_dir": "tests",
                    "test_prefix": "test_",
                    "test_suffix": ""
                }
            },
            "test_runner": {
                "enabled": True,
                "pytest_args": ["-v", "--tb=short"],
                "coverage": {
                    "enabled": True,
                    "minimum": 80,
                    "exclude": ["**/migrations/**", "**/tests/**", "**/__pycache__/**"]
                },
                "tracking": {
                    "enabled": True,
                    "history_size": 30,
                    "identify_flaky_threshold": 0.7
                },
                "reports": {
                    "markdown": True,
                    "json": True
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        parts = key.split('.')
        value = self._config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        parts = key.split('.')
        config = self._config
        
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        config[parts[-1]] = value
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_config()


# Global config instance
config = Config()