import asyncio
import pytest

async def add_num(a, b):
    await asyncio.sleep(2)
    if not (isinstance(a, int) and isinstance(b, int)):
        raise TypeError("Both arguments must be numbers haha")
    return a + b

    
@pytest.mark.asyncio
async def test_async_add_num():
    result = await add_num(3, 4)
    assert result == 7


@pytest.mark.asyncio
async def test_async_add_raises_type_error_for_invalid_input():
    with pytest.raises(TypeError, match="Both arguments must be numbers"):
        await add_num("a", 3)
        
        
@pytest.mark.asyncio
async def test_async_add_with_session(setup_resource):
    a, b = setup_resource
    result = await add_num(a, b)
    
    assert result == 3
    
    
