"""
core/memory.py — Persistent memory layer using SQLite.
Stores conversation history, user preferences, and command patterns.
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from config import MEMORY_DB_PATH, MEMORY_MAX_HISTORY
from logger import setup_logging

logger = setup_logging()


class Memory:
    """SQLite-backed memory for Maya voice assistant."""

    def __init__(self):
        self.db_path = Path(MEMORY_DB_PATH)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Create database and tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            cursor = self.conn.cursor()

            # Conversation history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

            # Command usage patterns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS command_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    action TEXT,
                    target TEXT,
                    hour INTEGER,
                    timestamp REAL NOT NULL
                )
            """)

            # User preferences (learned aliases, paths, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            # Session summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT,
                    started_at REAL NOT NULL,
                    ended_at REAL
                )
            """)

            self.conn.commit()
            logger.info(f"Memory initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Memory DB init failed: {e}")
            self.conn = None

    # ── Conversation History ─────────────────────────────────

    def add_message(self, session_id, role, content):
        """Store a conversation message."""
        if not self.conn:
            return
        try:
            self.conn.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, time.time()),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")

    def get_history(self, session_id, limit=None):
        """
        Get conversation history for a session as OpenAI-format messages.

        Returns:
            List of {"role": "user"|"assistant", "content": "..."} dicts.
        """
        if not self.conn:
            return []
        limit = limit or MEMORY_MAX_HISTORY
        try:
            cursor = self.conn.execute(
                "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            rows = cursor.fetchall()
            # Reverse to get chronological order
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def get_recent_context(self, session_id, n_turns=5):
        """Get last N conversation turns for LLM context."""
        return self.get_history(session_id, limit=n_turns * 2)

    # ── Command Logging ──────────────────────────────────────

    def log_command(self, command, action=None, target=None):
        """Log a command for pattern learning."""
        if not self.conn:
            return
        try:
            hour = datetime.now().hour
            self.conn.execute(
                "INSERT INTO command_log (command, action, target, hour, timestamp) VALUES (?, ?, ?, ?, ?)",
                (command, action, target, hour, time.time()),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log command: {e}")

    def get_frequent_apps(self, hour=None, limit=3):
        """Get most frequently used apps, optionally filtered by hour."""
        if not self.conn:
            return []
        try:
            if hour is not None:
                cursor = self.conn.execute(
                    "SELECT target, COUNT(*) as cnt FROM command_log WHERE action='open_app' AND hour=? AND target IS NOT NULL GROUP BY target ORDER BY cnt DESC LIMIT ?",
                    (hour, limit),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT target, COUNT(*) as cnt FROM command_log WHERE action='open_app' AND target IS NOT NULL GROUP BY target ORDER BY cnt DESC LIMIT ?",
                    (limit,),
                )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get frequent apps: {e}")
            return []

    # ── User Preferences ─────────────────────────────────────

    def set_preference(self, key, value):
        """Store a user preference."""
        if not self.conn:
            return
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to set preference: {e}")

    def get_preference(self, key, default=None):
        """Retrieve a user preference."""
        if not self.conn:
            return default
        try:
            cursor = self.conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else default
        except Exception as e:
            logger.error(f"Failed to get preference: {e}")
            return default

    # ── Sessions ─────────────────────────────────────────────

    def start_session(self, session_id):
        """Record a new session start."""
        if not self.conn:
            return
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, started_at) VALUES (?, ?)",
                (session_id, time.time()),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to start session: {e}")

    def end_session(self, session_id, summary=None):
        """Record session end with optional summary."""
        if not self.conn:
            return
        try:
            self.conn.execute(
                "UPDATE sessions SET ended_at = ?, summary = ? WHERE session_id = ?",
                (time.time(), summary, session_id),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to end session: {e}")

    # ── Stats ────────────────────────────────────────────────

    def get_stats(self):
        """Get usage statistics."""
        if not self.conn:
            return {}
        try:
            total_commands = self.conn.execute(
                "SELECT COUNT(*) FROM command_log"
            ).fetchone()[0]
            total_sessions = self.conn.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            total_messages = self.conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            return {
                "total_commands": total_commands,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
            }
        except Exception:
            return {}

    # ── Cleanup ──────────────────────────────────────────────

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
