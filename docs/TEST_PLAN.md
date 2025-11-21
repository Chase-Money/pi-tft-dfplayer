# Phase 1 Refactored Codebase Test Plan

## Executive Summary

This document outlines the comprehensive testing strategy for the Phase 1 refactored pi-tft-dfplayer codebase. Current test coverage is minimal for the new modular architecture, and this plan identifies priority areas requiring unit and integration tests.

## Current Test Status

### Existing Tests (Legacy Code)
- **Location**: `tests/`
- **Total Tests**: 35
- **Passing**: 22 (63%)
- **Failing**: 13 (37% - all due to missing evdev on macOS)
- **Coverage**: Legacy monolithic code only

### Test Categories
1. **Code Quality Tests** (11 tests) - ✓ All passing
   - Resource cleanup verification
   - Error handling patterns
   - Main loop protection

2. **Duplicate Code Tests** (4 tests) - ✓ All passing
   - Function uniqueness validation
   - Return type verification

3. **Exception Handling Tests** (4 tests) - ✗ Failing (evdev unavailable on macOS)
   - Serial initialization error handling
   - Touch device initialization error handling

4. **Resource Cleanup Tests** (4 tests) - ✗ Failing (evdev unavailable on macOS)
   - Cleanup handler registration
   - Serial/framebuffer closure verification

5. **Serial Error Handling Tests** (5 tests) - ✗ Failing (evdev unavailable on macOS)
   - Command error handling
   - Packet construction validation
   - Volume clamping

6. **Undefined Variables Tests** (6 tests) - ✓ All passing
   - Track number list validation
   - Track indexing verification

## Bugs Fixed in This Session

### Critical Fixes
1. **Import Error** (`src/backends/dfplayer_backend.py:10`)
   - Changed: `from hardware.dfplayer import DFPlayer`
   - To: `from ..hardware.dfplayer import DFPlayer`
   - Status: ✓ Fixed

2. **Path Traversal Vulnerability** (`src/utils/metadata.py:69`)
   - Added path normalization and validation
   - Prevents `../` escape sequences in artwork paths
   - Status: ✓ Fixed

3. **Thread Safety Issues** (Singleton getters)
   - Added threading.Lock to `config.py`, `state.py`, `events.py`
   - Implemented double-check locking pattern
   - Status: ✓ Fixed

4. **Missing Package Init** (`src/__init__.py`)
   - Created package-level `__init__.py`
   - Status: ✓ Fixed

5. **Import Errors** (utils modules)
   - Fixed `src/utils/track_catalog.py:10` - Changed `from core.state` to `from ..core.state`
   - Fixed `src/utils/calibration.py:12-13` - Changed `from hardware.*` to `from ..hardware.*`
   - Status: ✓ Fixed

## Static Analysis Results

### Module Import Verification
All 10 core modules import successfully:
- ✓ src.core.config
- ✓ src.core.state
- ✓ src.core.events
- ✓ src.utils.metadata
- ✓ src.utils.track_catalog
- ✓ src.utils.calibration
- ✓ src.backends.base
- ✓ src.backends.dfplayer_backend
- ✓ src.hardware.dfplayer
- ✓ src.hardware.framebuffer

### Syntax Check
All 20 Python files parse without syntax errors.

## Integration Test Results

All integration tests passed:
- ✓ Configuration management (load/save/reload)
- ✓ Singleton pattern
- ✓ Application state management
- ✓ Track selection and playback state
- ✓ Event bus pub/sub
- ✓ Metadata loading
- ✓ Track catalog loading

## Required Unit Tests (Priority Order)

### Priority 1: Core Modules (0% coverage currently)

