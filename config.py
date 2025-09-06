import os
import logging
from logging.handlers import RotatingFileHandler

# Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

# Your API ID & API HASH from my.telegram.org
APP_ID = int(os.environ.get("APP_ID", "21"))
API_HASH = os.environ.get("API_HASH", "c877fc81e")

# Your db channel Id
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1565"))

# OWNER ID
OWNER_ID = int(os.environ.get("OWNER_ID", "6695586027"))

# Port
PORT = os.environ.get("PORT", "8585")

# Database 
DB_URI = os.environ.get(
    "DATABASE_URL",
    "mongodb+srv://ultroidxTeam:ultroidxTeam@cluster0.gabxs6m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = os.environ.get("DATABASE_NAME", "Cluster0")

# Auto delete
DELETE_AFTER = int(os.environ.get("DELETE_AFTER", 60))  # seconds
NOTIFICATION_TIME = int(os.environ.get('NOTIFICATION_TIME', 60))  # seconds
AUTO_DELETE = os.environ.get("AUTO_DELETE", "True").lower() in ["true", "1", "yes", "on"]
GET_AGAIN = os.environ.get("GET_AGAIN", "False").lower() in ["true", "1", "yes", "on"]

DELETE_INFORM = os.environ.get("INFORM", "<blockquote> U want direct sex video all type\n\nmom son,bro sis,oyo,desi,rp naughty only,teleugu,mallu,tamil,she male,lesibean\n\nall direct file no link msg me to but vip memeber ship  @Myhero2k</blockquote>")
NOTIFICATION = os.environ.get(
    "NOTIFICATION",
    "File will delete after {DELETE_AFTER} seconds."
).format(DELETE_AFTER=DELETE_AFTER)
GET_INFORM = os.environ.get(
    "GET_INFORM",
    "File was deleted after {DELETE_AFTER} seconds. Use the button below to GET FILE AGAIN."
).format(DELETE_AFTER=DELETE_AFTER)

# Owner & support
BAN = int(os.environ.get("BAN", "1198543450"))
OWNER = os.environ.get("OWNER", "JNK_BACKUP")
OWNER_ID = int(os.environ.get("OWNER_ID", "6415368038"))
OWNER_USERNAME = os.environ.get('OWNER_USERNAME', 'JNK_BACKUP')
SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "JNK_BACKUP")
CHANNEL = os.environ.get("CHANNEL", "JNK_BACKUP")

# Shortener (token system)
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "arolinks.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "dc64f71dee43e715379e1da5d3bc9dbeb96b71a7")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 86400))
IS_VERIFY_ENV = os.environ.get("IS_VERIFY", "False")
IS_VERIFY = IS_VERIFY_ENV.lower() not in ['false', '0', 'no', 'off']

TUT_VID = os.environ.get("TUT_VID", "https://t.me/HOWTOOPENLINKFAST")

# Force sub channels
FORCE_SUB_CHANNELS = os.environ.get(
    "FORCE_SUB_CHANNELS",
    "-1002903033591,-1001764441595,-1001910410959,-1003011512366,-1002984711351,-1003007163709,-1002930816275,-1002842696173"
)
try:
    FORCE_SUB_CHANNELS = [int(x.strip()) for x in FORCE_SUB_CHANNELS.split(',') if x.strip()]
except Exception:
    FORCE_SUB_CHANNELS = []

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

# Start message
def format_message(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except KeyError:
        return template

START_MSG = format_message(
    os.environ.get(
        "START_MESSAGE",
        "Hello {first}\n\nI can store private files in Specified Channel and other users can access it from special link."
    ),
    DELETE_AFTER=DELETE_AFTER
)

try:
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "7623389594 7623389594 7623389594").split()]
except ValueError:
    raise Exception("Your Admins list does not contain valid integers.")

# Force sub message
FORCE_MSG = format_message(
    os.environ.get(
        "FORCE_SUB_MESSAGE",
        "Hello {first}\n\n<b>You need to join in all my Channels/Groups to use me\n\nKindly Please join all the channels below and try again</b>"
    ),
    DELETE_AFTER=DELETE_AFTER
)

# Custom caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", None)

# Content protection
PROTECT_CONTENT = os.environ.get('PROTECT_CONTENT', "False") == "True"
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'True'

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "<strong>u want direct sex video all type\n\nmom son,bro sis,oyo,desi,rp naughty only,teleugu,mallu,tamil,she male,lesibean\n\nall direct file no link msg me to but vip memeber ship  @Myhero2k</strong>"

ADMINS.append(OWNER_ID)
ADMINS.append(7623389594)

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
