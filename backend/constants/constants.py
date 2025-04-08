import yaml
import os
from src.config import ROOT_DIR

CONSTANTS_PATH = os.path.join(ROOT_DIR, 'constants', 'constants.yml')

try:
    with open(CONSTANTS_PATH, 'r') as file:
        _ALL_CONSTANTS = yaml.safe_load(file) or {}
except FileNotFoundError:
    raise FileNotFoundError(f"Constants file does not exist at {CONSTANTS_PATH}")

HERO_DICT = _ALL_CONSTANTS.get('HEROES_CONSTANTS', {})
if not HERO_DICT or not isinstance(HERO_DICT, dict):
    raise ValueError("Hero constants are not in a valid format or are empty")