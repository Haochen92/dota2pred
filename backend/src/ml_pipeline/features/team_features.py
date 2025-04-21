import json
import redis
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from collections import deque
from database.schemas.histories import TeamHistories, TeamMatchupHistories
from database.schemas.features import TeamFeatures
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Deque


class TeamFeatureProcessor:
    def __init__(
        self, 
        redis_client: redis.Redis = None, 
        db_client: Optional[AsyncEngine] = None, 
        max_history_length: int = 10
    ):
        self.redis = redis_client
        self.db = db_client
        self.max_history_length = max_history_length
        self.max_matchups = 1000
        self.cache_expiry = 86400 * 30
        
        # if not using redis
        self.team_histories: Dict[str, Deque[Dict[str, Any]]] = {}
        self.matchup_histories: Dict[Tuple[str, str], Deque[Dict[str, Any]]] = {}
        
    async def calculate_win_rate(self, team_name: str) -> float:
        if self.redis:
            team_histories = await self.get_team_history(team_name)
        else:
            team_histories = self.team_histories.get(team_name, [])
        
        if not team_histories:
            return 0.5
        
        win = 0
        for match in team_histories:
            if match['radiant_name'] == team_name and match['radiant_win']:
                win += 1
            elif match['dire_name'] == team_name and not match['radiant_win']:
                win += 1
            
        return win / len(team_histories)

    async def get_team_history(self, team_name: str) -> List[Dict[str, Any]]:
        try:
            cache_key = f"history:team:{team_name}"
            if self.redis:
                matches = self.redis.lrange(cache_key, 0, -1)
                
                if matches:
                    self.redis.expire(cache_key, self.cache_expiry)
                    return [json.loads(match) for match in matches]
                
                elif self.db:
                    history = await self.fetch_team_history_from_db(team_name)
                    # populate Redis
                    if history:
                        pipeline = self.redis.pipeline()
                        for match in history:
                            pipeline.rpush(cache_key, json.dumps(match))
                        pipeline.expire(cache_key, self.cache_expiry)
                        pipeline.execute()
                        
                        return history
            
            return []
        except Exception as e:
            print(f"Redis error at get_team_history: {e}")
            return []
            
            
    async def fetch_team_history_from_db(self, team_name: str) -> List[Dict[str, Any]]:
        if not self.db:
            return []
            
        async with AsyncSession(self.db) as session:
            stmt = select(TeamHistories).where(
                TeamHistories.team_name == team_name
            )
            
            result = await session.execute(stmt)
            results = result.scalars().first()
            if not results:
                return []
            matches = results.matches
            return matches
        
    async def update_team_history(self, team_name: str, match: Dict[str, Any]) -> None:
        if self.redis:
            cache_key = f"history:team:{team_name}"
            pipeline = self.redis.pipeline()
            # Add current match and trim off earliest match
            pipeline.rpush(cache_key, json.dumps(match))
            # Start counting from right till the max_length, ends at last index. 
            pipeline.ltrim(cache_key, -self.max_history_length, -1)
            pipeline.expire(cache_key, self.cache_expiry)
            pipeline.execute()
        else:
            if team_name not in self.team_histories:
                self.team_histories[team_name] = deque(maxlen=self.max_history_length)
            self.team_histories[team_name].append(match)
        
    async def calculate_matchup(self, team_name: str, opponent_name: str) -> float:
        team_ids = sorted([team_name, opponent_name])
        
        if self.redis:
            all_matches = await self.get_matchup_history(team_ids[0], team_ids[1])
        else:
            all_matches = self.matchup_histories.get((team_ids[0], team_ids[1]), [])
        
        if not all_matches:
            return 0.5
        
        win = 0
        for match in all_matches:
            if match['radiant_name'] == team_name and match['radiant_win']:
                win += 1
            elif match['dire_name'] == team_name and not match['radiant_win']:
                win += 1
        
        return win / len(all_matches)
    
    async def get_matchup_history(self, team1: str, team2: str) -> List[Dict[str, Any]]:
        try:
            cache_key = f"history:matchup:{team1}:{team2}"
            
            if self.redis:
                # check redis and fetch all the matches
                matches = self.redis.lrange(cache_key, 0, -1)
                if matches:
                    self.redis.expire(cache_key, self.cache_expiry)
                    return [json.loads(match) for match in matches]
                
                elif self.db:
                    history = await self.fetch_matchup_from_db(team1, team2)
                    
                    # populate Redis
                    if history:
                        pipeline = self.redis.pipeline()
                        for match in history:
                            pipeline.rpush(cache_key, json.dumps(match))
                        pipeline.expire(cache_key, self.cache_expiry)
                        pipeline.execute()
                        
                        return history
        except Exception as e:
            print(f"Redis error: {e}")
        
        return []
    
    async def update_matchup_history(self, team1: str, team2: str, match: Dict[str, Any]) -> None:
        team_ids = sorted([team1, team2])
        if self.redis:
            cache_key = f"history:matchup:{team_ids[0]}:{team_ids[1]}"
            
            pipeline = self.redis.pipeline()
            
            # Add current match and trim off earliest match
            pipeline.rpush(cache_key, json.dumps(match))
            pipeline.ltrim(cache_key, -self.max_history_length, - 1)
            pipeline.expire(cache_key, self.cache_expiry)
            pipeline.execute()
        else:
            if (team_ids[0], team_ids[1]) not in self.matchup_histories:
                self.matchup_histories[(team_ids[0], team_ids[1])] = deque(maxlen=self.max_history_length)
            self.matchup_histories[(team_ids[0], team_ids[1])].append(match)

    async def fetch_matchup_from_db(self, team1: str, team2: str) -> List[Dict[str, Any]]:
        if not self.db:
            return []
            
        async with AsyncSession(self.db) as session:
            stmt = select(TeamMatchupHistories).where(
                (TeamMatchupHistories.team1_name == team1) &
                (TeamMatchupHistories.team2_name == team2)
            )
            
            result = await session.execute(stmt)
            results = result.scalars().first()
            if not results:
                return []
            
            matches = results.matches
            
            return matches
            
    async def create_team_features(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        team_level_features = []
        match_records = df.to_dict('records')
        
        for match in match_records:
            for key, value in match.items():
                if isinstance(value, pd.Timestamp):
                    match[key] = value.isoformat()
            radiant_team = match['radiant_name']
            dire_team = match['dire_name']
            
            # Calculate features for each row
            radiant_win_rate = await self.calculate_win_rate(radiant_team)
            dire_win_rate = await self.calculate_win_rate(dire_team)
            matchup_rate = await self.calculate_matchup(radiant_team, dire_team)
            
            # append features to results
            team_level_features.append({
                'match_id': match['match_id'],
                'radiant_win_rate': radiant_win_rate,
                'dire_win_rate': dire_win_rate,
                'radiant_dire_matchup': matchup_rate
            })
            
            # update history dictionaries
            await self.update_team_history(radiant_team, match)
            await self.update_team_history(dire_team, match)
            await self.update_matchup_history(radiant_team, dire_team, match)
            
        return team_level_features

    async def store_to_db(self, features: List[Dict[str, Any]]) -> None:
        if not self.db:
            print("No database connection available")
            return
            
        try:
            async with AsyncSession(self.db) as session:
                for row in features:
                    # Check if the record already exists
                    stmt = select(TeamFeatures).where(TeamFeatures.match_id == row['match_id'])
                    result = await session.execute(stmt)
                    existing = result.scalars().first()
                    
                    if existing:
                        # Update existing record
                        existing.radiant_win_rate = row['radiant_win_rate']
                        existing.dire_win_rate = row['dire_win_rate']
                        existing.radiant_dire_matchup = row['radiant_dire_matchup']
                        session.add(existing)
                    else:
                        # Create new record
                        team_features = TeamFeatures(
                            match_id=row['match_id'],
                            radiant_win_rate=row['radiant_win_rate'],
                            dire_win_rate=row['dire_win_rate'],
                            radiant_dire_matchup=row['radiant_dire_matchup']
                        )
                        session.add(team_features)
            
                try:
                    await session.commit()
                    print(f"Successfully stored {len(features)} team feature records")
                except Exception as e:
                    await session.rollback()
                    print(f"Error storing team features: {str(e)}")
                    
        except Exception as e:
            print(f"Database session error: {e}")
    
    async def clear_history_cache(self) -> None:
        """Clear all history-related keys from Redis cache"""
        if self.redis:
            try:
                # Clear team history keys
                team_pattern = "history:team:*"
                team_keys = self.redis.keys(team_pattern)
                if team_keys:
                    self.redis.delete(*team_keys)
                    print(f"Cleared {len(team_keys)} team history keys from Redis")
                
                # Clear matchup history keys
                matchup_pattern = "history:matchup:*"
                matchup_keys = self.redis.keys(matchup_pattern)
                if matchup_keys:
                    self.redis.delete(*matchup_keys)
                    print(f"Cleared {len(matchup_keys)} matchup history keys from Redis")
                    
                total_cleared = len(team_keys) + len(matchup_keys)
                if total_cleared == 0:
                    print("No history keys found in Redis")
                else:
                    print(f"Total keys cleared: {total_cleared}")
            except Exception as e:
                print(f"Error clearing Redis cache: {e}")
                
    async def create_and_store_team_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = await self.create_team_features(df)
        await self.store_to_db(features)
        return pd.DataFrame(features)