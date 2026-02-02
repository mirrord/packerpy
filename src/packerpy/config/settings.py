"""Network configuration settings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkConfig:
    """Network configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    buffer_size: int = 4096
    timeout: float = 30.0
    max_connections: int = 100
    
    # Protocol settings
    protocol: str = "tcp"  # tcp or udp
    async_mode: bool = True
    
    # Security settings
    use_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
