import pytest
import logging
import requests
import subprocess
import time
import socket
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

# IMAGE TAG: TO SET IN CONFIG FILE
IMAGE_TAG = "match_prediction:latest"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def prediction_server_container():
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
            # Wait for the service to be ready before yielding.
            wait_for_logs(container, "Service match_prediction initialized", timeout=90)
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


@pytest.fixture(scope="function")
def bentoml_container_url():
    """
    Start BentoML container and yield the service URL
    """

    # Find an available port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    port = find_free_port()
    service_url = f"http://localhost:{port}"

    # Start the container
    container_process = subprocess.Popen(
        ["docker", "run", "--rm", "-p", f"{port}:3000", IMAGE_TAG], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    try:
        # Wait for the service to be ready
        service_ready = False
        for attempt in range(60):  # Wait up to 60 seconds
            try:
                response = requests.get(service_url, timeout=2)
                if response.status_code == 200:
                    service_ready = True
                    break
            except requests.RequestException:
                pass
            time.sleep(1)

        if not service_ready:
            # Get container logs for debugging
            stdout, stderr = container_process.communicate(timeout=5)
            logger.error(f"Container failed to start. STDOUT: {stdout.decode()}")
            logger.error(f"STDERR: {stderr.decode()}")
            raise Exception("BentoML service did not become ready in time")

        logger.info(f"BentoML container is ready at {service_url}")
        yield service_url

    finally:
        # Clean up: stop the container
        container_process.terminate()
        container_process.wait(timeout=10)
