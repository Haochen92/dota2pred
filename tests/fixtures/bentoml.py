import pytest
from dota_oracle_common.utils.set_logging import get_logger
from typing import Iterator
from testcontainers.core.container import DockerContainer

# IMAGE TAG: TO SET IN CONFIG FILE
IMAGE_TAG = "dota_prediction_service:latest"

logger = get_logger(__name__)


@pytest.fixture(scope="function")
def prediction_server_container() -> Iterator[str]:
    """
    Starts the BentoML prediction server using a DockerContainer
    for the duration of the test session.
    """

    # THE CORRECT CLASS NAME: DockerContainer
    # We instantiate it with the image tag.
    with DockerContainer(image=IMAGE_TAG) as container:
        # Use the builder pattern to configure it.
        container.with_exposed_ports(3000)

        try:
            # Wait for the service to be ready using health check instead of logs
            from testcontainers.core.waiting_utils import wait_for

            wait_for(lambda: container.exec("curl -f http://localhost:3000/readyz").exit_code == 0)
        except Exception as e:
            # On failure, dump logs for easy debugging in CI environments.
            logs = container.get_logs()
            logger.error(f"Container failed to start. STDOUT: {logs[0].decode()}")
            logger.error(f"STDERR: {logs[1].decode()}")
            raise e

        # Get the connection details for the running container.
        host = container.get_container_host_ip()
        port = container.get_exposed_port(3000)
        service_url = f"http://{host}:{port}"

        logger.info(f"BentoML container is ready and listening at {service_url}")

        # Yield the URL to the tests that need it.
        yield service_url

    # The 'with' statement ensures the container is automatically stopped and removed.
    logger.info("BentoML container has been stopped.")
