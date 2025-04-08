import json
from sqlmodel import Session, select
from collections import deque
from database.schemas.team_histories import TeamHistories, TeamMatchupHistories
from database.schemas.features import TeamFeatures

class TeamFeatureProcessor:
    def __init__(self, redis_client= None, db_client=None, max_history_length=10):
        self.redis = redis_client
        self.db = db_client
        self.max_history_length = max_history_length
        self.max_matchups = 1000
        
        # if not using redis
        self.team_histories = {}
        self.matchup_histories = {}
        
    def calculate_win_rate(self, team_name: str) -> float:
        if self.redis:
            team_histories = self.get_team_history(team_name)
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

    def get_team_history(self, team_name: str):
        
        try:
            cache_key = f"history:team:{team_name}"
            matches = self.redis.lrange(cache_key, 0, -1)
            
            if matches:
                # Set expiration (fixing the missing argument)
                self.redis.expire(cache_key, 86400 * 30)
                return [json.loads(match) for match in matches]
            
            elif self.db:
                history = self.fetch_team_history_from_db(team_name)
                # populate Redis
                if history:
                    pipeline = self.redis.pipeline()
                    for match in history:
                        pipeline.lpush(cache_key, json.dumps(match))
                    pipeline.execute()
                    
                    return history
        except Exception as e:
            print(f"Redis error: {e}")
            
        return []
            
    def fetch_team_history_from_db(self, team_name) -> list:
        with Session(self.db) as session:
            stmt = select(TeamHistories).where(
                TeamHistories.team_name == team_name
            )
            
            results = session.exec(stmt)
            if not results:
                return []
            
            matches = results.matches
            sorted_matches = sorted(
                matches,
                key=lambda match: match['match_date'],
                reverse=True
            )
            
            return sorted_matches[:self.max_history_length]
        
    def update_team_history(self, team_name: str, match):
        if self.redis:
            cache_key = f"history:team:{team_name}"
            pipeline = self.redis.pipeline()
            # Add current match and trim off earliest match
            pipeline.lpush(cache_key, json.dumps(match))
            pipeline.ltrim(cache_key, 0, self.max_history_length - 1)
            pipeline.execute()
        else:
            if team_name not in self.team_histories:
                self.team_histories[team_name] = deque(maxlen=self.max_history_length)
            self.team_histories[team_name].append(match)
        
    def calculate_matchup(self, team_name: str, opponent_name: str) -> float:
        team_ids = sorted([team_name, opponent_name])
        
        if self.redis:
            all_matches = self.get_matchup_history(team_ids[0], team_ids[1])
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
    
    def get_matchup_history(self, team1, team2):
        try:
            cache_key = f"history:matchup:{team1}:{team2}"
            
            # check redis and fetch all the matches
            matches = self.redis.lrange(cache_key, 0, -1)
            if matches:
                self.redis.expire(cache_key, 86400 * 30)
                return [json.loads(match) for match in matches]
            
            elif self.db:
                history = self.fetch_matchup_from_db(team1, team2)
                
                # populate Redis
                if history:
                    pipeline = self.redis.pipeline()
                    for match in history:
                        pipeline.lpush(cache_key, json.dumps(match))
                    pipeline.expire(cache_key, 86400 * 30)
                    pipeline.execute()
                    
                    return history
        except Exception as e:
            print(f"Redis error: {e}")
        
        return []
    
    def update_matchup_history(self, team1: str, team2: str, match):
        team_ids = sorted([team1, team2])
        if self.redis:
            cache_key = f"history:matchup:{team_ids[0]}:{team_ids[1]}"
            
            pipeline = self.redis.pipeline()
            
            # Add current match and trim off earliest match
            pipeline.lpush(cache_key, json.dumps(match))
            pipeline.ltrim(cache_key, 0, self.max_history_length - 1)
            pipeline.execute()
        else:
            if (team_ids[0], team_ids[1]) not in self.matchup_histories:
                self.matchup_histories[(team_ids[0], team_ids[1])] = deque(maxlen=self.max_history_length)
            self.matchup_histories[(team_ids[0], team_ids[1])].append(match)

    def fetch_matchup_from_db(self, team1: str, team2: str) -> list:
        with Session(self.db) as session:
            stmt = select(TeamMatchupHistories).where(
                (TeamMatchupHistories.team1_name == team1) &
                (TeamMatchupHistories.team2_name == team2)
            )
            
            results = session.exec(stmt)
            if not results:
                return []
            
            matches = results.matches
            sorted_matches = sorted(
                matches,
                key=lambda match: match['match_date'],
                reverse=True
            )
            
            return sorted_matches[:self.max_history_length]
            

    def create_team_features(self, df):
        
        team_level_features = []

        for _, match in df.iterrows():
            radiant_team = match['radiant_name']
            dire_team = match['dire_name']
            
            # Calculate features for each row
            radiant_win_rate = self.calculate_win_rate(radiant_team)
            dire_win_rate = self.calculate_win_rate(dire_team)
            matchup_rate = self.calculate_matchup(radiant_team, dire_team)
            
            # append features to results
            team_level_features.append({
                'match_id': match['match_id'],
                'radiant_win_rate': radiant_win_rate,
                'dire_win_rate': dire_win_rate,
                'radiant_dire_matchup': matchup_rate
            })
            
            # update history dictionaries
            self.update_team_history(radiant_team, match)
            self.update_team_history(dire_team, match)
            self.update_matchup_history(radiant_team, dire_team, match)
            
        return team_level_features

    def store_to_db(self, features):
        model_fields = {
            name for name, field in TeamFeatures.__fields__.items()
            if not name.startswith('_')
        }
        
        with Session(self.db) as session:
            for row in features:
                # Filter data to match model fields
                filtered_data = {
                    field: row[field]
                    for field in model_fields
                    if field in row
                }
                
                # Create the model instance with the filtered data
                team_features = TeamFeatures(**filtered_data)
                session.merge(team_features)
        
            session.commit()
            
    def create_and_store_team_features(self, df):
        features = self.create_team_features(df)
        self.store_to_db(features)