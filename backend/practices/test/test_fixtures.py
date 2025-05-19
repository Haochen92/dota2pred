import pytest
from .test_assertions import add_num

@pytest.mark.asyncio
async def test_async_add_with_fixtures(default_numbers):
    num1, num2 = default_numbers
    
    result = await add_num(num1, num2)
    assert result == 30
    print("Running test_async_add")
    
    
