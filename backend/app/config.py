"""Application configuration loaded from environment variables."""

import socket
from functools import lru_cache
from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_host_to_ip(url: str) -> str:
    """Resolve hostname in URL to IP so IPv6-only hosts work on Windows (getaddrinfo fix)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host or host.replace(".", "").replace(":", "").isdigit():
            return url  # already IP or no host
        # Prefer IPv6 (Supabase often has AAAA only); then IPv4
        for family in (socket.AF_INET6, socket.AF_INET):
            try:
                infos = socket.getaddrinfo(host, parsed.port or 5432, family, socket.SOCK_STREAM)
                if not infos:
                    continue
                addr = infos[0][4][0]
                if ":" in addr:
                    addr = f"[{addr}]"
                new_netloc = (parsed.netloc.replace(host, addr, 1) if host in parsed.netloc
                              else f"{parsed.username}:{parsed.password}@{addr}:{parsed.port or 5432}")
                return urlunparse((
                    parsed.scheme,
                    new_netloc,
                    parsed.path or "",
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                ))
            except (socket.gaierror, OSError):
                continue
    except Exception:
        pass
    return url


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    openai_api_key: str
    openai_max_concurrent: int = 5

    @property
    def async_database_url(self) -> str:
        """Ensure URL uses asyncpg driver, strip unsupported query params (e.g. pgbouncer), resolve host if needed."""
        url = self.database_url.strip().strip('"').strip("'")
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg doesn't accept ?pgbouncer=true; strip query string for the connection
        parsed = urlparse(url)
        if parsed.query:
            url = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "", "", "", ""))
        return _resolve_host_to_ip(url)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
