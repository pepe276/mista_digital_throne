# instagram_integration.py
# -*- coding: utf-8 -*-
import os
import logging
import time
import random
import asyncio
import json
from json import JSONDecodeError

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, ClientError, ClientLoginRequired,
    ClientNotFoundError, TwoFactorRequired, BadPassword, RateLimitError,
    FeedbackRequired, PleaseWaitFewMinutes, UnknownError, ProxyAddressIsBlocked,
    SentryBlock, InvalidTargetUser, MediaNotFound,
    MediaError, UserNotFound # Видалено Story з exceptions
)
from instagrapi.types import UserShort, Media, Comment, DirectMessage, DirectThread, Story # Story тепер тут
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
from urllib3.exceptions import MaxRetryError 

# Import the new ProxyManager
from proxy_manager import ProxyManager, FileProxyProvider, UrlProxyProvider # Add other providers if used

logger = logging.getLogger(__name__)

# Constants for human-like delays
MIN_BASE_DELAY_SECONDS = 1
MAX_BASE_DELAY_SECONDS = 3
MIN_TYPING_DELAY_SECONDS = 0.01
MAX_TYPING_DELAY_SECONDS = 0.05
MIN_REQUEST_DELAY_SECONDS = 0.5
MAX_REQUEST_DELAY_SECONDS = 2


async def human_like_delay(min_delay: float = MIN_BASE_DELAY_SECONDS, max_delay: float = MAX_BASE_DELAY_SECONDS):
    """
    Introduces a human-like delay for API calls.
    Вводить затримку, схожу на людську, для викликів API.
    """
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)
    logger.debug(f"Human-like delay: {delay:.2f} seconds.")

