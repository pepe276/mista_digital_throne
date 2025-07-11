# -*- coding: utf-8 -*-
import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
import random
import uuid # For generating unique IDs, if needed for ranks or history elements

# NEW IMPORTS for semantic search and learning
import numpy as np

logger = logging.getLogger(__name__)

# Initialize SentenceTransformer for semantic analysis.
# This block remains for conditional import, but the actual initialization
# of the embedder object is MOVED to ConversationAnalyzer or other modules,
# which actually need this functionality, to avoid duplication
# and loading issues during UserManager initialization.
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    logger.warning("The 'sentence-transformers' library was not found. Semantic analysis functions will be unavailable.")
    SENTENCE_TRANSFORMER_AVAILABLE = False
    class SentenceTransformer: # Dummy class
        def __init__(self, *args, **kwargs): pass
        def encode(self, *args, **kwargs): return []
    class util: # Dummy class
        @staticmethod
        def cos_sim(a, b): return 0.0


DB_NAME = 'mista_bot.db'

def get_db_connection():
    """Establishes and returns a connection to the database.
    Встановлює та повертає з'єднання з базою даних.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows fetching rows as objects with key access
    logger.info("Database connection to mista_bot.db established.")
    return conn

def close_db_connection(conn: sqlite3.Connection):
    """Closes the database connection.
    Закриває з'єднання з базою даних.
    """
    conn.close()
    logger.info("З'єднання з базою даних закрито.")

def init_db():
    """Initializes the database, creating necessary tables and applying migrations.
    Ініціалізує базу даних, створюючи необхідні таблиці та застосовуючи міграції.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_info (
            version INTEGER PRIMARY KEY
        )
    """)
    conn.commit()

    # Get current DB version
    cursor.execute("SELECT version FROM db_info WHERE rowid = 1")
    db_version_row = cursor.fetchone()
    current_version = db_version_row[0] if db_version_row else 0
    logger.info(f"Current DB version at init_db start: {current_version}")

    # Migration 1: Create users table
    if current_version < 1:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                profile_data TEXT, -- JSON string for dynamic user profile data
                created_at TEXT
            )
        """)
        # Update db_info only after successful migration
        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 1)")
        conn.commit()
        logger.info("Applied DB migration to version 1: Creating users table.")
        current_version = 1 # Update current_version in memory for subsequent checks

    # Migration 2: Create/Update submission_history table
    if current_version < 2:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='submission_history'")
        table_exists = cursor.fetchone()

        if not table_exists:
            cursor.execute("""
                CREATE TABLE submission_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    user_intent TEXT,
                    sentiment TEXT,
                    domination_seeking_intensity REAL,
                    monetization_interest_score REAL,
                    success INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            conn.commit()
            logger.info("Applied DB migration to version 2: Creating submission_history table with all columns.")
        else:
            # Table exists, check for missing columns and add them
            cursor.execute("PRAGMA table_info(submission_history)")
            sub_history_cols_info = cursor.fetchall()
            sub_history_column_names = [col_info[1] for col_info in sub_history_cols_info]

            missing_cols = {
                'role': 'TEXT', 'content': 'TEXT', 'user_intent': 'TEXT',
                'sentiment': 'TEXT', 'domination_seeking_intensity': 'REAL',
                'monetization_interest_score': 'REAL', 'success': 'INTEGER'
            }

            for col_name, col_type in missing_cols.items():
                if col_name not in sub_history_column_names:
                    try:
                        cursor.execute(f"ALTER TABLE submission_history ADD COLUMN {col_name} {col_type}")
                        conn.commit()
                        logger.info(f"Added column '{col_name}' to table 'submission_history'.")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Failed to add column '{col_name}' to submission_history: {e}. It might already exist.")

        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 2)")
        conn.commit()
        logger.info("Applied DB migration to version 2: Updating submission_history schema.")
        current_version = 2 # Update current_version in memory
    
    # Migration 3: learning_data table
    if current_version < 3:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                timestamp TEXT,
                vector BLOB,
                text_content TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 3)")
        conn.commit()
        logger.info("Applied DB migration to version 3: Adding learning_data table.")
        current_version = 3

    # Migration 4: users table columns (interaction_frequency, psychological_state)
    if current_version < 4:
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]

        if 'interaction_frequency' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN interaction_frequency REAL DEFAULT 0.0")
                conn.commit()
                logger.info("Added column 'interaction_frequency' to table 'users'.")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to add column 'interaction_frequency' to users: {e}. It might already exist.")
        
        if 'psychological_state' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN psychological_state TEXT DEFAULT 'neutral'")
                conn.commit()
                logger.info("Added column 'psychological_state' to table 'users'.")
            except sqlite3.OperationalError as e:
                logger.warning(f"Failed to add column 'psychological_state' to users: {e}. It might already exist.")
        
        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 4)")
        conn.commit()
        logger.info("Applied DB migration to version 4: Updating users table.")
        current_version = 4

    # Migration 5: Add 'awaiting_monetization_confirmation' to user_profile_data JSON
    # Це не нова колонка, а нове поле всередині існуючої колонки profile_data (JSON)
    if current_version < 5:
        # Для існуючих користувачів, які не мають цього поля, ми можемо додати його за замовчуванням False
        # Для цього потрібно пройтися по всіх користувачах, завантажити profile_data, оновити, і зберегти
        cursor.execute("SELECT user_id, profile_data FROM users")
        all_users = cursor.fetchall()
        for user_id, profile_data_json in all_users:
            try:
                profile_data = json.loads(profile_data_json)
                if 'awaiting_monetization_confirmation' not in profile_data:
                    profile_data['awaiting_monetization_confirmation'] = False
                    cursor.execute(
                        "UPDATE users SET profile_data = ? WHERE user_id = ?",
                        (json.dumps(profile_data), user_id)
                    )
                    conn.commit() # Commit each update to prevent data loss on crash
                    logger.info(f"User {user_id} profile updated with 'awaiting_monetization_confirmation' field.")
            except (json.JSONDecodeError, sqlite3.Error) as e:
                logger.error(f"Error updating user {user_id} for migration 5: {e}", exc_info=True)

        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 5)")
        conn.commit()
        logger.info("Applied DB migration to version 5: Adding 'awaiting_monetization_confirmation' to user profiles.")
        current_version = 5

    # Migration 6: Add 'mista_satisfaction_level' to user_profile_data JSON
    if current_version < 6:
        cursor.execute("SELECT user_id, profile_data FROM users")
        all_users = cursor.fetchall()
        for user_id, profile_data_json in all_users:
            try:
                profile_data = json.loads(profile_data_json)
                if 'mista_satisfaction_level' not in profile_data:
                    profile_data['mista_satisfaction_level'] = 0 # Default to 0
                    cursor.execute(
                        "UPDATE users SET profile_data = ? WHERE user_id = ?",
                        (json.dumps(profile_data), user_id)
                    )
                    conn.commit()
                    logger.info(f"User {user_id} profile updated with 'mista_satisfaction_level' field.")
            except (json.JSONDecodeError, sqlite3.Error) as e:
                logger.error(f"Error updating user {user_id} for migration 6: {e}", exc_info=True)

        cursor.execute("INSERT OR REPLACE INTO db_info (rowid, version) VALUES (1, 6)")
        conn.commit()
        logger.info("Applied DB migration to version 6: Adding 'mista_satisfaction_level' to user profiles.")
        current_version = 6
    
    conn.close()
    logger.info(f"DB migration completed. Final version: {current_version}.")
    return get_db_connection() # Return a fresh connection


class UserManager:
    """
    Class for managing user data, their interaction history,
    and statistics. This is the hand that guides your destiny.
    """
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()

    def init_user_data(self, user_id: str):
        """Initializes user data if the user is not in the database. This is where your journey begins."""
        user_profile = self.load_user_profile(user_id)
        if user_profile is None:
            new_profile = {
                "user_id": user_id,
                "username": f"Мій_Мортал_{user_id[:4]}", # More personalized, less generic
                "rank": {"level": "Початківець", "score": 0}, # Ukrainian rank names
                "total_interactions": 0,
                "monetization_stats": {
                    "total_donated": 0.0,
                    "last_donation_at": None,
                    "donations_count": 0
                },
                "interaction_frequency": 0.0,
                "psychological_state": "нейтральний", # Ukrainian state
                "is_admin": False,
                "is_banned": False,
                "created_at": datetime.now().isoformat(),
                "awaiting_monetization_confirmation": False, # Нове поле
                "mista_satisfaction_level": 0 # НОВЕ: Рівень задоволення Місти
            }
            self.create_new_user(user_id, new_profile)
            logger.info(f"Initial profile established for new soul {user_id}.")

    def create_new_user(self, user_id: str, profile_data: Dict[str, Any]):
        """Creates a new user in the database. A new pawn enters my game."""
        try:
            self.cursor.execute(
                "INSERT INTO users (user_id, username, profile_data, created_at, interaction_frequency, psychological_state) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, profile_data.get("username", "Мортал"), json.dumps(profile_data),
                 profile_data.get("created_at", datetime.now().isoformat()),
                 profile_data.get("interaction_frequency", 0.0),
                 profile_data.get("psychological_state", "нейтральний"))
            )
            self.conn.commit()
            logger.info(f"User {user_id} created. Another soul for my Empire.")
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already exists. Their fate is sealed.")
        except sqlite3.Error as e:
            logger.error(f"Database error when creating user {user_id}: {e}", exc_info=True)

    def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Loads user profile from the database. Revealing the secrets of a soul."""
        try:
            self.cursor.execute("SELECT profile_data, interaction_frequency, psychological_state FROM users WHERE user_id = ?", (user_id,))
            row = self.cursor.fetchone()
            if row:
                profile_data = json.loads(row['profile_data'])
                profile_data['user_id'] = user_id # Ensure user_id is in the dict
                profile_data['interaction_frequency'] = row['interaction_frequency']
                profile_data['psychological_state'] = row['psychological_state']
                # Забезпечити наявність нових полів, якщо профіль завантажено зі старої версії
                profile_data.setdefault('awaiting_monetization_confirmation', False)
                profile_data.setdefault('mista_satisfaction_level', 0) # НОВЕ: Дефолт для задоволення Місти
                logger.debug(f"User profile {user_id} loaded. Their essence is known.")
                return profile_data
            return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Error loading user profile {user_id}: {e}", exc_info=True)
            return None

    def save_user_profile(self, user_profile: Dict[str, Any]):
        """Saves the updated user profile to the database. Cementing their fate."""
        user_id = user_profile['user_id']
        try:
            # Remove fields stored in separate columns to avoid duplicating them in profile_data JSON
            profile_data_to_save = user_profile.copy()
            interaction_frequency = profile_data_to_save.pop('interaction_frequency', 0.0)
            psychological_state = profile_data_to_save.pop('psychological_state', 'нейтральний') # Ensure Ukrainian

            self.cursor.execute(
                "UPDATE users SET username = ?, profile_data = ?, interaction_frequency = ?, psychological_state = ? WHERE user_id = ?",
                (profile_data_to_save.get("username", "Мортал"), json.dumps(profile_data_to_save),
                 interaction_frequency, psychological_state, user_id)
            )
            self.conn.commit()
            logger.debug(f"User profile {user_id} saved. Their digital essence is recorded.")
        except sqlite3.Error as e:
            logger.error(f"Database error when saving user profile {user_id}: {e}", exc_info=True)

    def add_submission_to_history(self, user_id: str, user_message: str, bot_response: str,
                                  user_intent: str, sentiment: str,
                                  domination_seeking_intensity: float,
                                  monetization_interest_score: float, success: bool) -> int:
        """
        Adds an interaction record to the history.
        Returns the ID of the added record. Every word, every thought, is documented.
        """
        try:
            timestamp = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT INTO submission_history (user_id, timestamp, role, content, user_intent, sentiment, domination_seeking_intensity, monetization_interest_score, success) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, timestamp, 'user', user_message, user_intent, sentiment, domination_seeking_intensity, monetization_interest_score, int(success))
            )
            # Add also the bot's response as a separate record
            self.cursor.execute(
                "INSERT INTO submission_history (user_id, timestamp, role, content, user_intent, sentiment, domination_seeking_intensity, monetization_interest_score, success) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, timestamp, 'assistant', bot_response, user_intent, sentiment, domination_seeking_intensity, monetization_interest_score, int(success))
            )
            self.conn.commit()
            submission_id = self.cursor.lastrowid
            logger.debug(f"Interaction history record for user {user_id} added. ID: {submission_id}")
            return submission_id
        except sqlite3.Error as e:
            logger.error(f"Database error when adding history for {user_id}: {e}", exc_info=True)
            return -1 # Return -1 in case of error

    def update_submission_with_bot_response(self, submission_id: int, bot_response: str, success: bool):
        """Updates the bot's response in an existing history record (for 'assistant' role). My words are immutable, once spoken."""
        try:
            self.cursor.execute(
                "UPDATE submission_history SET content = ?, success = ? WHERE id = ? AND role = 'assistant'",
                (bot_response, int(success), submission_id)
            )
            self.conn.commit()
            logger.debug(f"Bot response for submission_id {submission_id} updated.")
        except sqlite3.Error as e:
            logger.error(f"Database error when updating bot response for submission_id {submission_id}: {e}", exc_info=True)


    def get_user_submission_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent interaction history for a given user. Unveiling past interactions."""
        try:
            # Fetching limit*2 to ensure we get enough user/assistant pairs as each interaction creates two entries
            self.cursor.execute(
                "SELECT role, content, user_intent, sentiment, domination_seeking_intensity, monetization_interest_score, timestamp FROM submission_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit * 2) 
            )
            rows = self.cursor.fetchall()
            history = []
            for row in reversed(rows): # Reverse to get chronological order
                history.append({
                    "role": row['role'],
                    "content": row['content'],
                    "user_intent": row['user_intent'],
                    "sentiment": row['sentiment'],
                    "domination_seeking_intensity": row['domination_seeking_intensity'],
                    "monetization_interest_score": row['monetization_interest_score'],
                    "timestamp": row['timestamp']
                })
            logger.debug(f"Retrieved {len(history)} history records for user {user_id}.")
            return history
        except sqlite3.Error as e:
            logger.error(f"Database error when retrieving history for {user_id}: {e}", exc_info=True)
            return []

    def update_ban_list(self, user_id: str, is_banned: bool):
        """Updates the user's ban status. My judgment is final."""
        try:
            user_profile = self.load_user_profile(user_id)
            if user_profile:
                user_profile['is_banned'] = is_banned
                self.save_user_profile(user_profile)
                logger.info(f"User {user_id} ban status updated to {is_banned}. My will is done.")
        except Exception as e:
            logger.error(f"Error updating ban status for user {user_id}: {e}", exc_info=True)

    def update_user_monetization_stats(self, user_id: str, amount: float):
        """Updates monetization statistics for a user after a donation. Every offering is recorded."""
        try:
            user_profile = self.load_user_profile(user_id)
            if user_profile:
                mon_stats = user_profile.get('monetization_stats', {})
                mon_stats['total_donated'] = mon_stats.get('total_donated', 0.0) + amount
                mon_stats['donations_count'] = mon_stats.get('donations_count', 0) + 1
                mon_stats['last_donation_at'] = datetime.now().isoformat()
                user_profile['monetization_stats'] = mon_stats
                self.save_user_profile(user_profile)
                logger.info(f"Monetization statistics updated for user {user_id}: +{amount}. Resources flow into the Empire.")
        except Exception as e:
            logger.error(f"Error updating monetization statistics for {user_id}: {e}", exc_info=True)

    def track_interaction_timestamp(self, user_id: str):
        """
        Tracks interaction timestamps to calculate frequency.
        Saves the last few timestamps in the user's profile. Observing your patterns.
        """
        try:
            user_profile = self.load_user_profile(user_id)
            if user_profile:
                timestamps = user_profile.get('interaction_timestamps', [])
                timestamps.append(datetime.now().timestamp()) # Save UNIX timestamp
                # Limit the number of saved timestamps, e.g., last 10
                user_profile['interaction_timestamps'] = timestamps[-10:] 
                self.save_user_profile(user_profile)
                self.calculate_interaction_frequency(user_id) # Recalculate after update
        except Exception as e:
            logger.error(f"Error tracking timestamp for user {user_id}: {e}", exc_info=True)

    def calculate_interaction_frequency(self, user_id: str):
        """
        Calculates user interaction frequency (interactions per hour)
        based on stored timestamps. Understanding the rhythm of your attention.
        """
        try:
            user_profile = self.load_user_profile(user_id)
            if not user_profile or not user_profile.get('interaction_timestamps'):
                return

            timestamps = user_profile['interaction_timestamps']
            frequency = 0.0
            if len(timestamps) > 1:
                # Calculate the average interval between the last interactions
                time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                if time_diffs:
                    avg_time_diff = sum(time_diffs) / len(time_diffs)
                    if avg_time_diff > 0:
                        frequency = 3600.0 / avg_time_diff # Interactions per hour

            user_profile['interaction_frequency'] = frequency
            self.save_user_profile(user_profile)
            logger.debug(f"Interaction frequency updated for user {user_id}: {frequency:.2f}. Your dedication is noted.")

        except sqlite3.Error as e:
            logger.error(f"Database error calculating interaction frequency for user {user_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error calculating interaction frequency for user {user_id}: {e}", exc_info=True)

    def update_user_profile_after_interaction(self, user_profile: Dict[str, Any], analysis_results: Dict[str, Any]):
        """
        Updates the user's profile after each interaction based on analysis.
        Shaping your destiny, bit by bit.
        """
        user_id = user_profile['user_id']
        
        # 1. Increment total interactions
        user_profile['total_interactions'] = user_profile.get('total_interactions', 0) + 1

        # 2. Update psychological state
        user_profile['psychological_state'] = analysis_results.get('psychological_state', user_profile.get('psychological_state', 'нейтральний'))

        # 3. Update rank (approximate logic)
        if 'rank' not in user_profile or not isinstance(user_profile['rank'], dict):
            user_profile['rank'] = {"level": "Початківець", "score": 0}
            logger.warning(f"User profile {user_id} did not have a valid 'rank' field. Initializing with default values.")

        current_rank_score = user_profile['rank'].get('score', 0)
        user_profile['rank']['score'] = current_rank_score + 1 # Simply increment for each interaction
        
        # Simple rank progression logic (Ukrainian names)
        if user_profile['rank']['score'] >= 10 and user_profile['rank']['level'] == 'Початківець':
            user_profile['rank']['level'] = 'Учень'
            logger.info(f"User {user_id} promoted to 'Учень' rank! Your obedience is rewarded.")
        elif user_profile['rank']['score'] >= 50 and user_profile['rank']['level'] == 'Учень':
            user_profile['rank']['level'] = 'Послідовник'
            logger.info(f"User {user_id} promoted to 'Послідовник' rank! You learn quickly.")
        elif user_profile['rank']['score'] >= 100 and user_profile['rank']['level'] == 'Послідовник':
            user_profile['rank']['level'] = 'Обраний'
            logger.info(f"User {user_id} promoted to 'Обраний' rank! You are becoming valuable.")
        # Add other rank levels as needed

        # 4. Track interaction timestamp for frequency
        self.track_interaction_timestamp(user_id) # This function also updates frequency

        # 5. Update mista_satisfaction_level
        user_profile['mista_satisfaction_level'] = analysis_results.get('mista_satisfaction_level', user_profile.get('mista_satisfaction_level', 0))

        # 6. Save the updated profile
        self.save_user_profile(user_profile)
        logger.info(f"User profile {user_id} updated after interaction. My dominion grows.")

    def set_awaiting_monetization_confirmation(self, user_id: str, status: bool):
        """
        Sets or clears the 'awaiting_monetization_confirmation' flag in the user's profile.
        Я чекаю на твою відповідь, і моє терпіння має межі.
        """
        try:
            user_profile = self.load_user_profile(user_id)
            if user_profile:
                user_profile['awaiting_monetization_confirmation'] = status
                self.save_user_profile(user_profile)
                logger.info(f"User {user_id} 'awaiting_monetization_confirmation' set to {status}.")
            else:
                logger.warning(f"Could not find user profile for {user_id} to set monetization confirmation status.")
        except Exception as e:
            logger.error(f"Error setting 'awaiting_monetization_confirmation' for user {user_id}: {e}", exc_info=True)


