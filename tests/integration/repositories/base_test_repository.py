from dota_oracle_common.repositories.base_repository import BaseRepository
from dota_oracle_common.utils import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from typing import List, TypeVar


T = TypeVar("T", bound=SQLModel)

logger = get_logger(__name__)


class BaseTestRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
            
    def _assert_equal(
        self, 
        expected_instance: T, 
        actual_instance: T, 
        test_scenario: str,
    ):
        
        field_names = self._get_relevant_field_names(expected_instance)
        
        for name in field_names:
            
            expected_value = getattr(expected_instance, name)
            actual_value = getattr(actual_instance, name)
        
            assert actual_value == expected_value, (
                f"Test {test_scenario}: "
                f"Field '{name}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
            
    def _assert_count_equal(self, actual_count: int, expected_count: int, test_scenario: str):
        assert actual_count == expected_count, \
            f"Test {test_scenario}: expected {actual_count} results, got {expected_count}"
        
    def _get_relevant_field_names(self, instance) -> List[str]:
        cls = instance.__class__
        
        # Retrieve all class columns, without relationships
        return [col.name for col in cls.__table__.columns]
    
    