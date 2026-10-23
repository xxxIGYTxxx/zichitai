"""不正アクセス・サイバー攻撃ニュース 日次ダイジェスト 設定"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent


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


# このフォルダの .env を優先し、無ければ障害情報モニターの .env を共用する
_load_dotenv(BASE_DIR / ".env")
_load_dotenv(REPO_DIR / ".env")

STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "seen.json"

# 自治体名の判定に、障害情報モニターの監視レジストリを流用
MUNICIPALITIES_CSV = REPO_DIR / "data" / "municipalities.csv"

# 取得設定
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "15"))      # 1情報源のタイムアウト秒
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))         # 失敗時の再試行回数
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))           # 並列数
# BleepingComputer はブラウザ以外のUAを403で弾くため、ブラウザ風にする
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
)

# 抽出・まとめ・表示
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "48"))          # これより古い記事は対象外
FIRST_RUN_HOURS = int(os.getenv("FIRST_RUN_HOURS", "24"))        # 初回（状態なし）に送る範囲
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.5"))     # 同じ行にまとめる類似度の下限（重み付き）
SUMMARY_CHARS = int(os.getenv("SUMMARY_CHARS", "120"))           # 概要文を載せる文字数
MAX_ROWS = int(os.getenv("MAX_ROWS", "150"))                     # 1通に載せる行数の上限

# 送信済み記事の保持日数（これより古いものは掃除）
SEEN_RETENTION_DAYS = int(os.getenv("SEEN_RETENTION_DAYS", "14"))

# メール設定（環境変数 / GitHub Secrets で注入。障害情報モニターと共用）
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
# 宛先はカンマ区切りで複数指定可
MAIL_TO = os.getenv("MAIL_TO", "niwatori67@gmail.com")
MAIL_TO_LIST = [a.strip() for a in MAIL_TO.split(",") if a.strip()]
MAIL_FROM = os.getenv("MAIL_FROM", GMAIL_USER or "niwatori67@gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

# 「新着なし」でもメールを送るか（日刊なので既定は送る）
NOTIFY_EMPTY = os.getenv("NOTIFY_EMPTY", "true").lower() in ("1", "true", "yes")