#### `src/core/config.py`
**Required Tests**:
1. `test_config_defaults` - Verify all default values
2. `test_config_load_from_file` - Load existing config
3. `test_config_invalid_json` - Handle malformed JSON gracefully
4. `test_config_save_atomic` - Verify atomic write via temp file
5. `test_config_deep_merge` - Test configuration merging
6. `test_config_get_nested` - Test dot-notation path access
7. `test_config_set_nested` - Test dot-notation path setting
8. `test_config_reset_section` - Reset specific sections
9. `test_config_reset_all` - Reset entire config
10. `test_config_environment_overrides` - Test env var priority
11. `test_config_singleton_thread_safety` - Concurrent get_config() calls
12. `test_config_touch_calibration` - Touch calibration persistence
13. `test_config_volume_clamping` - Volume range validation

**Coverage Goal**: 90%+

#### `src/core/state.py`
**Required Tests**:
1. `test_state_track_management` - Add/get tracks
2. `test_state_empty_tracks` - Handle empty track list
3. `test_state_track_selection` - Select by index
4. `test_state_track_wrapping` - Index wrapping behavior
5. `test_state_advance_track` - Next/previous navigation
6. `test_state_playback_state` - Play/pause/stop transitions
7. `test_state_volume_setting` - Volume state management
8. `test_state_metadata_integration` - Track metadata association
9. `test_state_artwork_cache` - Artwork caching
10. `test_state_scroll_position` - Track list scrolling
11. `test_state_ensure_visible` - Scroll-to-track logic
12. `test_state_singleton_thread_safety` - Concurrent get_state() calls

**Coverage Goal**: 90%+

#### `src/core/events.py`
**Required Tests**:
1. `test_event_subscribe` - Subscribe to event
2. `test_event_unsubscribe` - Unsubscribe from event
3. `test_event_publish` - Publish event with args
4. `test_event_multiple_subscribers` - Multiple callbacks
5. `test_event_callback_exception` - Handle callback errors
6. `test_event_clear_single` - Clear specific event
7. `test_event_clear_all` - Clear all events
8. `test_event_no_duplicate_subscription` - Prevent duplicate subs
9. `test_event_singleton_thread_safety` - Concurrent get_event_bus() calls

**Coverage Goal**: 95%+

### Priority 2: Utilities (0% coverage currently)

#### `src/utils/metadata.py`
**Required Tests**:
1. `test_load_metadata_valid` - Load valid JSON
2. `test_load_metadata_missing_file` - Handle missing file
3. `test_load_metadata_invalid_json` - Handle malformed JSON
4. `test_load_metadata_path_resolution` - Artwork path resolution
5. `test_load_metadata_path_traversal_attack` - Security validation (CRITICAL)
6. `test_load_metadata_both_formats` - Handle {"tracks": {...}} and {...}
7. `test_load_artwork_thumbnail` - Load and resize image
8. `test_load_artwork_missing` - Handle missing artwork
9. `test_load_artwork_invalid_image` - Handle corrupt images
10. `test_artwork_cache_lru` - LRU eviction
11. `test_artwork_cache_hit` - Cache hit behavior
12. `test_artwork_cache_miss` - Cache miss behavior

**Coverage Goal**: 85%+

#### `src/utils/track_catalog.py`
**Required Tests**:
1. `test_load_catalog_pipe_format` - Parse "number|title" format
2. `test_load_catalog_missing_file` - Fallback to generated list
3. `test_load_catalog_invalid_lines` - Skip malformed lines
4. `test_load_catalog_empty_file` - Handle empty file
5. `test_load_catalog_whitespace` - Handle whitespace correctly
6. `test_load_catalog_duplicate_numbers` - Handle duplicates

**Coverage Goal**: 85%+

#### `src/utils/calibration.py`
**Required Tests**:
1. `test_calibration_workflow` - Full 4-point calibration (mock touch)
2. `test_calibration_display_targets` - Verify UI rendering
3. `test_calibration_timeout` - Handle calibration timeout
4. `test_calibration_median_filtering` - Touch sample filtering
5. `test_calibration_bounds_calculation` - Min/max calculation

**Coverage Goal**: 75%+ (hardware-dependent code)

### Priority 3: Backends (0% coverage currently)

