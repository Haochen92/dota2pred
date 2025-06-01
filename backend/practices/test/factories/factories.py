from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle.models.inference.schema import PerformanceMetrics

class PerformanceMetricsFactory(ModelFactory[PerformanceMetrics]):
    pass


if __name__ == '__main__':
    performance_metrics_instance = PerformanceMetricsFactory()
    instance1 = performance_metrics_instance.build()
    print(instance1)