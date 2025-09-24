RESOURCE_FILE_PATH = "resources"
CHAT_FILE_PATH = f"{RESOURCE_FILE_PATH}/chats.json"
CREDENTIALS_FILE_PATH = f"{RESOURCE_FILE_PATH}/credentials.json"
FORWARD_CONFIG_FILE_PATH = f"{RESOURCE_FILE_PATH}/forwardConfig.json"
HISTORY_FILE_PATH = f"{RESOURCE_FILE_PATH}/history.json"
IGNORE_CHATS_FILE_PATH = f"{RESOURCE_FILE_PATH}/ignoreChats.json"
WANTED_USER_FILE_PATH = f"{RESOURCE_FILE_PATH}/wantedUser.json"
FORWARD_PROGRESS_FILE_PATH = f"{RESOURCE_FILE_PATH}/forward_progress.json"

MEDIA_FOLDER_PATH = "media"

SESSION_FOLDER_PATH = "sessions"
SESSION_PREFIX_PATH = f"{SESSION_FOLDER_PATH}/session_"

# Forwarding configuration constants
DEFAULT_CHUNK_SIZE = 500  # Messages per chunk when retrieving from Telegram
DEFAULT_BATCH_SIZE = 50   # Messages to process before saving progress
DEFAULT_RATE_LIMIT_DELAY = 1.0  # Seconds between message sends
