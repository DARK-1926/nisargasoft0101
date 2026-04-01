from __future__ import annotations

import logging
import random

from scrapy.downloadermiddlewares.retry import get_retry_request


class RandomizedProxyMiddleware:
    def __init__(self, proxies: list[str], user_agents: list[str], crawler=None) -> None:
        self.proxies = proxies
        self.user_agents = user_agents
        self.crawler = crawler
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            proxies=crawler.settings.getlist("ROTATING_PROXY_LIST"),
            user_agents=crawler.settings.getlist("USER_AGENT_POOL"),
            crawler=crawler,
        )

    def process_request(self, request):
        if self.user_agents:
            request.headers["User-Agent"] = random.choice(self.user_agents)
        request.headers["Accept-Language"] = "en-IN,en;q=0.9"

        location_profile = request.meta.get("location_profile")
        if location_profile is not None:
            request.headers["X-Forwarded-For"] = location_profile.x_forwarded_for

        if self.proxies:
            request.meta["proxy"] = random.choice(self.proxies)

    def process_exception(self, request, exception):
        self.logger.warning("proxy_failure url=%s error=%s", request.url, repr(exception))
        spider = getattr(self.crawler, "spider", None)
        if spider is None:
            return None
        return get_retry_request(request, spider=spider, reason=f"proxy_failure:{exception}")
