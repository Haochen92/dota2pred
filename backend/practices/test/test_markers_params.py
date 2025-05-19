import sys
import pytest 
from .test_assertions import add_num

@pytest.mark.skipif(sys.version_info < (3, 11), reason='requires python 3.11 or higher')
def test_task_group():
    assert sys.version_info >= (3, 11)
    

# parameters

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "a, b, expected",
    [(1,2,3), (2,3,4), (3,4,7)]
)
async def test_async_addition_with_params(a, b, expected):
    assert await add_num(a, b) == expected