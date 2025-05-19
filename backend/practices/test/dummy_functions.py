from .test_assertions import add_num
from src.data_repository.features_repository import FeaturesRepository
from src.data_repository.schemas.features import HeroFeaturesTable

async def multiply(a, b, c):
    product = await add_num(a, b) * c
    return product


async def function_with_object_call(features_repo: FeaturesRepository, hero_class: HeroFeaturesTable):
    data = await features_repo.get_feature_by_id(123, hero_class)
    
    return f"created {data} successfully!"