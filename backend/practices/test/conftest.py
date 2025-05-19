import pytest
from typing import Tuple, Generator

@pytest.fixture(scope='module')
def default_numbers():
    """A fixture that provides a tuple of memory"""
    print("Setting up default number fixtures...")
    return (10, 20)



@pytest.fixture(scope='package')
def setup_resource() -> Generator[Tuple[int, int], None, None]:
    '''A fixture which simulates setting up resource with tear down. Will only be run when requested'''
    print("setting up constants")
    
    yield (1,2)
    
    print("closing constants")
    
    
@pytest.fixture(scope='session', autouse=True)
def log_session() -> Generator[None, None, None]:
    '''Fixture which signals the start and end of test. Will run without being requested'''
    print("Signalling Session Start")
    yield
    print("Signalling Session End")
