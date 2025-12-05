"""Hybrid session backend: Redis for hot cache, DB for cold storage.

This backend provides fast session access via Redis while persisting to the
database for durability. Sessions are written to Redis on every save (fast),
and periodically synced to the database in a background thread.

Requires:
    pip install django-redis

Settings:
    SESSION_ENGINE = 'e_footprint_interface.hybrid_session_backend'
    SESSION_REDIS_URL = 'redis://localhost:6379/0'  # or from env
    SESSION_REDIS_TTL = 600  # Hot cache TTL in seconds (default 10 min)
    SESSION_DB_SYNC_INTERVAL = 60  # Sync to DB every N seconds (default 60s)
"""
import threading
import time
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore
from django.core.cache import caches
from django.conf import settings
from efootprint.logger import logger

# Configuration with defaults
REDIS_TTL = getattr(settings, 'SESSION_REDIS_TTL', 600)  # 10 minutes
DB_SYNC_INTERVAL = getattr(settings, 'SESSION_DB_SYNC_INTERVAL', 60)  # 1 minute


class SessionStore(DBSessionStore):
    """Hybrid session store: Redis hot cache + DB cold storage.

    All reads/writes go to Redis for speed. DB is synced in the background
    every DB_SYNC_INTERVAL seconds for durability. Race conditions are safe
    because Redis is the source of truth for active sessions.
    """

    cache_key_prefix = 'session:'
    last_db_sync_key_prefix = 'session_last_sync:'

    def __init__(self, session_key=None):
        super().__init__(session_key)
        self._cache = caches['session_cache']  # Redis cache, configured in CACHES

    def _get_cache_key(self):
        return f"{self.cache_key_prefix}{self._get_or_create_session_key()}"

    def _get_last_sync_key(self):
        return f"{self.last_db_sync_key_prefix}{self._get_or_create_session_key()}"

    def load(self):
        """Load session: try Redis first, fall back to DB."""
        cache_key = self._get_cache_key()

        # Try Redis first
        start = time.time()
        data = self._cache.get(cache_key)
        redis_time = time.time() - start

        if data is not None:
            logger.info(f"Session loaded from Redis in {redis_time*1000:.1f}ms")
            return data

        # Fall back to DB
        logger.info(f"Session not in Redis (checked in {redis_time*1000:.1f}ms), loading from DB")
        start = time.time()
        data = super().load()
        db_time = time.time() - start
        logger.info(f"Session loaded from DB in {db_time*1000:.1f}ms")

        # Populate Redis cache for next time
        if data:
            self._cache.set(cache_key, data, REDIS_TTL)
            logger.info(f"Session cached to Redis (TTL: {REDIS_TTL}s)")

        return data

    def _sync_to_db_background(self, must_create):
        """Sync session to DB in background thread."""
        def do_sync():
            try:
                start = time.time()
                super(SessionStore, self).save(must_create=must_create)
                db_time = time.time() - start
                logger.info(f"Session synced to DB in background: {db_time*1000:.1f}ms")
            except Exception as e:
                logger.error(f"Background DB sync failed: {e}")

        thread = threading.Thread(target=do_sync, daemon=True)
        thread.start()

    def save(self, must_create=False):
        """Save session: always to Redis (fast), periodically to DB (background)."""
        cache_key = self._get_cache_key()
        session_data = self._get_session(no_load=must_create)

        # Always save to Redis (fast) - this is the source of truth for active sessions
        start = time.time()
        self._cache.set(cache_key, session_data, REDIS_TTL)
        redis_time = time.time() - start
        logger.info(f"Session saved to Redis in {redis_time*1000:.1f}ms (TTL: {REDIS_TTL}s)")

        # Check if we need to sync to DB (in background)
        last_sync_key = self._get_last_sync_key()
        last_sync = self._cache.get(last_sync_key) or 0
        now = time.time()

        if now - last_sync >= DB_SYNC_INTERVAL:
            # Update last sync time immediately to prevent concurrent syncs
            self._cache.set(last_sync_key, now, REDIS_TTL * 2)
            # Sync to DB in background thread - doesn't block the response
            self._sync_to_db_background(must_create)
            logger.info(f"DB sync triggered in background (interval: {DB_SYNC_INTERVAL}s)")

    def delete(self, session_key=None):
        """Delete session from both Redis and DB."""
        if session_key is None:
            session_key = self._get_or_create_session_key()

        cache_key = f"{self.cache_key_prefix}{session_key}"
        self._cache.delete(cache_key)
        self._cache.delete(f"{self.last_db_sync_key_prefix}{session_key}")
        super().delete(session_key)
        logger.info("Session deleted from Redis and DB")

    def flush(self):
        """Flush session: delete and create new."""
        self.delete(self._session_key)
        self._session_key = None
        self.modified = True
        self.accessed = True

    @classmethod
    def clear_expired(cls):
        """Clear expired sessions from DB (Redis handles its own expiry via TTL)."""
        super().clear_expired()