#### `src/backends/base.py`
**Required Tests**:
1. `test_backend_abstract_methods` - Verify ABC enforcement
2. `test_backend_init` - Initialization logic
3. `test_backend_error_callback` - Error callback registration
4. `test_backend_metadata_methods` - Optional metadata methods

**Coverage Goal**: 80%+

#### `src/backends/dfplayer_backend.py`
**Required Tests**:
1. `test_dfplayer_backend_init` - Initialization
2. `test_dfplayer_backend_initialize_success` - Successful hardware init
3. `test_dfplayer_backend_initialize_failure` - Handle init failure
4. `test_dfplayer_backend_play_pause_stop` - Playback controls
5. `test_dfplayer_backend_next_prev` - Track navigation
6. `test_dfplayer_backend_play_track` - Specific track playback
7. `test_dfplayer_backend_volume` - Volume control
8. `test_dfplayer_backend_status` - Status reporting
9. `test_dfplayer_backend_shutdown` - Clean shutdown
10. `test_dfplayer_backend_connection_check` - Connection status

**Coverage Goal**: 80%+ (requires mocking DFPlayer)

### Priority 4: Hardware (Partial coverage from legacy tests)

#### `src/hardware/dfplayer.py`
**Required Tests**:
1. `test_dfplayer_packet_construction` - Verify packet format
2. `test_dfplayer_checksum` - Checksum calculation
3. `test_dfplayer_command_methods` - All command methods
4. `test_dfplayer_serial_error_handling` - Serial errors
5. `test_dfplayer_connection_check` - Connection verification

**Coverage Goal**: 85%+

#### `src/hardware/framebuffer.py`
**Required Tests**:
1. `test_framebuffer_init` - Initialization
2. `test_framebuffer_rgb565_conversion` - Color conversion
3. `test_framebuffer_push` - Push frame to device
4. `test_framebuffer_close` - Cleanup
5. `test_framebuffer_missing_device` - Handle missing /dev/fb1

**Coverage Goal**: 75%+ (hardware-dependent)

#### `src/hardware/touch.py`
**Required Tests**:
1. `test_touch_init` - Initialization with all orientations
2. `test_touch_calibration` - Calibration application
3. `test_touch_scale_xy` - Coordinate transformation
4. `test_touch_median_filter` - Touch filtering
5. `test_touch_orientation_configs` - All 8 orientations
6. `test_touch_missing_device` - Handle missing touch device

**Coverage Goal**: 80%+ (hardware-dependent)

## Mock Requirements

To achieve the coverage goals, the following mocks are needed:

### Hardware Mocks
1. **MockDFPlayer** - Simulates DFPlayer Mini responses
2. **MockFramebuffer** - Simulates framebuffer device
3. **MockTouchDevice** - Simulates evdev touch input
4. **MockSerial** - Simulates serial port

### File System Mocks
1. **TempConfig** - Temporary configuration files
2. **TempMetadata** - Temporary metadata JSON
3. **TempCatalog** - Temporary track catalog files

## Test Infrastructure Needs

### Dependencies
```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-timeout>=2.1.0
pillow>=10.0.0
pyserial>=3.5
```

### Test Fixtures (conftest.py)
1. `temp_config` - Temporary config file fixture
2. `mock_dfplayer` - Mock DFPlayer device
3. `mock_framebuffer` - Mock framebuffer
4. `mock_touch` - Mock touch input
5. `sample_tracks` - Sample track catalog
6. `sample_metadata` - Sample metadata JSON

## Continuous Integration Recommendations

### GitHub Actions Workflow
```yaml
- Run pytest on every PR
- Require 80%+ coverage for new code
- Run tests on multiple Python versions (3.9, 3.10, 3.11)
- Generate coverage reports
- Run static analysis (pylint, mypy, flake8)
```

### Pre-commit Hooks
1. `black` - Code formatting
2. `isort` - Import sorting
3. `flake8` - Linting
4. `mypy` - Type checking
5. `pytest` - Unit tests

## Performance Testing

### Load Testing
1. **Event Bus** - Test with 100+ subscribers
2. **Artwork Cache** - Test LRU with 50+ images
3. **Track Catalog** - Test with 1000+ tracks
4. **Config Save** - Test concurrent writes

