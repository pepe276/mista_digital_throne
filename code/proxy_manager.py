# proxy_manager.py
# -*- coding: utf-8 -*-
import logging
import random
import asyncio
import time # Added time import for UrlProxyProvider
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

class ProxyProvider:
    """Abstract base class for proxy providers."""
    async def get_proxy(self) -> Optional[str]:
        raise NotImplementedError("The 'get_proxy' method must be implemented by subclasses.")

    async def report_unhealthy(self, proxy: str):
        """Report that a proxy is unhealthy or not working."""
        logger.warning(f"Proxy '{proxy}' reported as unhealthy. The proxy provider should handle this.")

class FileProxyProvider(ProxyProvider):
    """Proxy provider that reads proxies from a file."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.proxies: List[str] = []
        self._load_proxies()
        self.unhealthy_proxies: List[str] = []
        logger.info(f"FileProxyProvider initialized from file: {filepath}. Proxies found: {len(self.proxies)}")

    def _load_proxies(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.proxies = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except FileNotFoundError:
            logger.error(f"Proxy file not found: {self.filepath}")
            self.proxies = []
        except Exception as e:
            logger.error(f"Error loading proxies from file {self.filepath}: {e}")
            self.proxies = []

    async def get_proxy(self) -> Optional[str]:
        """Returns a random available proxy."""
        available_proxies = [p for p in self.proxies if p not in self.unhealthy_proxies]
        if not available_proxies and self.unhealthy_proxies:
            logger.warning("All proxies marked as unhealthy. Attempting to reset the list of unhealthy proxies.")
            self.unhealthy_proxies.clear()
            available_proxies = list(self.proxies) # Reset all proxies

        if available_proxies:
            return random.choice(available_proxies)
        logger.warning("No available proxies to use.")
        return None

    async def report_unhealthy(self, proxy: str):
        """Marks a proxy as unhealthy."""
        if proxy and proxy not in self.unhealthy_proxies:
            self.unhealthy_proxies.append(proxy)
            logger.warning(f"Proxy '{proxy}' added to unhealthy list.")

class UrlProxyProvider(ProxyProvider):
    """Proxy provider that loads proxies from a specified URL."""
    def __init__(self, url: str):
        self.url = url
        self.proxies: List[str] = []
        self.last_update = 0
        self.update_interval = 3600 # Update proxies every hour
        self.unhealthy_proxies: List[str] = []
        logger.info(f"UrlProxyProvider initialized from URL: {url}")

    async def _update_proxies_from_url(self):
        if time.time() - self.last_update < self.update_interval:
            return # Do not update too often

        logger.info(f"Updating proxy list from URL: {self.url}")
        try:
            # Stub for asynchronous HTTP request. In real code, this would be aiohttp or httpx
            # For demonstration, use a dummy delay and return an empty list.
            await asyncio.sleep(1) # Simulate network request
            # In a real application:
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(self.url)
            #     response.raise_for_status()
            #     new_proxies = [line.strip() for line in response.text.splitlines() if line.strip() and not line.strip().startswith('#')]
            #     self.proxies = new_proxies
            #     self.unhealthy_proxies.clear() # Reset unhealthy proxies on update
            #     self.last_update = time.time()
            #     logger.info(f"Updated proxy list from URL. Found: {len(self.proxies)}")
            # Temporarily, for stub:
            self.proxies = ["http://placeholder.proxy.com:8080"] # Example proxy
            self.unhealthy_proxies.clear()
            self.last_update = time.time()
            logger.warning("UrlProxyProvider is using dummy proxies. Implement real HTTP request.")

        except Exception as e:
            logger.error(f"Error updating proxies from URL {self.url}: {e}")

    async def get_proxy(self) -> Optional[str]:
        """Returns a random available proxy, updating the list as needed."""
        await self._update_proxies_from_url()
        available_proxies = [p for p in self.proxies if p not in self.unhealthy_proxies]
        if not available_proxies and self.unhealthy_proxies:
            logger.warning("All proxies from URL marked as unhealthy. Attempting to reset the list of unhealthy proxies.")
            self.unhealthy_proxies.clear()
            available_proxies = list(self.proxies) # Reset all proxies

        if available_proxies:
            return random.choice(available_proxies)
        logger.warning("No available proxies from URL to use.")
        return None

    async def report_unhealthy(self, proxy: str):
        """Marks a proxy as unhealthy."""
        if proxy and proxy not in self.unhealthy_proxies:
            self.unhealthy_proxies.append(proxy)
            logger.warning(f"Proxy '{proxy}' added to unhealthy list (from URL).")

class ProxyManager:
    """
    Manages a pool of proxies using various providers.
    Provides cyclic switching or selection of the best proxy.
    """
    def __init__(self, proxy_providers: Optional[List[ProxyProvider]] = None):
        self.proxy_providers = proxy_providers if proxy_providers is not None else []
        self.current_provider_index = 0
        logger.info(f"ProxyManager initialized with {len(self.proxy_providers)} proxy providers.")

    def add_provider(self, provider: ProxyProvider):
        """Adds a new proxy provider to the manager."""
        self.proxy_providers.append(provider)
        logger.info(f"Added new proxy provider: {type(provider).__name__}.")

    async def get_proxy(self) -> Optional[str]:
        """
        Attempts to get a proxy from the current provider,
        or switches to the next if the current one does not provide a proxy.
        """
        if not self.proxy_providers:
            logger.warning("ProxyManager: No available proxy providers.")
            return None

        # Try all providers in turn, starting with the current one
        for _ in range(len(self.proxy_providers)):
            provider = self.proxy_providers[self.current_provider_index]
            proxy = await provider.get_proxy()
            if proxy:
                logger.debug(f"ProxyManager: Got proxy '{proxy}' from {type(provider).__name__}.")
                return proxy
            
            logger.warning(f"ProxyManager: Current provider {type(provider).__name__} failed to provide a proxy. Switching to the next one.")
            self.current_provider_index = (self.current_provider_index + 1) % len(self.proxy_providers)

        logger.error("ProxyManager: All proxy providers failed to provide an available proxy.")
        return None

    async def report_unhealthy(self, proxy: str):
        """Reports an unhealthy proxy to the current proxy provider."""
        if self.proxy_providers:
            provider = self.proxy_providers[self.current_provider_index]
            await provider.report_unhealthy(proxy)
        else:
            logger.warning(f"ProxyManager: No providers to report unhealthy proxy: {proxy}.")
