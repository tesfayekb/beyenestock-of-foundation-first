import logging
import os

import structlog

# S7-4: structlog.configure() mutates a process-global state machine.
# The previous implementation called it on every get_logger() invocation
# — once per module import. Across a long Railway lifetime (workers
# reloaded, agents re-importing helpers, hot-reload during local dev)
# this risks processor-stack drift: each call rebuilds the processor
# list, and a partially-initialised configure (e.g., interrupted by a
# context switch) could leave the pipeline in a half-applied state.
# Guard the call with a module-level sentinel so configuration runs
# exactly once per process.
_configured = False


def get_logger(service_name: str):
    """
    Return a structlog logger bound to ``service_name``.

    Configuration is applied lazily on the first call and never again.
    Subsequent callers get a freshly-bound logger over the already-
    configured pipeline.
    """
    global _configured
    if not _configured:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
                if os.getenv("ENVIRONMENT") == "production"
                else structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.INFO
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )
        _configured = True
    return structlog.get_logger(service_name=service_name)
