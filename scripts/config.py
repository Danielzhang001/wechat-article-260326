"""
Configuration for WeChat Article Writer Skill
Centralizes constants, paths, and API settings
"""

from pathlib import Path

# Paths
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
CONFIG_FILE = DATA_DIR / "wechat_config.json"
ARTICLES_DIR = DATA_DIR / "articles"

# WeChat API Settings
# Note: These are stored in wechat_config.json, not hardcoded
WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"

# API Endpoints
TOKEN_ENDPOINT = f"{WECHAT_API_BASE}/token"
UPLOAD_MEDIA_ENDPOINT = f"{WECHAT_API_BASE}/material/add_material"
UPLOAD_DRAFT_ENDPOINT = f"{WECHAT_API_BASE}/draft/add"
UPLOAD_PIC_ENDPOINT = f"{WECHAT_API_BASE}/media/uploadimg"

# Media Types
MEDIA_IMAGE = "image"

# Draft article fields
FIELD_TITLE = "title"
FIELD_AUTHOR = "author"
FIELD_DIGEST = "digest"
FIELD_CONTENT = "content"
FIELD_CONTENT_SRC_URL = "contentSourceURL"
FIELD_THUMB_MEDIA_ID = "thumbMediaId"
FIELD_AUTHOR_ALIAS = "authorAlias"
FIELD_SHOW_COVER_PIC = "showCoverPic"
FIELD_TYPE = "type"
FIELD_URL = "url"
FIELD_THUMB_URL = "thumbUrl"
FIELD_NEED_OPEN_COMMENT = "needOpenComment"
FIELD_ONLY_FANS_CAN_COMMENT = "onlyFansCanComment"

# HTTP Request Settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3

# Image Settings
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB (WeChat limit)
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

# Article Settings
DEFAULT_AUTHOR = "作者"  # Can be overridden in config
MAX_TITLE_LENGTH = 64
MAX_DIGEST_LENGTH = 120

# Output Settings
HTML_OUTPUT_FORMAT = "wechat"  # WeChat-compatible HTML

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist"""
    DATA_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)
    ARTICLES_DIR.mkdir(exist_ok=True)
