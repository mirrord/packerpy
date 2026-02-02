# Test Suite for PackerPy

## Overview
Comprehensive unit test suite covering all modules in the PackerPy project.

## Test Files Created (14 total)

### Phase 1: Simple Modules
- ✅ `test_config.py` - NetworkConfig dataclass tests
- ✅ `test_handlers.py` - BaseHandler interface tests

### Phase 2: Protocol Foundation
- ✅ `test_serializer.py` - BytesSerializer tests
- ✅ `test_message_partial.py` - MessagePartial and encoders (most complex!)
- ✅ `test_message.py` - Message class tests
- ✅ `test_protocol.py` - Protocol encoder/decoder tests

### Phase 3: Transport Layer
- ✅ `test_tcp_sync_client.py` - Synchronous TCP client
- ✅ `test_tcp_sync_server.py` - Synchronous TCP server
- ✅ `test_tcp_async_client.py` - Asynchronous TCP client
- ✅ `test_tcp_async_server.py` - Asynchronous TCP server
- ✅ `test_udp_sync_socket.py` - Synchronous UDP socket
- ✅ `test_udp_async_socket.py` - Asynchronous UDP socket

### Phase 4: High-Level API
- ✅ `test_client.py` - High-level Client class
- ✅ `test_server.py` - High-level Server class

## Setup

### Install Dependencies
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"
```

### Dependencies Added
- pytest>=8.0.0
- pytest-asyncio>=0.23.0
- pytest-cov>=4.1.0
- pytest-mock>=3.12.0

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Verbose Output
```bash
pytest -v
```

### Workaround for Long-Running Tests (Output Viewing)
When tests take too long and output gets truncated, save results to a file:

```powershell
# Run tests and save output to file
pytest -v > test_results.txt 2>&1

# Or with more detail
pytest -vv --tb=long > test_output.txt 2>&1

# View the output after completion
cat test_results.txt
# or
Get-Content test_results.txt
```

On Unix/Linux/macOS:
```bash
pytest -v | tee test_results.txt
```

### Alternative: Run Specific Test Subsets
```bash
# Run only fast tests
pytest -v tests/unit/test_config.py tests/unit/test_handlers.py

# Run one module at a time
pytest -v tests/unit/test_message_partial.py > partial_results.txt 2>&1
```

### Run with Coverage
```bash
pytest --cov=src/packerpy --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/unit/test_config.py
pytest tests/unit/test_message_partial.py
```

### Run Specific Test Class
```bash
pytest tests/unit/test_config.py::TestNetworkConfig
```

### Run Specific Test Function
```bash
pytest tests/unit/test_config.py::TestNetworkConfig::test_initialization_defaults
```

### Run Tests by Marker
```bash
# Run only async tests
pytest -k "async"

# Run only sync tests
pytest -k "sync"

# Run specific module tests
pytest -k "message"
```

### Run Tests in Parallel (if pytest-xdist installed)
```bash
pytest -n auto
```

## Test Coverage

### Generate Coverage Report
```bash
# HTML report (opens in browser)
pytest --cov=src/packerpy --cov-report=html
start htmlcov/index.html

# Terminal report
pytest --cov=src/packerpy --cov-report=term

# Combined
pytest --cov=src/packerpy --cov-report=html --cov-report=term
```

### Coverage Goals
- Overall: >90%
- Critical modules (message.py, message_partial.py, protocol.py): >95%

## Test Structure

### Test Organization
```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_handlers.py
│   ├── test_serializer.py
│   ├── test_message_partial.py (500+ lines!)
│   ├── test_message.py
│   ├── test_protocol.py
│   ├── test_tcp_sync_client.py
│   ├── test_tcp_sync_server.py
│   ├── test_tcp_async_client.py
│   ├── test_tcp_async_server.py
│   ├── test_udp_sync_socket.py
│   ├── test_udp_async_socket.py
│   ├── test_client.py
│   └── test_server.py
└── integration/
    └── (future integration tests)
```

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<description>`

## Key Test Features

### Mocking
All tests use proper mocking to isolate units:
- Socket operations mocked with `unittest.mock`
- Asyncio operations mocked with `AsyncMock`
- Threading behavior controlled with mocks
- No actual network calls made

### Async Tests
Async tests marked with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected
```

### Fixtures
Common test fixtures can be added to `conftest.py`:
```python
# tests/conftest.py
import pytest

@pytest.fixture
def sample_message():
    return Message(...)
```

## Debugging Tests

### Run with Output
```bash
pytest -s  # Don't capture stdout
pytest -v -s  # Verbose with output
```

### Run with Debugger
```bash
pytest --pdb  # Drop into debugger on failure
pytest --trace  # Drop into debugger at start
```

### Show Print Statements
```bash
pytest -s --capture=no
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src/packerpy --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Common Issues

### Import Errors
If you see import errors, make sure:
1. You're in the project root directory
2. The package is installed: `uv sync` or `pip install -e .`
3. PYTHONPATH includes src: This is configured in pytest.ini

### Async Test Failures
If async tests fail:
1. Ensure pytest-asyncio is installed
2. Check that `@pytest.mark.asyncio` decorator is present
3. Verify `asyncio_mode = auto` in pytest.ini

### Mock Not Working
If mocks aren't being called:
1. Check the import path in `@patch()`
2. Use `patch.object()` for instance methods
3. Verify the mock is set up before the code runs

## Test Statistics

Total test files: 15
Estimated total tests: ~300+
Most complex module: test_message_partial.py (~50 test methods)

## Next Steps

1. Run the full test suite: `pytest -v`
2. Check coverage: `pytest --cov=src/packerpy`
3. Fix any failing tests
4. Add integration tests in tests/integration/
5. Set up CI/CD pipeline
6. Monitor coverage over time

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Maintain >90% coverage
3. Follow existing test patterns
4. Use descriptive test names
5. Mock external dependencies
6. Test both success and error paths
