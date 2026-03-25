"""Shared HTTP helpers for Searcharr-nxg integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning


class IntegrationError(RuntimeError):
    """Raised when an upstream integration request fails."""


@dataclass
class HttpJsonClient:
    """Small JSON-over-HTTP helper with consistent error handling."""

    timeout_seconds: int = 15
    verify_ssl: Union[bool, str] = True

    def _prepare_request(self) -> None:
        if self.verify_ssl is False:
            disable_warnings(InsecureRequestWarning)

    def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            self._prepare_request()
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise IntegrationError(f"GET request failed for {url}: {exc}") from exc
        return response.json()

    def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            self._prepare_request()
            response = requests.post(
                url,
                headers=headers,
                json=json_body,
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise IntegrationError(f"POST request failed for {url}: {exc}") from exc
        return response.json()

    def put(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            self._prepare_request()
            response = requests.put(
                url,
                headers=headers,
                json=json_body,
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise IntegrationError(f"PUT request failed for {url}: {exc}") from exc
        if not response.content:
            return {}
        return response.json()
