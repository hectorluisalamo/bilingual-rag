import logging, os, sys, json, re


def sanitize_db_url(url: str) -> str:
    if not url:
        return url
    # Hide password
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:*****@", url)

class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        for k in ("request_id", "route", "index", "topic", "lang", "duration_ms"):
            if hasattr(record, k):
                base[k] = getattr(record, k)
        if record.exc_info:
            base["exc_type"] = record.exc_info[0].__name__
        return json.dumps(base, ensure_ascii=False)

def configure_logging(db_url_for_log: str | None = None):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler(sys.stdout)
    fmt = os.getenv("LOG_FORMAT", "json")
    if fmt == "json":
        h.setFormatter(JsonLineFormatter())
    else:
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(h)
    root.setLevel(level)
    if os.getenv("SA_LOG", "0") in ("1", "true", "True"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
    if db_url_for_log:
        root.info("startup db", sanitize_db_url(db_url_for_log))
