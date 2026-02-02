# Unit Testing Plan for PackerPy

## Project Overview
PackerPy is a bitwise data packer/unpacker for Python focused on network communications. It provides a clean architecture with:
- High-level Client/Server classes
- Message abstraction with declarative field definitions
- Protocol layer for encoding/decoding
- Transport layer (TCP/UDP, sync/async)
- BYTES serialization format
- Custom field encoders (FixedPoint, Enum, RunLength, 7-bit ASCII, Bitwise)

## Testing Framework
- **Framework:** pytest (already in dev-dependencies)
- **Python Version:** >=3.10
- **Test Structure:** tests/unit/ directory

## Modules to Test

### 1. Config Module (`config/settings.py`)
**File:** `test_config.py`
- Test `NetworkConfig` dataclass initialization
- Test default values
- Test field validation (if any)
- Test dataclass features (equality, repr, etc.)

### 2. Handlers Module (`handlers/base.py`)
**File:** `test_handlers.py`
- Test `BaseHandler` abstract interface
- Create concrete test implementation
- Test `handle()` method contract
- Test `on_connect()` callback
- Test `on_disconnect()` callback

### 3. Protocols - Serializer (`protocols/serializer.py`)
**File:** `test_serializer.py`
- Test `BytesSerializer.serialize()` with Message objects
- Test `BytesSerializer.deserialize()` with byte data
- Test error handling for invalid data
- Mock Message class for testing

### 4. Protocols - Message Partial (`protocols/message_partial.py`)
**File:** `test_message_partial.py`

**This is the MOST COMPLEX module - requires extensive testing:**

#### MessagePartial Base Class
- Test initialization with kwargs
- Test serialize_bytes() for various field types:
  - Built-in types: int, str, float, double, bool, bytes
  - Sized integers: int(8), int(16), int(32), int(64), uint(8-64)
  - Nested MessagePartial
  - Fixed arrays (numlist)
  - Dynamic arrays (dynamic_array)
  - Delimiter arrays
- Test deserialize_bytes() for all field types
- Test validate() method
- Test to_dict() and from_dict() conversions
- Test both BIG_ENDIAN and LITTLE_ENDIAN encoding

#### Bitwise Encoding
- Test bitwise mode with bit fields
- Test _serialize_bitwise() and _deserialize_bitwise()
- Test mixed bit sizes (1-bit, 3-bit, 5-bit, etc.)
- Test signed vs unsigned bitwise fields
- Test bitwise arrays
- Test BitPackingContext and BitUnpackingContext
- Test byte boundary handling and padding

#### Field Encoders
Each encoder needs dedicated tests:

**FixedPointEncoder:**
- Test encoding/decoding with various precision (16.16, 8.24, etc.)
- Test signed and unsigned fixed-point
- Test edge cases (max/min values)
- Test rounding behavior

**EnumEncoder:**
- Test encoding/decoding IntEnum values
- Test various sizes (1, 2, 4 bytes)
- Test invalid enum values
- Test enum to int and back

**RunLengthEncoder:**
- Test encoding repeated sequences
- Test decoding run-length data
- Test edge cases (empty data, no repeats, all same)
- Test length prefix handling

**SevenBitASCIIEncoder:**
- Test packing 8 chars into 7 bytes
- Test unpacking
- Test various string lengths
- Test ASCII character range

**BitwiseEncoder:**
- Test various bit counts (1-64 bits)
- Test signed vs unsigned
- Test value range validation
- Test bit packing/unpacking

#### Context Classes
**BitPackingContext:**
- Test pack_bits() with various bit counts
- Test flush() with partial bytes
- Test byte boundary crossing
- Test accumulation of multiple fields

**BitUnpackingContext:**
- Test unpack_bits() with various bit counts
- Test get_bytes_consumed()
- Test reading across byte boundaries
- Test insufficient data handling

### 5. Protocols - Message (`protocols/message.py`)
**File:** `test_message.py`
- Test Message base class with declarative fields
- Test all field types (same as MessagePartial)
- Test serialize_bytes() and deserialize_bytes()
- Test validate() method
- Test to_dict() and from_dict()
- Test custom encoders
- Test enum fields
- Test nested MessagePartial fields
- Test arrays (fixed, dynamic, delimiter)
- Test bitwise mode in Message
- Test example messages (TemperatureMessage, StatusMessage)

### 6. Protocols - Protocol (`protocols/protocol.py`)
**File:** `test_protocol.py`
- Test Protocol initialization with BytesSerializer
- Test encode_message() with valid messages
- Test decode_message() with valid bytes
- Test validate_message()
- Test create_message() convenience method
- Test error handling (invalid message, invalid bytes)
- Mock Message and BytesSerializer for testing

### 7. Transport - TCP Sync Client (`transports/tcp/sync_client.py`)
**File:** `test_tcp_sync_client.py`
- Test SyncTCPClient initialization
- Test connect() method
- Test send() method
- Test receive() method
- Test close() method
- Test context manager (__enter__, __exit__)
- Test error handling (not connected, connection refused)
- Use mock socket for testing

