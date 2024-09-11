import logging

def get_logger(name):
    logger = logging.getLogger(name)
    
    # Set logger level to INFO to capture INFO and higher level logs
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if not logger.hasHandlers():
        # Set up handlers
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler('error.log')

        # Configure handlers
        console_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.ERROR)

        console_format = logging.Formatter('%(name)s - %(message)s')
        file_format = logging.Formatter('Time: %(asctime)s - File: %(filename)s - Name: %(name)s - Error Msg: %(message)s')

        console_handler.setFormatter(console_format)
        file_handler.setFormatter(file_format)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
    
    return logger

if __name__ == "__main__":
    get_logger(__name__)