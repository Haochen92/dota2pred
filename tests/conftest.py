pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.redis",
    "tests.fixtures.repositories",
    "tests.fixtures.bentoml",
    "tests.fixtures.pipeline_services",
    "tests.fixtures.data_providers",
    "tests.fixtures.event_processors",
    "tests.fixtures.orchestrators",
    "tests.fixtures.feature_engineering",
    "tests.factories.repository_factories",
    "tests.factories.unit_test_factory",
    "tests.factories.redis_models_factory",
]
