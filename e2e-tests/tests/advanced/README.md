# Advanced Testing Modules

This directory contains advanced testing patterns that extend beyond basic unit and integration testing. These tests help ensure production reliability, performance, and consistency.

## Testing Modules

### 1. Contract Testing (`contract/`)
**Purpose**: Verify that external API mocks match real API responses.

```bash
# Run contract tests (requires real API calls)
pytest tests/advanced/contract/ -m contract

# Update API contracts
pytest tests/advanced/contract/ -m contract --update-contracts
```

**Key Tests**:
- `test_steam_live_games_response_structure()` - Validates Steam API response structure
- `test_mock_steam_response_matches_expected_structure()` - Ensures mocks match reality
- `test_contract_drift_detection()` - Detects when APIs change

### 2. Property-Based Testing (`property_based/`)
**Purpose**: Test with randomly generated inputs to find edge cases.

```bash
# Run property-based tests
pytest tests/advanced/property_based/ -m property

# Run with more examples for thorough testing
pytest tests/advanced/property_based/ --hypothesis-max-examples=100
```

**Key Tests**:
- `test_team_features_handle_any_valid_match_count()` - Tests with random match counts
- `test_hero_combinations_produce_valid_features()` - Tests with random hero combinations
- `test_match_outcome_invariants()` - Tests invariants that should always hold

**Dependencies**: `hypothesis` (install with `pip install hypothesis`)

### 3. Performance Testing (`performance/`)
**Purpose**: Test system performance under various load conditions.

```bash
# Run performance tests
pytest tests/advanced/performance/ -m performance

# Run with specific load patterns
pytest tests/advanced/performance/ -k "concurrent_matches"
```

**Key Tests**:
- `test_pipeline_handles_concurrent_matches()` - Tests concurrent processing
- `test_redis_stream_throughput()` - Tests Redis performance
- `test_database_connection_pool_limits()` - Tests DB connection limits

### 4. Chaos Engineering (`chaos/`)
**Purpose**: Test system resilience when components fail.

```bash
# Run chaos tests
pytest tests/advanced/chaos/ -m chaos

# Run specific failure scenarios
pytest tests/advanced/chaos/ -k "redis_failure"
```

**Key Tests**:
- `test_pipeline_survives_redis_connection_loss()` - Redis failure simulation
- `test_database_connection_pool_exhaustion()` - DB failure simulation
- `test_model_inference_timeout_handling()` - ML service failure simulation

### 5. Snapshot Testing (`snapshot/`)
**Purpose**: Ensure ML features remain consistent across code changes.

```bash
# Run snapshot tests
pytest tests/advanced/snapshot/ -m snapshot

# Update snapshots after intentional changes
UPDATE_SNAPSHOTS=true pytest tests/advanced/snapshot/ -m snapshot
```

**Key Tests**:
- `test_hero_features_snapshot()` - Validates hero feature consistency
- `test_team_features_snapshot()` - Validates team feature consistency
- `test_feature_array_structure_snapshot()` - Validates final feature arrays

### 6. Cross-Service Integration Testing (`cross_integration/`)
**Purpose**: Test complete match lifecycle workflow across all services.

```bash
# Run cross-integration tests
pytest tests/advanced/cross_integration/ -m integration_workflow

# Run specific workflow tests
pytest tests/advanced/cross_integration/ -k "complete_match_lifecycle"
```

**Key Tests**:
- `test_complete_match_lifecycle_workflow()` - **THE CROWN JEWEL** - Tests entire pipeline flow
- `test_data_consistency_across_services()` - Validates data integrity across services
- `test_service_communication_patterns()` - Tests producer-consumer patterns
- `test_partial_workflow_failure_recovery()` - Tests workflow resilience

## Running All Advanced Tests

```bash
# Run all advanced tests
pytest tests/advanced/ -v

# Run with specific markers
pytest tests/advanced/ -m "not chaos"  # Skip chaos tests

# Run in parallel (if you have pytest-xdist)
pytest tests/advanced/ -n auto
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Advanced Tests
  run: |
    pytest tests/advanced/contract/ -m contract --tb=short
    pytest tests/advanced/property_based/ --hypothesis-max-examples=50
    pytest tests/advanced/performance/ -m performance --tb=short
    pytest tests/advanced/chaos/ -m chaos --tb=short
    UPDATE_SNAPSHOTS=false pytest tests/advanced/snapshot/ -m snapshot
```

### Production Readiness Checklist
- [ ] Contract tests pass (APIs haven't changed)
- [ ] Property-based tests find no edge case failures
- [ ] Performance tests meet throughput requirements
- [ ] Chaos tests prove system resilience
- [ ] Snapshot tests confirm ML feature consistency
- [ ] **Cross-integration tests validate complete workflow** ⭐

## Test Dependencies

Add these to your `requirements.txt` or `pyproject.toml`:

```txt
# For property-based testing
hypothesis>=6.0.0

# For performance monitoring  
psutil>=5.8.0

# For chaos testing
redis>=4.0.0

# For snapshot testing (built-in with Python)
# No additional dependencies needed
```

## Learning Resources

1. **Contract Testing**: Learn about consumer-driven contracts and API evolution
2. **Property-Based Testing**: Explore QuickCheck-style testing with Hypothesis
3. **Performance Testing**: Study load testing patterns and bottleneck identification
4. **Chaos Engineering**: Research Netflix's Chaos Monkey and fault injection
5. **Snapshot Testing**: Understand golden master testing for regression prevention
6. **Cross-Integration Testing**: Study end-to-end workflow validation and service orchestration

## The Crown Jewel Test 👑

The **`test_complete_match_lifecycle_workflow()`** is the most important test in your entire suite. It validates:

1. **🔍 Discovery**: Matches are detected from external APIs
2. **⚙️ Feature Engineering**: Features are created and stored
3. **🤖 Prediction**: ML models generate predictions
4. **🏁 Completion**: Outcomes are tracked and accuracy measured

**This single test proves your entire Dota 2 prediction pipeline works end-to-end!**

These advanced testing patterns will significantly improve your system's reliability and help catch issues before they reach production! 🚀