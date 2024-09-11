from datetime import datetime as dt

def unix_to_datetime(unix_timestamp):
    """
    Convert unix timestamp used by Dota 2's client into readable
    datetime format. 

    Args:
        unix_timestamp (int): unix timestamp in seconds 

    Returns:
        dt.datetime: returns dt.datetime object after conversion
    """    
    return dt.fromtimestamp(unix_timestamp)