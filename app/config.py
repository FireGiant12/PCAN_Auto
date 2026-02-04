"""Configuration management for PCAN_Auto.

Supports loading configuration from JSON files with environment variable overrides.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChannelConfigData:
    """Configuration for a CAN channel."""
    channel: str
    bitrate: int = 500000
    fd: bool = False
    data_bitrate: Optional[int] = None
    listen_only: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    channels: List[ChannelConfigData]
    log_level: str = "INFO"
    log_file: Optional[str] = None
    enable_trace: bool = False
    trace_file: Optional[str] = None
    
    @classmethod
    def from_file(cls, path: Path) -> 'AppConfig':
        """Load configuration from JSON file.
        
        Args:
            path: Path to configuration JSON file
            
        Returns:
            AppConfig instance
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded config from {path}")
            return cls._from_dict(data)
        except FileNotFoundError:
            logger.error(f"Config file not found: {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise ValueError(f"Invalid config format: {e}")
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables.
        
        Supported variables:
        - PCAN_CHANNELS: JSON array of channel configs
        - PCAN_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR)
        - PCAN_LOG_FILE: Log file path
        - PCAN_ENABLE_TRACE: Enable message tracing (true/false)
        - PCAN_TRACE_FILE: Trace file path
        
        Returns:
            AppConfig instance
        """
        config_data = {
            'log_level': os.environ.get('PCAN_LOG_LEVEL', 'INFO'),
            'log_file': os.environ.get('PCAN_LOG_FILE'),
            'enable_trace': os.environ.get('PCAN_ENABLE_TRACE', 'false').lower() == 'true',
            'trace_file': os.environ.get('PCAN_TRACE_FILE'),
        }
        
        # Parse channels from environment
        channels_env = os.environ.get('PCAN_CHANNELS')
        if channels_env:
            try:
                channels_data = json.loads(channels_env)
                config_data['channels'] = [
                    ChannelConfigData(**ch) for ch in channels_data
                ]
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Invalid PCAN_CHANNELS: {e}")
                config_data['channels'] = []
        else:
            config_data['channels'] = []
        
        logger.info("Loaded config from environment variables")
        return cls(**config_data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create config from dictionary."""
        channels = []
        for ch_data in data.get('channels', []):
            channels.append(ChannelConfigData(**ch_data))
        
        return cls(
            channels=channels,
            log_level=data.get('log_level', 'INFO'),
            log_file=data.get('log_file'),
            enable_trace=data.get('enable_trace', False),
            trace_file=data.get('trace_file')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'channels': [asdict(ch) for ch in self.channels],
            'log_level': self.log_level,
            'log_file': self.log_file,
            'enable_trace': self.enable_trace,
            'trace_file': self.trace_file
        }
    
    def save(self, path: Path) -> None:
        """Save configuration to JSON file.
        
        Args:
            path: Path to write configuration to
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Saved config to {path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}", exc_info=True)
            raise


def create_default_config() -> AppConfig:
    """Create default configuration.
    
    Returns:
        AppConfig with default settings
    """
    return AppConfig(
        channels=[
            ChannelConfigData(channel="PCAN_USBBUS1", bitrate=500000),
            ChannelConfigData(channel="PCAN_USBBUS2", bitrate=500000),
        ],
        log_level="INFO",
        enable_trace=False
    )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load application configuration.
    
    Priority order:
    1. Explicit config_path parameter
    2. Environment variables
    3. Default config file (./config.json)
    4. Built-in defaults
    
    Args:
        config_path: Optional explicit config file path
        
    Returns:
        AppConfig instance
    """
    # Try explicit path first
    if config_path:
        if config_path.exists():
            return AppConfig.from_file(config_path)
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
    
    # Try environment variables
    if os.environ.get('PCAN_CHANNELS'):
        config = AppConfig.from_env()
        if config.channels:
            return config
    
    # Try default config file
    default_config_path = Path("config.json")
    if default_config_path.exists():
        return AppConfig.from_file(default_config_path)
    
    # Use defaults
    logger.info("Using default configuration")
    return create_default_config()
