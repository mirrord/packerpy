"""Unit tests for config.settings module."""

import pytest

from packerpy.config.settings import NetworkConfig


class TestNetworkConfig:
    """Test suite for NetworkConfig dataclass."""

    def test_initialization_defaults(self):
        """Test NetworkConfig initialization with default values."""
        config = NetworkConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.buffer_size == 4096
        assert config.timeout == 30.0
        assert config.max_connections == 100
        assert config.protocol == "tcp"
        assert config.async_mode is True
        assert config.use_ssl is False
        assert config.ssl_cert_path is None
        assert config.ssl_key_path is None

    def test_initialization_custom_values(self):
        """Test NetworkConfig initialization with custom values."""
        config = NetworkConfig(
            host="127.0.0.1",
            port=9000,
            buffer_size=8192,
            timeout=60.0,
            max_connections=200,
            protocol="udp",
            async_mode=False,
            use_ssl=True,
            ssl_cert_path="/path/to/cert.pem",
            ssl_key_path="/path/to/key.pem",
        )

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.buffer_size == 8192
        assert config.timeout == 60.0
        assert config.max_connections == 200
        assert config.protocol == "udp"
        assert config.async_mode is False
        assert config.use_ssl is True
        assert config.ssl_cert_path == "/path/to/cert.pem"
        assert config.ssl_key_path == "/path/to/key.pem"

    def test_dataclass_equality(self):
        """Test that two NetworkConfig instances with same values are equal."""
        config1 = NetworkConfig(host="localhost", port=8080)
        config2 = NetworkConfig(host="localhost", port=8080)

        assert config1 == config2

    def test_dataclass_inequality(self):
        """Test that two NetworkConfig instances with different values are not equal."""
        config1 = NetworkConfig(host="localhost", port=8080)
        config2 = NetworkConfig(host="localhost", port=9000)

        assert config1 != config2

    def test_dataclass_repr(self):
        """Test NetworkConfig string representation."""
        config = NetworkConfig(host="127.0.0.1", port=8080)
        repr_str = repr(config)

        assert "NetworkConfig" in repr_str
        assert "127.0.0.1" in repr_str
        assert "8080" in repr_str

    def test_partial_initialization(self):
        """Test NetworkConfig with only some parameters provided."""
        config = NetworkConfig(host="192.168.1.1", buffer_size=2048)

        assert config.host == "192.168.1.1"
        assert config.buffer_size == 2048
        assert config.port == 8080  # default
        assert config.timeout == 30.0  # default

    def test_ssl_configuration(self):
        """Test SSL-related configuration."""
        config = NetworkConfig(
            use_ssl=True,
            ssl_cert_path="/etc/ssl/cert.pem",
            ssl_key_path="/etc/ssl/key.pem",
        )

        assert config.use_ssl is True
        assert config.ssl_cert_path == "/etc/ssl/cert.pem"
        assert config.ssl_key_path == "/etc/ssl/key.pem"

    def test_protocol_types(self):
        """Test different protocol configurations."""
        tcp_config = NetworkConfig(protocol="tcp")
        udp_config = NetworkConfig(protocol="udp")

        assert tcp_config.protocol == "tcp"
        assert udp_config.protocol == "udp"

    def test_async_mode_toggle(self):
        """Test async mode can be toggled."""
        async_config = NetworkConfig(async_mode=True)
        sync_config = NetworkConfig(async_mode=False)

        assert async_config.async_mode is True
        assert sync_config.async_mode is False

    def test_numeric_types(self):
        """Test that numeric fields accept appropriate types."""
        config = NetworkConfig(
            port=int(8080),
            buffer_size=int(4096),
            timeout=float(30.0),
            max_connections=int(100),
        )

        assert isinstance(config.port, int)
        assert isinstance(config.buffer_size, int)
        assert isinstance(config.timeout, float)
        assert isinstance(config.max_connections, int)
