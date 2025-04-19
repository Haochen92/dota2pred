from sqlmodel import Session, select
import pandas as pd
from database.schemas.features import PlayerHeroFeature
from database.schemas.histories import PlayerHeroHistories
from collections import deque

# create a cron job for syncing from redis to postgresql database

class PlayerHeroFeatures:
    def __init__(self, redis_client= None, db_client=None, max_history_length=20):
        self.redis = redis_client
        self.db = db_client
        self.max_history_length = max_history_length
        self.max_matchups = 1000
        self.cache_expiry = 86400 * 30
        
        # if not using redis
        self.player_hero_histories = {}
        
    def create_player_hero_features(self, df):
        
        features = []
        
        for _, match in df.iterrows():
            match_id = match['match_id']
            match_result = {}
            match_result['match_id'] = match_id
            
            radiant_num = range(0, 5)
            dire_num = range(128, 133)
            radiant_win = match['radiant_win']
            
            for i in radiant_num:
                account_id = match[f'{i}_account_id']
                hero_id = match[f'{i}_hero_id']
                # Calculate win rate based on previous matches
                win_rate = self.calculate_win_rate(account_id, hero_id)
                # Add win rate to results for this match
                match_result[f'player_hero_{i}_win_rate'] = win_rate
                # Update history after calculating
                self.update_player_hero_histories(account_id, hero_id, radiant_win)
            
            for j in dire_num:
                account_id = match[f'{j}_account_id']
                hero_id = match[f'{j}_hero_id']
                dire_win = not radiant_win
                win_rate = self.calculate_win_rate(account_id, hero_id)
                match_result[f'player_hero_{j}_win_rate'] = win_rate
                self.update_player_hero_histories(account_id, hero_id, dire_win)
            
            # Append complete match result with all player win rates
            features.append(match_result)

        return features

    def calculate_win_rate(self, account_id, hero_name):
        history = self.get_player_hero_history(account_id, hero_name)
        if not history:
            return 0.5
        
        return sum(history) / len(history)
    
    def get_player_hero_history(self, account_id, hero_name):
        if self.redis:
            cache_key = f'histories:player_hero:{account_id}:{hero_name}'
            try:
                history = self.redis.lrange(cache_key, 0, -1)
                if history:
                    self.redis.expire(cache_key, self.cache_expiry)
                    return [int(x) for x in history] 
                
                elif self.db:
                    history = self.fetch_history_from_db(account_id, hero_name)
                    if history:
                        pipeline = self.redis.pipeline()
                        pipeline.rpush(cache_key, *[int(val) for val in history])
                        pipeline.expire(cache_key, self.cache_expiry)
                        pipeline.execute()
                        return history
            except Exception as e:
                print(f"Redis error: {e}")
                
        return self.player_hero_histories.get((account_id, hero_name), [])
    
    def fetch_history_from_db(self, account_id, hero_name):
        table = PlayerHeroHistories
        try:
            with Session(self.db) as session:
                stmt = select(table).where(
                    (table.account_id == account_id) &
                    (table.hero_name == hero_name)
                )
                results = session.exec(stmt)
                results_list = results.all()
                if not results_list:
                    return []
                
                matches = results.matches
                return matches
        except Exception as e:
            print(f'Unable to read database: {e}')
            raise(e)
            
    
    def update_player_hero_histories(self, account_id, hero_name, win: bool):
        if self.redis:
            cache_key = f'histories:player_hero:{account_id}:{hero_name}'
            pipeline = self.redis.pipeline()
            pipeline.rpush(cache_key, int(win))
            pipeline.ltrim(cache_key, -self.max_history_length, - 1)
            pipeline.expire(cache_key, self.cache_expiry)
            pipeline.execute()
        else:
            
            key = (account_id, hero_name)
            if (account_id, hero_name) not in self.player_hero_histories:
                self.player_hero_histories[key] = deque(maxlen=self.max_history_length)
            
            self.player_hero_histories[key].append(win)
                
    
    def store_to_db(self, player_hero_features):
        
        with Session(self.db) as session:
            # For each match record
            for match in player_hero_features:
                # Create a new PlayerHeroFeature instance
                player_hero_feature_obj = PlayerHeroFeature(
                    match_id=match["match_id"],
                    player_hero_0_win_rate=match["player_hero_0_win_rate"],
                    player_hero_1_win_rate=match["player_hero_1_win_rate"],
                    player_hero_2_win_rate=match["player_hero_2_win_rate"], 
                    player_hero_3_win_rate=match["player_hero_3_win_rate"],
                    player_hero_4_win_rate=match["player_hero_4_win_rate"],
                    player_hero_128_win_rate=match["player_hero_128_win_rate"],
                    player_hero_129_win_rate=match["player_hero_129_win_rate"],
                    player_hero_130_win_rate=match["player_hero_130_win_rate"],
                    player_hero_131_win_rate=match["player_hero_131_win_rate"],
                    player_hero_132_win_rate=match["player_hero_132_win_rate"]
                )
                
                # Use merge instead of add
                session.merge(player_hero_feature_obj)
            
            # Commit all records at once
            try:
                session.commit()
                print(f"Successfully stored {len(player_hero_features)} player-hero feature records")
            except Exception as e:
                session.rollback()
                print(f"Error storing player-hero features: {str(e)}")

        
    def create_and_store_player_hero_features(self, df):
        features = self.create_player_hero_features(df)
        self.store_to_db(features)
        return pd.DataFrame(features)
        
    def clear_history_cache(self):
        if self.redis:
            try:
                pattern = "histories:player_hero:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    print(f"Cleared {len(keys)} player hero histories from redis")
            except Exception as e:
                print(f"Error clearing redis key: {e}")