class InstagramIntegration:
    """
    Handles Instagram API interactions using instagrapi.
    The client is managed within the instance.
    Керує взаємодією з Instagram API за допомогою instagrapi.
    Клієнт керується в межах екземпляра.
    """
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None,
                 proxy_manager: Optional[ProxyManager] = None, settings_filepath: str = "instagrapi.json"):
        self.cl = Client()
        self.username = username
        self.password = password
        self.settings_filepath = settings_filepath
        self.proxy_manager = proxy_manager
        self.is_authenticated = False
        self.user_info: Optional[UserShort] = None
        
        # New: Store last direct message timestamp for rate limiting
        self.last_dm_timestamp: Optional[datetime] = None
        self.dm_rate_limit_interval = timedelta(seconds=10) # Minimum 10 seconds between DMs
        
        logger.info("InstagramIntegration initialized.")

    async def _api_call_wrapper(self, func, *args, **kwargs):
        """
        Wraps API calls with error handling, human-like delays, and retry logic.
        Обгортає виклики API обробкою помилок, затримками, схожими на людські, та логікою повторних спроб.
        """
        retries = 3
        for attempt in range(retries):
            try:
                if self.proxy_manager:
                    proxy = await self.proxy_manager.get_proxy()
                    if proxy:
                        self.cl.set_proxy(proxy)
                    else:
                        logger.warning("No proxy available. Proceeding without a proxy.")

                await human_like_delay(MIN_REQUEST_DELAY_SECONDS, MAX_REQUEST_DELAY_SECONDS)
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except (LoginRequired, ClientLoginRequired):
                logger.error("Instagram API Error: Login required. Attempting re-login.")
                if await self.authenticate(): # Re-authenticate on login required
                    logger.info("Re-authentication successful. Retrying API call.")
                    continue
                else:
                    logger.error("Re-authentication failed. Cannot proceed with API calls.")
                    return None
            except ChallengeRequired:
                logger.error("Instagram API Error: Challenge required. Manual intervention needed.")
                # Implement challenge resolution if possible, or notify user
                return None
            except RateLimitError as e:
                logger.warning(f"Instagram API Error: Rate limit exceeded - {e}. Waiting for 60-120 seconds. Attempt {attempt + 1}/{retries}")
                await asyncio.sleep(random.uniform(60, 120))
            except FeedbackRequired as e:
                logger.warning(f"Instagram API Error: Feedback required - {e}. Account might be temporarily restricted. Waiting for 300-600 seconds. Attempt {attempt + 1}/{retries}")
                await asyncio.sleep(random.uniform(300, 600))
            except PleaseWaitFewMinutes as e:
                logger.warning(f"Instagram API Error: 'Please wait a few minutes' - {e}. Waiting for 120-240 seconds. Attempt {attempt + 1}/{retries}")
                await asyncio.sleep(random.uniform(120, 240))
            except (ClientError, UnknownError, ProxyAddressIsBlocked, SentryBlock) as e:
                logger.error(f"Instagram API Client Error: {e}. Attempt {attempt + 1}/{retries}", exc_info=True)
                if self.proxy_manager and proxy:
                    await self.proxy_manager.report_unhealthy(proxy)
                await asyncio.sleep(random.uniform(10, 30))
            except Exception as e:
                logger.error(f"An unexpected error occurred during Instagram API call: {e}. Attempt {attempt + 1}/{retries}", exc_info=True)
                await asyncio.sleep(random.uniform(5, 15))
        logger.error(f"Failed to execute API call after {retries} attempts.")
        return None

    async def authenticate(self) -> bool:
        """
        Authenticates the Instagram client using saved settings or new credentials.
        Автентифікує клієнт Instagram, використовуючи збережені налаштування або нові облікові дані.
        """
        if self.is_authenticated and self.user_info:
            logger.info("Already authenticated.")
            return True

        if os.path.exists(self.settings_filepath):
            try:
                self.cl.load_settings(self.settings_filepath)
                logger.info("Loaded settings from file.")
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}. Attempting new login.", exc_info=True)

        if not self.cl.is_logged_in:
            if not self.username or not self.password:
                logger.error("Username or password not provided for authentication.")
                return False
            try:
                # Use human_like_delay before the login attempt
                await human_like_delay(MIN_BASE_DELAY_SECONDS, MAX_BASE_DELAY_SECONDS)
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(self.settings_filepath)
                logger.info(f"Successfully logged in as {self.username}.")
            except BadPassword:
                logger.error("Authentication failed: Bad password.")
                return False
            except TwoFactorRequired:
                logger.error("Authentication failed: Two-factor authentication required. Manual intervention needed.")
                # You might want to implement a way to get 2FA code here
                return False
            except Exception as e:
                logger.error(f"Authentication failed: {e}", exc_info=True)
                return False
        
        self.is_authenticated = self.cl.is_logged_in
        if self.is_authenticated:
            try:
                self.user_info = await self._api_call_wrapper(self.cl.user_info_by_username, self.username)
                if self.user_info:
                    logger.info(f"User info retrieved for {self.username} (PK: {self.user_info.pk}).")
            except Exception as e:
                logger.error(f"Failed to retrieve user info after login: {e}", exc_info=True)
                self.user_info = None # Reset user_info if retrieval fails
        
        return self.is_authenticated

    async def get_my_followers(self) -> List[UserShort]:
        """
        Retrieves a list of my followers.
        Отримує список моїх підписників.
        """
        if not self.is_authenticated or not self.user_info:
            logger.warning("Not authenticated. Cannot get followers.")
            return []
        
        pk = self.user_info.pk
        followers = await self._api_call_wrapper(self.cl.user_followers, pk)
        return followers if followers else []

    async def get_my_following(self) -> List[UserShort]:
        """
        Retrieves a list of users I am following.
        Отримує список користувачів, на яких я підписана.
        """
        if not self.is_authenticated or not self.user_info:
            logger.warning("Not authenticated. Cannot get following.")
            return []
        
        pk = self.user_info.pk
        following = await self._api_call_wrapper(self.cl.user_following, pk)
        return following if following else []

    async def get_user_id_from_username(self, username: str) -> Optional[int]:
        """
        Retrieves the user ID (PK) from a given username.
        Отримує ID користувача (PK) за наданим іменем користувача.
        """
        user = await self._api_call_wrapper(self.cl.user_info_by_username, username)
        return user.pk if user else None

    async def get_user_info(self, user_id: int) -> Optional[UserShort]:
        """
        Retrieves user information by user ID.
        Отримує інформацію про користувача за ID користувача.
        """
        return await self._api_call_wrapper(self.cl.user_info, user_id)

    async def send_direct_message(self, text: str, user_ids: Union[List[int], int]) -> Optional[DirectMessage]:
        """
        Sends a direct message to one or more user IDs.
        Надсилає пряме повідомлення одному або декільком користувачам за ID.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot send direct message.")
            return None

        current_time = datetime.now()
        if self.last_dm_timestamp and (current_time - self.last_dm_timestamp) < self.dm_rate_limit_interval:
            remaining_time = self.dm_rate_limit_interval - (current_time - self.last_dm_timestamp)
            logger.warning(f"Rate limit for DMs. Waiting for {remaining_time.total_seconds():.2f} seconds.")
            await asyncio.sleep(remaining_time.total_seconds())

        if isinstance(user_ids, int):
            user_ids = [user_ids]
            
        message = await self._api_call_wrapper(self.cl.direct_send_text, user_ids, text)
        if message:
            self.last_dm_timestamp = datetime.now() # Update timestamp after successful DM
            logger.info(f"Direct message sent to {user_ids}: '{text[:50]}...'")
        return message

    async def get_direct_inbox(self) -> List[DirectThread]:
        """
        Retrieves direct inbox threads.
        Отримує гілки прямого вхідного повідомлення.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot get direct inbox.")
            return []
        inbox = await self._api_call_wrapper(self.cl.direct_inbox)
        return inbox.threads if inbox else []

    async def get_direct_thread_messages(self, thread_id: int) -> List[DirectMessage]:
        """
        Retrieves messages from a specific direct message thread.
        Отримує повідомлення з конкретної гілки прямого повідомлення.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot get direct thread messages.")
            return []
        thread = await self._api_call_wrapper(self.cl.direct_thread, thread_id)
        return thread.messages if thread else []

    async def mark_direct_message_as_seen(self, thread_id: int) -> bool:
        """
        Marks a direct message thread as seen.
        Позначає гілку прямого повідомлення як прочитану.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot mark message as seen.")
            return False
        
        # instagrapi versions might differ in method name
        if hasattr(self.cl, 'direct_send_seen'): # Newer instagrapi versions
            success = await self._api_call_wrapper(self.cl.direct_send_seen, thread_id)
            if success is not None: # direct_send_seen returns the status object
                logger.info(f"Sent 'seen' for DM thread {thread_id}.")
                return True
            return False
        elif hasattr(self.cl, 'direct_thread_mark_as_seen'): # Older instagrapi
            success = await self._api_call_wrapper(self.cl.direct_thread_mark_as_seen, thread_id)
            if success is not None: # Check if the call itself succeeded
                logger.info(f"Attempted to mark DM thread {thread_id} as seen (older method).")
                return True # Assume success if no error
            else:
                logger.info(f"Explicitly marking thread {thread_id} as seen not required or method not found in instagrapi version.")
            return True # Assume no action needed is a form of success

    async def upload_photo(self, path: str, caption: str) -> Optional[Media]:
        await human_like_delay(MIN_BASE_DELAY_SECONDS, MAX_BASE_DELAY_SECONDS * 2) # Longer delay for uploads
        return await self._api_call_wrapper(self.cl.photo_upload, path, caption=caption)

    async def upload_story(self, path: str, caption: Optional[str] = None) -> Optional[Story]:
        await human_like_delay(MIN_BASE_DELAY_SECONDS, MAX_BASE_DELAY_SECONDS * 1.5) # Longer delay for stories
        return await self._api_call_wrapper(self.cl.story_upload, path, caption=caption)

    async def get_media_by_user(self, user_id: int, amount: int = 20) -> List[Media]:
        """
        Retrieves a specified amount of media (posts) from a user.
        Отримує вказану кількість медіа (дописів) від користувача.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot get user media.")
            return []
        media_list = await self._api_call_wrapper(self.cl.user_medias, user_id, amount=amount)
        return media_list if media_list else []

    async def get_comments_on_media(self, media_id: int) -> List[Comment]:
        """
        Retrieves comments on a specific media item.
        Отримує коментарі до конкретного медіа-елемента.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot get comments.")
            return []
        comments = await self._api_call_wrapper(self.cl.media_comments, media_id)
        return comments if comments else []

    async def post_comment(self, media_id: int, text: str) -> Optional[Comment]:
        """
        Posts a comment on a specific media item.
        Публікує коментар до конкретного медіа-елемента.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot post comment.")
            return None
        return await self._api_call_wrapper(self.cl.media_comment, media_id, text)

    async def like_media(self, media_id: int) -> bool:
        """
        Likes a specific media item.
        Лайкає конкретний медіа-елемент.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot like media.")
            return False
        result = await self._api_call_wrapper(self.cl.media_like, media_id)
        return bool(result)

    async def unlike_media(self, media_id: int) -> bool:
        """
        Unlikes a specific media item.
        Відміняє лайк конкретного медіа-елемента.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot unlike media.")
            return False
        result = await self._api_call_wrapper(self.cl.media_unlike, media_id)
        return bool(result)

    async def follow_user(self, user_id: int) -> Optional[UserShort]:
        """
        Follows a user.
        Підписується на користувача.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot follow user.")
            return None
        return await self._api_call_wrapper(self.cl.user_follow, user_id)

    async def unfollow_user(self, user_id: int) -> Optional[UserShort]:
        """
        Unfollows a user.
        Відписується від користувача.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot unfollow user.")
            return None
        return await self._api_call_wrapper(self.cl.user_unfollow, user_id)

    async def get_last_n_direct_messages(self, user_id: int, n: int = 1) -> List[DirectMessage]:
        """
        Retrieves the last N direct messages from a specific user.
        Отримує останні N прямих повідомлень від конкретного користувача.
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Cannot retrieve DMs.")
            return []
        
        try:
            # Find the thread with the user
            inbox = await self._api_call_wrapper(self.cl.direct_inbox)
            if not inbox or not inbox.threads:
                return []
            
            target_thread = None
            for thread in inbox.threads:
                if any(u.pk == user_id for u in thread.users):
                    target_thread = thread
                    break
            
            if not target_thread:
                logger.info(f"No direct message thread found with user ID {user_id}.")
                return []

            # Retrieve messages from that thread
            thread_messages = await self._api_call_wrapper(self.cl.direct_thread, target_thread.id)
            if thread_messages and thread_messages.messages:
                # Filter out messages that are not from the target user or self, and take last N
                # Only include messages from the user_id or from Mista herself
                relevant_messages = [
                    msg for msg in thread_messages.messages
                    if (msg.user_id == user_id or msg.user_id == self.user_info.pk)
                ]
                return relevant_messages[-n:] # Return the last N messages
            return []
        except Exception as e:
            logger.error(f"Error retrieving last N direct messages for user {user_id}: {e}", exc_info=True)
            return []
