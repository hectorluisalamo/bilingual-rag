import structlog, logging, sys, os


def setup_logging():
    logging.basicConfig(stream=sys.stdout, level=os.getenv("LOG_LEVEL","INFO"))
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"), 
            structlog.processors.add_log_level, 
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
setup_logging()