### Memory Testing
1. Monitor memory usage during long runs
2. Check for memory leaks in caches
3. Verify resource cleanup

## Security Testing

### Input Validation
1. ✓ Path traversal prevention (metadata.py) - FIXED
2. JSON injection in config files
3. Command injection in track titles
4. Buffer overflow in serial commands

### Authentication/Authorization
Not applicable for this project (embedded device)

## Regression Testing

### Legacy Code Compatibility
1. Verify original dfplayer_fb_gui.py still works
2. Test backward compatibility with old config files
3. Test with original track catalog format

## Documentation Testing

### API Documentation
1. Verify all public methods have docstrings
2. Check type hints coverage
3. Validate examples in docstrings

## Test Execution Timeline

### Phase 1 (Immediate - Week 1)
- Complete Priority 1 tests (Core modules)
- Achieve 80%+ coverage on core

### Phase 2 (Week 2)
- Complete Priority 2 tests (Utilities)
- Complete Priority 3 tests (Backends)
- Achieve 75%+ overall coverage

### Phase 3 (Week 3)
- Complete Priority 4 tests (Hardware)
- Add integration tests
- Achieve 80%+ overall coverage

### Phase 4 (Week 4)
- Performance testing
- Security hardening
- Documentation review

## Success Metrics

1. **Code Coverage**: 80%+ overall, 90%+ for core modules
2. **Test Reliability**: 0 flaky tests
3. **CI/CD**: All tests pass on every commit
4. **Bug Detection**: Catch 95%+ of bugs before merge
5. **Test Speed**: Full test suite < 30 seconds

## Known Limitations

1. **evdev dependency** - Cannot test touch input on macOS/Windows
2. **Hardware requirements** - Some tests require actual Raspberry Pi
3. **Serial hardware** - DFPlayer tests need hardware or good mocks
4. **Display hardware** - Framebuffer tests need real device or mocks

## Recommendations for Next Steps

1. **Immediate** (Priority 1):
   - Write core module tests (config, state, events)
   - Set up pytest-cov for coverage tracking
   - Create basic mock infrastructure

2. **Short-term** (Priority 2):
   - Write utility tests (metadata, track_catalog)
   - Add backend tests with mocks
   - Set up CI/CD pipeline

3. **Long-term** (Priority 3):
   - Hardware integration tests on Pi
   - Performance benchmarking
   - Security audit
   - Documentation improvements

4. **Consider**:
   - Property-based testing with Hypothesis
   - Mutation testing with mutmut
   - Contract testing for hardware interfaces
   - Visual regression testing for UI

## Appendix: Test File Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── core/
│   │   ├── test_config.py        # 13 tests
│   │   ├── test_state.py         # 12 tests
│   │   └── test_events.py        # 9 tests
│   ├── utils/
│   │   ├── test_metadata.py      # 12 tests
│   │   ├── test_track_catalog.py # 6 tests
│   │   └── test_calibration.py   # 5 tests
│   ├── backends/
│   │   ├── test_base.py          # 4 tests
│   │   └── test_dfplayer_backend.py  # 10 tests
│   └── hardware/
│       ├── test_dfplayer.py      # 5 tests
│       ├── test_framebuffer.py   # 5 tests
│       └── test_touch.py         # 6 tests
├── integration/
│   ├── __init__.py
│   ├── test_config_state_integration.py
│   ├── test_event_bus_integration.py
│   └── test_backend_integration.py
├── performance/
│   ├── __init__.py
│   └── test_performance.py
└── legacy/                        # Existing tests
    ├── test_code_quality.py
    ├── test_duplicate_code.py
    ├── test_exception_handling.py
    ├── test_resource_cleanup.py
    ├── test_serial_error_handling.py
    └── test_undefined_variables.py
```

**Total New Tests Needed**: ~87 unit tests + 10-15 integration tests
**Estimated Effort**: 40-60 hours for comprehensive test suite
