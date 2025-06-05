from .api_clients.opendota_api import fetch_opendota
from dota_oracle.models.match import ProMatchAPIResponse, ProMatchOutcome
from dota_oracle.utils.set_logging import get_logger
from typing import List
from pydantic import ValidationError
import aiohttp

logger = get_logger(__name__)

async def fetch_pro_match(max_match_id: int, min_max_id: int) -> List[ProMatchOutcome]:
    output_list = []
    
    while max_match_id >= min_max_id:
        try:
            res = await fetch_opendota(
                endpoint="/proMatches",
                params={"less_than_match_id": max_match_id}
            )
            
            api_response = ProMatchAPIResponse.model_validate(res)
            list_instances = api_response.root
            
            list_match_ids = [instance.match_id for instance in list_instances]
            min_max_id = min(list_match_ids)
            
            output_list.append(*list_instances)
            
        except (
            aiohttp.ClientConnectionError, 
            aiohttp.ClientError, 
            aiohttp.http.HttpProcessingError, 
            ValueError, 
            ValidationError
        ) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message, exc_info=True)
            raise 
        except Exception as e:
            logger.error(f"Exception while fetching promatches, {e}", exc_info=True)
            raise
        
    return output_list 
