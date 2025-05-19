import pytest
from pytest_mock import mocker

@pytest.mark.asyncio
async def test_my_function_which_uses_an_api(mocker):
    mock_api_call = mocker.patch('practices.test.dummy_functions.add_num') # requires absolute import from a module
    expected_api_response = 4
    
    mock_api_call.return_value = expected_api_response
    
    from practices.test.dummy_functions import multiply
    
    result = await multiply(1,2,3)
    
    assert result == 12
    
    mock_api_call.assert_called_once()
    mock_api_call.assert_called_once_with(1, 2)

@pytest.mark.asyncio
async def test_mock_with_autospec(mocker):
    from practices.test.dummy_functions import FeaturesRepository, HeroFeaturesTable, function_with_object_call
    mock_repo_argument = mocker.MagicMock(spec=FeaturesRepository)
    mock_repo_argument.get_feature_by_id.return_value = 150
    
    mock_second_arg = mocker.MagicMock(spec=HeroFeaturesTable)
    
    result = await function_with_object_call(mock_repo_argument, mock_second_arg)
    assert result == "created 150 successfully!"
    
