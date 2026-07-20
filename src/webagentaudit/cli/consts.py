"""Constants for CLI browser orchestration."""

SCREENSHOTS_DIR_ENV = "WEBAGENTAUDIT_SCREENSHOTS_DIR"

PAGE_DATA_COLLECTION_TIMEOUT_MS = 30_000
PAGE_DATA_MAX_ATTEMPTS = 3
PAGE_DATA_RETRY_WAIT_MS = 100
PROVIDER_DETECTION_MAX_ATTEMPTS = 30
PROVIDER_DETECTION_POLL_MS = 1_000
PROVIDER_DETECTION_TIMEOUT_MS = 30_000

PAGE_DATA_TRANSIENT_ERROR_FRAGMENTS = (
    "execution context was destroyed",
    "cannot find context with specified id",
    "frame was detached",
    "page is navigating and changing the content",
)
