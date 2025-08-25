"""
Unit tests for the Matches Router.
"""

from dota_oracle_common.models.pagination import PaginatedMatchResponse


def test_get_matches_success(api_layer_client):
    """Test successful retrieval of matches."""
    # ACT
    response = api_layer_client.get("/matches/")

    # ASSERT
    assert response.status_code == 200
    # The unit_test_match_pagination_service is already mocked in the fixture
    # so this will return the mock's default response


def test_get_matches_with_query_parameters(api_layer_client):
    """Test matches endpoint with query parameters."""
    # ACT
    response = api_layer_client.get("/matches/?page=2&page_size=10&team_name=Secret&hero_names[]=Anti-Mage")

    # ASSERT
    assert response.status_code == 200
    # Query parameters are parsed by FastAPI and passed to the service


def test_get_matches_with_mock_response(api_layer_client, mock_match_pagination_service):
    """Test matches endpoint with specific mock response."""
    # ARRANGE
    mock_response = PaginatedMatchResponse(
        matches=[], total_count=100, page=1, page_size=20, total_pages=5, has_next=True, has_previous=False
    )
    mock_match_pagination_service.get_paginated_matches.return_value = mock_response

    # ACT
    response = api_layer_client.get("/matches/")

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 100
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 5
    assert data["has_next"] is True
    assert data["has_previous"] is False


def test_get_matches_service_error(api_layer_client, mock_match_pagination_service):
    """Test handling of pagination service errors."""
    # ARRANGE
    mock_match_pagination_service.get_paginated_matches.side_effect = Exception("Database error")

    # ACT & ASSERT
    response = api_layer_client.get("/matches/")
    assert response.status_code == 500


def test_matches_router_configuration(matches_router):
    """Test router configuration."""
    assert matches_router.prefix == "/matches"
    assert "matches" in matches_router.tags

    # Check that the route exists
    routes = [route.path for route in matches_router.routes]
    assert "/matches/" in routes
