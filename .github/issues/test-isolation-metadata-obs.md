# Test isolation issues with metadata and obs_script tests

## Problem Description

Some tests in `test_metadata.py` and `test_obs_script.py` fail when run as part of a larger test suite, but pass when run individually. The error is:

```
ImportError: module src.core.metadata not in sys.modules
```

## Affected Tests

- `test_metadata.py::TestSourceCapabilitiesDetection::*` (8 tests)
- `test_metadata.py::TestMetadataWithCapabilities::*` (2 tests)  
- `test_obs_script.py::TestOBSScript::*` (10 tests)

**Total: 20 failing tests**

## Current Behavior

✅ **Individual test run:**
```bash
uv run pytest tests/test_metadata.py -v
# ✅ All 23 tests pass

uv run pytest tests/test_obs_script.py -v  
# ✅ All 10 tests pass
```

❌ **Multi-test run:**
```bash
uv run pytest tests/test_metadata.py tests/test_obs_script.py
# ❌ 20 ImportError failures
```

## Root Cause

The issue appears to be related to `importlib.reload()` calls in `setup_method()` of both test files:

```python
def setup_method(self):
    """Reset module state before each test."""
    import src.core.metadata
    importlib.reload(src.core.metadata)  # ← This causes issues
```

When tests are run together, the module state gets corrupted and `src.core.metadata` is no longer in `sys.modules` for subsequent tests.

## Attempted Fixes

1. **Conditional reload** - check `sys.modules` before reload
2. **Safer import handling** - guard against missing modules  

Neither approach fully resolved the multi-test session issues.

## Impact

- **Core functionality works:** 141 tests pass, 8 skipped ✅
- **Critical features work:** CLI, extractor, audio analyzer, file reorganization ✅
- **Only edge case fails:** OBS integration tests in multi-test runs ❌

## Potential Solutions

1. **Remove `importlib.reload()`** - Tests work without it individually
2. **Use pytest fixtures** instead of `setup_method()` for module state
3. **Isolate test sessions** - Run metadata/obs tests separately
4. **Mock module imports** instead of reloading actual modules

## Priority

**Low** - This doesn't block development or core functionality. The affected tests are for OBS integration edge cases and work correctly when run in isolation.

## Test Command to Reproduce

```bash
# This works (141 passed, 8 skipped)
uv run pytest --ignore=tests/test_beat_switch_animator.py \
              --ignore=tests/test_blender_animation_engine.py \
              --ignore=tests/test_blender_project_setup.py \
              --ignore=tests/test_blender_vse_keyframe_helper.py \
              --ignore=tests/test_energy_pulse_animator.py \
              --ignore=tests/test_multi_pip_animator.py \
              --ignore=tests/test_blender_project.py \
              --ignore=tests/test_blender_vse_config.py \
              --ignore=tests/test_blender_vse_constants.py \
              --ignore=tests/test_blender_vse_layout_manager.py

# This shows the 20 ImportError failures
```

## Related Files

- `tests/test_metadata.py` (lines 19-23, 80-84, 160-164)
- `tests/test_obs_script.py` (lines 27-35)
- `src/core/metadata.py` - target module being reloaded