### 8. Transport - TCP Sync Server (`transports/tcp/sync_server.py`)
**File:** `test_tcp_sync_server.py`
- Test SyncTCPServer initialization
- Test start() method
- Test stop() method
- Test _handle_client() method
- Test handler callback invocation
- Test error handling
- Use mock socket for testing

### 9. Transport - TCP Async Client (`transports/tcp/async_client.py`)
**File:** `test_tcp_async_client.py`
- Test AsyncTCPClient initialization
- Test async connect() method
- Test async send() method
- Test async receive() method
- Test async close() method
- Test async context manager (__aenter__, __aexit__)
- Test error handling
- Use pytest-asyncio for async tests
- Mock asyncio.open_connection

### 10. Transport - TCP Async Server (`transports/tcp/async_server.py`)
**File:** `test_tcp_async_server.py`
- Test AsyncTCPServer initialization
- Test async start() method
- Test async stop() method
- Test async _handle_client() method
- Test handler callback invocation
- Test error handling
- Use pytest-asyncio for async tests
- Mock asyncio.start_server

### 11. Transport - UDP Sync Socket (`transports/udp/sync_socket.py`)
**File:** `test_udp_sync_socket.py`
- Test SyncUDPSocket initialization
- Test bind() method
- Test send_to() method
- Test receive_from() method
- Test close() method
- Test context manager
- Test auto-assigned port (port=0)
- Use mock socket for testing

### 12. Transport - UDP Async Socket (`transports/udp/async_socket.py`)
**File:** `test_udp_async_socket.py`
- Test AsyncUDPSocket initialization
- Test AsyncUDPProtocol class
- Test async bind() method
- Test async send_to() method
- Test async receive_from() method
- Test async close() method
- Test async context manager
- Test error handling
- Use pytest-asyncio for async tests
- Mock asyncio.create_datagram_endpoint

### 13. High-Level Client (`client.py`)
**File:** `test_client.py`
- Test Client initialization
- Test connect() method (starts background thread)
- Test send() method with Message objects
- Test receive() method with timeout
- Test close() method
- Test get_status() and ConnectionStatus enum
- Test get_error() method
- Test _receive_loop() background processing
- Test _run_async_client() thread execution
- Test error handling and status transitions
- Mock AsyncTCPClient and Protocol

### 14. High-Level Server (`server.py`)
**File:** `test_server.py`
- Test Server initialization
- Test start() method (starts background thread)
- Test stop() method
- Test receive() method with timeout
- Test send() method (note: limited for TCP)
- Test get_status() and ConnectionStatus enum
- Test get_error() method
- Test _handle_raw_data() callback
- Test message_handler invocation
- Test _run_async_server() thread execution
- Test error responses for invalid messages
- Mock AsyncTCPServer and Protocol

## Testing Strategy

### Unit Test Principles
1. **Isolation:** Each test should test one unit in isolation
2. **Mocking:** Mock external dependencies (sockets, asyncio, threads)
3. **Coverage:** Aim for >90% code coverage
4. **Edge Cases:** Test boundary conditions, empty data, max values
5. **Error Paths:** Test all error handling code
6. **Async Tests:** Use pytest-asyncio for async code

### Common Test Patterns

#### For Data Classes
```python
def test_initialization():
    obj = MyClass(param1=value1, param2=value2)
    assert obj.param1 == value1
    assert obj.param2 == value2

def test_defaults():
    obj = MyClass()
    assert obj.param1 == default_value
```

#### For Serialization
```python
def test_round_trip():
    original = create_test_data()
    serialized = serialize(original)
    deserialized = deserialize(serialized)
    assert deserialized == original
```

#### For Async Code
```python
import pytest

@pytest.mark.asyncio
async def test_async_method():
    obj = AsyncClass()
    result = await obj.async_method()
    assert result == expected
```

#### For Context Managers
```python
def test_context_manager():
    with MyClass() as obj:
        # Test usage
        pass
    # Test cleanup happened
```

#### For Threading Code
```python
def test_background_thread():
    obj = MyClass()
    obj.start()  # Starts thread
    time.sleep(0.1)  # Let thread initialize
    assert obj.is_running()
    obj.stop()  # Stops thread
```

### Mocking Guidelines

#### Mock Sockets
```python
from unittest.mock import Mock, patch, MagicMock

@patch('socket.socket')
def test_with_mock_socket(mock_socket):
    mock_instance = mock_socket.return_value
    mock_instance.recv.return_value = b'test data'
    # Test code using socket
```

#### Mock Asyncio
```python
@pytest.mark.asyncio
@patch('asyncio.open_connection')
async def test_with_mock_asyncio(mock_open):
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_open.return_value = (mock_reader, mock_writer)
    # Test code
```

## Test Execution Order

### Phase 1: Simple Modules (Start Here)
1. test_config.py
2. test_handlers.py

### Phase 2: Protocol Foundation
3. test_serializer.py
4. test_message_partial.py (extensive!)
5. test_message.py (extensive!)
6. test_protocol.py

