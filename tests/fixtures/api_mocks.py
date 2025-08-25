import pytest
from httpx import Response
import respx
from dota_oracle_common.constants.endpoint_configs import service_url


@pytest.fixture
def mock_prediction_service_api(respx_mock: respx.MockRouter) -> None:
    """
    Mocks all endpoints for the external Prediction Service API.
    Provides a default "happy path" implementation.
    """
    respx_mock.post(service_url.PUBLIC_MATCHES_INFERENCE_URL, name="predict").mock(
        return_value=Response(200, json={"prediction": "mocked_success"})
    )