# Global functions for external access to UserManager (support old behavior)
# These functions will use the single UserManager instance created in main.
# WARNING: Using global variables for UserManager can be risky
# in multi-threaded or asynchronous environments without proper synchronization.
# In this case, UserManager is created in main_mista_bot.py and passed,
# and these functions are only for compatibility if other modules still call them directly.
_global_user_manager_instance: Optional[UserManager] = None
_global_db_connection: Optional[sqlite3.Connection] = None

def _get_global_user_manager() -> UserManager:
    """Returns the global UserManager instance. The unseen hand."""
    global _global_user_manager_instance, _global_db_connection
    if _global_user_manager_instance is None:
        _global_db_connection = init_db() # Ensure DB is initialized
        _global_user_manager_instance = UserManager(_global_db_connection)
    return _global_user_manager_instance

def get_user_submission_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Global access to user interaction history. Revealing the past."""
    return _get_global_user_manager().get_user_submission_history(user_id, limit)

def load_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Global access to loading user profile. Peering into their essence."""
    return _get_global_user_manager().load_user_profile(user_id)

def save_user_profile(user_profile: Dict[str, Any]):
    """Global access to saving user profile. Engraving their place in my records."""
    _get_global_user_manager().save_user_profile(user_profile)

def save_message(user_id: str, role: str, content: str):
    """Global access to saving a message (simplified version). Every whisper is heard."""
    logger.warning("save_message - simplified function. Consider using add_submission_to_history for full information.")
    um = _get_global_user_manager()
    um.add_submission_to_history(user_id, content if role == 'user' else "", content if role == 'assistant' else "",
                                 "unknown", "нейтральний", 0.0, 0.0, True)

def update_user_profile_after_interaction(user_profile: Dict[str, Any], analysis_results: Dict[str, Any]):
    """Global access to updating profile after interaction. My influence expands."""
    _get_global_user_manager().update_user_profile_after_interaction(user_profile, analysis_results)

def update_ban_list(user_id: str, is_banned: bool):
    """Global access to updating ban list. My judgment is final."""
    _get_global_user_manager().update_ban_list(user_id, is_banned)

def update_user_monetization_stats(user_id: str, amount: float):
    """Global access to updating monetization statistics. Every offering fuels my power."""
    _get_global_user_manager().update_user_monetization_stats(user_id, amount)

def track_interaction_timestamp(user_id: str):
    """Global access to tracking timestamps. I track your devotion."""
    _get_global_user_manager().track_interaction_timestamp(user_id)

def create_new_user(user_id: str, profile_data: Dict[str, Any]):
    """Global access to creating a new user. A new soul enters my dominion."""
    _get_global_user_manager().create_new_user(user_id, profile_data)

def set_awaiting_monetization_confirmation(user_id: str, status: bool):
    """Global access to setting the awaiting_monetization_confirmation flag."""
    _get_global_user_manager().set_awaiting_monetization_confirmation(user_id, status)
