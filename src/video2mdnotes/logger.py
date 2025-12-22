import sys
from loguru import logger

# Remove the default handler
logger.remove()

# Add a new handler that logs to stderr
# This is standard practice for CLI applications
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# You can also add a file logger for persistent logs
# logger.add(
#     "logs/app.log",
#     level="DEBUG",
#     rotation="10 MB",
#     retention="10 days",
#     format="{time} {level} {message}",
# )

# The logger is now configured and can be imported from this module
# e.g., from video2mdnotes.logger import logger
