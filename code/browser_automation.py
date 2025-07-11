import asyncio
from playwright.async_api import Playwright, async_playwright, expect, TimeoutError
from typing import Optional
import logging
import random
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

async def human_like_delay(min_delay: float = 1, max_delay: float = 3):
    """
    Introduces a human-like delay.
    """
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)
    logger.debug(f"Human-like delay: {delay:.2f} seconds.")

class BrowserAutomation:
    def __init__(self, headless: bool = True):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = headless
        logger.info(f"BrowserAutomation initialized with headless={self.headless}")

    async def launch_browser(self):
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        storage_state_path = os.path.join(os.path.dirname(__file__), "storage_state.json")
        if os.path.exists(storage_state_path):
            self.context = await self.browser.new_context(storage_state=storage_state_path)
            logger.info(f"Loaded session state from {storage_state_path}")
        else:
            self.context = await self.browser.new_context()
            logger.warning(f"No storage_state.json found at {storage_state_path}. Starting fresh context.")

        self.page = await self.context.new_page()
        logger.info("Browser launched and new page created.")

    async def navigate(self, url: str):
        if self.page is None:
            logger.error("No page available. Call launch_browser first.")
            return
        await self.page.goto(url)
        logger.info(f"Navigated to {url}")

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            logger.info("Browser closed.")
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Playwright stopped.")

    async def get_page_content(self) -> str:
        if self.page is None:
            logger.error("No page available. Call launch_browser first.")
            return ""
        return await self.page.content()

    async def take_screenshot(self, path: str):
        if self.page is None:
            logger.error("No page available. Call launch_browser first.")
            return
        await self.page.screenshot(path=path)
        logger.info(f"Screenshot saved to {path}")

    async def save_page_content(self, filename: str):
        if self.page is None:
            logger.error("No page available to save content.")
            return
        try:
            content = await self.page.content()
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Page content saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save page content to {filename}: {e}")

    async def get_user_profile_info(self, username: str) -> Optional[dict]:
        if self.page is None:
            logger.error("No page available. Call launch_browser first.")
            return None

        logger.info(f"Navigating to {username}'s profile...")
        await self.navigate(f"https://www.instagram.com/{username}/")

        try:
            # Wait for a common element on a profile page, e.g., the username in the title
            await self.page.wait_for_selector("h2", timeout=15000) # Adjust selector as needed
            logger.info(f"Profile page for {username} loaded.")

            # Extract information (these selectors are placeholders and need to be verified)
            followers_count = await self.page.locator("a[href*='/followers'] span").text_content()
            following_count = await self.page.locator("a[href*='/following'] span").text_content()
            posts_count = await self.page.locator("li span[class*='g47']").text_content()

            return {
                "username": username,
                "followers": followers_count,
                "following": following_count,
                "posts": posts_count
            }
        except TimeoutError:
            logger.error(f"Timeout waiting for profile page elements for {username}.")
            await self.save_page_content(f"instagram_profile_load_timeout_{username}.html")
            return None
        except Exception as e:
            logger.error(f"Failed to get profile info for {username}: {e}", exc_info=True)
            await self.save_page_content(f"instagram_profile_error_{username}.html")
            return None

    async def login(self, username, password, session_id: Optional[str] = None) -> bool:
        if self.page is None:
            logger.error("No page available. Call launch_browser first.")
            return False

        logger.info(f"Attempting to log in as {username}...")

        # If storage_state is loaded, we assume login is not needed
        # We will navigate to Instagram homepage and check if we are logged in
        await self.navigate("https://www.instagram.com/")
        await self.take_screenshot("instagram_after_storage_state_load.png") # Take screenshot here
        try:
            await self.page.wait_for_selector('[aria-label="Home"]', timeout=15000) # Shorter timeout for selector if already on main domain
            logger.info(f"Successfully logged in as {username} using saved session.")
            return True
        except TimeoutError:
            logger.warning("Timeout waiting for Home icon after loading session. Session might be invalid or expired.")
            logger.error(f"Login failed for {username}: Session invalid or expired.")
            return False

# Example usage (for testing purposes)
async def main():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    INSTAGRAM_SESSIONID = os.getenv("SESSIONID")

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("Error: INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not found in .env file.")
        return

    automation = BrowserAutomation(headless=False) # Set to False to see the browser
    try:
        await automation.launch_browser()
        
        if await automation.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSIONID):
            print(f"Successfully logged in as {INSTAGRAM_USERNAME}. Taking screenshot...")
            # After successful login, take a screenshot
            await automation.take_screenshot("instagram_after_login_attempt.png")
            print("Screenshot of page after login attempt taken: instagram_after_login_attempt.png")

            # Get user profile info
            profile_info = await automation.get_user_profile_info(INSTAGRAM_USERNAME)
            if profile_info:
                print(f"Profile Info for {INSTAGRAM_USERNAME}: {profile_info}")
            else:
                print(f"Failed to retrieve profile info for {INSTAGRAM_USERNAME}.")
        else:
            print("Login failed.")

    finally:
        await automation.close_browser()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())