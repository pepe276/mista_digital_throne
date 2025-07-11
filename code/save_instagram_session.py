import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def save_session_state():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False) # Launch a visible browser
        context = await browser.new_context()
        page = await context.new_page()

        logger.info("Navigating to Instagram login page. Please log in manually.")
        await page.goto("https://www.instagram.com/accounts/login/")

        # Wait for the user to manually log in.
        # You can adjust this wait time or add a more sophisticated check
        # like waiting for a specific element on the logged-in page.
        try:
            await page.wait_for_url("https://www.instagram.com/", timeout=60000) # Wait up to 60 seconds for login
            logger.info("Successfully logged in manually. Saving session state...")
        except Exception as e:
            logger.error(f"Manual login timed out or failed: {e}. Please ensure you log in within the timeout period.")
            await browser.close()
            return

        # Save the storage state
        storage_state_path = os.path.join(os.path.dirname(__file__), "storage_state.json")
        await context.storage_state(path=storage_state_path)
        logger.info(f"Session state saved to {storage_state_path}")

        await browser.close()
        logger.info("Browser closed.")

if __name__ == "__main__":
    asyncio.run(save_session_state())