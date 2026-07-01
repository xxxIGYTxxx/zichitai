"""全自治体 障害情報モニター 設定"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """依存ライブラリ無しで .env を os.environ に反映（既存の環境変数は上書きしない）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(exist_ok=True)

# 元データ（code4fukui/localgovjp 由来）と生成レジストリ
SOURCE_CSV = DATA_DIR / "localgovjp.csv"
REGISTRY_CSV = DATA_DIR / "municipalities.csv"
STATE_FILE = STATE_DIR / "seen.json"

# 巡回設定
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "12"))      # 1サイトのタイムアウト秒
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "24"))          # 並列数
USER_AGENT = os.getenv(
    "USER_AGENT",
    "JichitaiFailureMonitor/1.0 (+daily digest; contact niwatori67@gmail.com)",
)
MAX_ITEMS_PER_SITE = int(os.getenv("MAX_ITEMS_PER_SITE", "40"))  # 1サイトの通知上限
MAX_FOLLOW = int(os.getenv("MAX_FOLLOW", "3"))            # 追跡する「お知らせ一覧」page数

# 状態の保持日数（これより古い既知アイテムは掃除）
SEEN_RETENTION_DAYS = int(os.getenv("SEEN_RETENTION_DAYS", "45"))

# メール設定（環境変数 / GitHub Secrets で注入）
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
# 宛先はカンマ区切りで複数指定可
MAIL_TO = os.getenv("MAIL_TO", "niwatori67@gmail.com")
MAIL_TO_LIST = [a.strip() for a in MAIL_TO.split(",") if a.strip()]
MAIL_FROM = os.getenv("MAIL_FROM", GMAIL_USER or "niwatori67@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
