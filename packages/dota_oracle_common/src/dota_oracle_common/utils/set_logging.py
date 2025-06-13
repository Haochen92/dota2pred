import logging
from dota_oracle_common.config import ROOT_DIR
import pytz
from datetime import datetime

'''
    Todos:
    1. Rename file to logger.py and update all imports
    2. Rename function to configure_logger and update all imports
    3. Implement RotatingFileHandler
'''
def get_logger(name):
 
    # output_fpath = ROOT_DIR / 'logs' / f'{name}_error.log'
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if not logger.hasHandlers():
        # Set up handlers
        console_handler = logging.StreamHandler()
        # file_handler = logging.FileHandler(output_fpath)

        # Configure handlers
        console_handler.setLevel(logging.INFO)
        # file_handler.setLevel(logging.ERROR)

        console_format = logging.Formatter('%(name)s - %(message)s')
        # file_format = logging.Formatter('Time: %(asctime)s - File: %(filename)s - Name: %(name)s - Error Msg: %(message)s')
        # file_format.converter = lambda *args: datetime.now(pytz.timezone('Asia/Shanghai')).timetuple()

        console_handler.setFormatter(console_format)
        # file_handler.setFormatter(file_format)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        # logger.addHandler(file_handler)
    else:
        logger.info(f"Handlers already set up {logger.handlers}")
    
    return logger

if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("testing console log")
    logger.error("testing error log")
    