### Phase 3: Transport Layer
7. test_tcp_sync_client.py
8. test_tcp_sync_server.py
9. test_udp_sync_socket.py
10. test_tcp_async_client.py
11. test_tcp_async_server.py
12. test_udp_async_socket.py

### Phase 4: High-Level API
13. test_client.py
14. test_server.py

## Dependencies Needed
```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
]
```

## Coverage Goals
- **Overall:** >90%
- **Critical Modules:** >95% (message.py, message_partial.py, protocol.py)
- **Edge Cases:** All error paths covered

## Notes on Complex Areas

### Message/MessagePartial Serialization
- These are the core of the system
- Support many field types and encoding modes
- Need comprehensive tests for all type combinations
- Bitwise encoding is particularly complex
- Test byte order (big/little endian) for all numeric types

### Async Code
- Use pytest-asyncio
- Be careful with event loops
- Mock asyncio functions, not actual network calls
- Test timeout scenarios

### Threading Code
- Client and Server use background threads
- Test thread lifecycle (start, run, stop)
- Use small timeouts in tests (sleep 0.1s)
- Test status transitions
- Test queue-based communication

### Error Handling
- Test all ValueError, ConnectionError paths
- Test insufficient data scenarios
- Test invalid message formats
- Test connection failures

## Test File Template

```python
"""Unit tests for [module name]."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from packerpy.[module] import [ClassToTest]


class Test[ClassName]:
    """Test suite for [ClassName]."""
    
    def test_initialization(self):
        """Test basic initialization."""
        obj = [ClassName]()
        assert obj is not None
    
    def test_[specific_functionality](self):
        """Test [specific functionality]."""
        # Arrange
        obj = [ClassName]()
        
        # Act
        result = obj.method()
        
        # Assert
        assert result == expected
    
    def test_[error_case](self):
        """Test error handling for [case]."""
        obj = [ClassName]()
        
        with pytest.raises(ExpectedException):
            obj.method_that_fails()


# For async tests
@pytest.mark.asyncio
class TestAsync[ClassName]:
    """Async test suite for [ClassName]."""
    
    async def test_async_method(self):
        """Test async method."""
        obj = [ClassName]()
        result = await obj.async_method()
        assert result == expected
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/packerpy --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py

# Run with verbose output
pytest -v

# Run async tests
pytest -v -k "async"
```

## Priority Features to Test

### Critical (Must Test First)
1. Message serialization/deserialization (core functionality)
2. Protocol encode/decode
3. Field type support (int, str, float, etc.)
4. BytesSerializer

### High Priority
5. Transport layer (TCP/UDP clients/servers)
6. Client/Server high-level API
7. Custom encoders (FixedPoint, Enum)
8. Bitwise encoding

### Medium Priority
9. Error handling and validation
10. Context managers
11. Async functionality
12. Threading behavior

### Lower Priority
13. Advanced encoders (RunLength, SevenBitASCII)
14. Edge cases and boundary conditions
15. Performance characteristics

## Implementation Notes

### Key Insights from Code Review

1. **Message vs MessagePartial:** Both have nearly identical implementations with serialize/deserialize. MessagePartial is meant for nested structures.

2. **Bitwise Mode:** Special mode where fields are packed at bit-level resolution. Requires BitPackingContext/BitUnpackingContext.

3. **Custom Encoders:** FieldEncoder base class allows arbitrary encoding schemes. Must implement encode() and decode() methods.

4. **Arrays:** Three types supported:
   - Fixed (numlist): Fixed-size array
   - Dynamic (dynamic_array): Length-prefixed array
   - Delimiter: Delimiter-separated array

5. **Threading Architecture:** Client and Server run async code in background threads, exposing sync API to user.

6. **Status Enums:** Both Client and Server use ConnectionStatus enum to track state.

7. **Error Handling:** Errors stored in _error attribute, status set to ERROR state.

8. **Queue-based Communication:** Received messages stored in Queue for user to consume.

## Expected Challenges

1. **Mocking Threading:** Client/Server use threads + asyncio. Need to carefully mock both.
2. **Bitwise Encoding:** Complex bit manipulation. Need thorough edge case testing.
3. **Async Context Managers:** Requires pytest-asyncio and careful setup/teardown.
4. **Socket Mocking:** Need to mock socket behavior realistically.
5. **Field Type Variety:** Many field types need individual test cases.

## Success Criteria

- [ ] All 15 test files created
- [ ] >90% code coverage overall
- [ ] All tests pass
- [ ] pytest-asyncio configured
- [ ] Mock patterns established
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Documentation in docstrings
- [ ] CI/CD ready (if needed)

## Next Steps

1. Update pyproject.toml with test dependencies
2. Start with Phase 1 (simple modules)
3. Build up test utilities/fixtures for reuse
4. Create mock helpers for common patterns
5. Progress through phases systematically
6. Monitor coverage as you go
7. Refactor tests for clarity/maintainability
