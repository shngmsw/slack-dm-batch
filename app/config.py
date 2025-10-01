import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Application settings
    APP_NAME: str = "Slack DM Batch Sender"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Slack API settings
    SLACK_TOKEN: Optional[str] = os.getenv("SLACK_TOKEN")
    SLACK_RATE_LIMIT_DELAY: float = float(os.getenv("SLACK_RATE_LIMIT_DELAY", "1.0"))  # seconds
    SLACK_MAX_RETRIES: int = int(os.getenv("SLACK_MAX_RETRIES", "3"))
    
    # File upload settings
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    UPLOAD_FOLDER: str = "static/uploads"
    ALLOWED_EXTENSIONS: set = {".csv", ".json", ".txt"}
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    SEND_RESULTS_LOG_FILE: str = os.getenv("SEND_RESULTS_LOG_FILE", "logs/send_results.log")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    @classmethod
    def get_log_config(cls) -> dict:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "level": cls.LOG_LEVEL,
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "file": {
                    "level": cls.LOG_LEVEL,
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": cls.LOG_FILE,
                    "formatter": "detailed",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                },
                "send_results": {
                    "level": "INFO",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": cls.SEND_RESULTS_LOG_FILE,
                    "formatter": "detailed",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 10,
                },
            },
            "loggers": {
                "": {  # root logger
                    "level": cls.LOG_LEVEL,
                    "handlers": ["console", "file"],
                },
                "send_results": {
                    "level": "INFO",
                    "handlers": ["send_results"],
                    "propagate": False,
                },
            },
        }

settings = Settings()