from sqlalchemy import create_engine, event
from api.core.config import settings

try:
    from pgvector.psycopg2 import register_vector
except Exception:
    register_vector = None

engine = create_engine(settings.db_url, pool_pre_ping=True)
VECTOR_ADAPTER = False

@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, connection_record):
    global VECTOR_ADAPTER
    # Ensure lists bind as pgvector `vector` (not numeric)
    if register_vector is not None and not VECTOR_ADAPTER:
        try:
            register_vector(dbapi_connection)
            VECTOR_ADAPTER = True
        except Exception:
            VECTOR_ADAPTER = False
