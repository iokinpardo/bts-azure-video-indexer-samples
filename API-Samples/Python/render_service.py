"""FastAPI helper service for invoking Azure Video Indexer from Render.com.

The service exposes simple endpoints that wrap Azure Video Indexer operations
so you can upload videos or query their insights without running the samples on
localhost. It relies on the API key (primary/secondary) flow and keeps access
tokens cached for you.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl


class UploadUrlRequest(BaseModel):
    """Input payload for uploading a video by referencing an external URL."""

    name: str
    video_url: HttpUrl
    description: Optional[str] = ""
    privacy: str = "private"
    wait_for_index: bool = False
    include_index_payload: bool = False
    poll_timeout_seconds: Optional[int] = None
    poll_interval_seconds: Optional[int] = None
    language: str = "English"


class VideoIndexerApi:
    """Lightweight wrapper around the Video Indexer REST API using API keys."""

    def __init__(self) -> None:
        self.account_id = self._require_env("VI_ACCOUNT_ID")
        self.location = self._require_env("VI_LOCATION")
        self.subscription_key = self._require_env("VI_SUBSCRIPTION_KEY")
        self.api_endpoint = os.getenv("VI_API_ENDPOINT", "https://api.videoindexer.ai").rstrip("/")
        self.default_language = os.getenv("VI_DEFAULT_LANGUAGE", "English")
        self.default_timeout = int(os.getenv("VI_WAIT_TIMEOUT_SECONDS", "900"))
        self.default_interval = int(os.getenv("VI_POLL_INTERVAL_SECONDS", "10"))
        self.token_ttl = int(os.getenv("VI_TOKEN_TTL_SECONDS", "3300"))
        self._cached_token: Optional[str] = None
        self._token_expiration = 0.0

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Environment variable {name} is required for render_service.")
        return value

    def _headers(self) -> Dict[str, str]:
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}

    def _token_valid(self) -> bool:
        return bool(self._cached_token) and time.time() < self._token_expiration

    def _parse_token_response(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text.strip()

        if isinstance(payload, dict):
            token = payload.get("accessToken")
        else:
            token = str(payload).strip('"')

        if not token:
            raise ValueError("Video Indexer did not return an access token.")

        return token

    def get_access_token(self, allow_edit: bool = True) -> str:
        if self._token_valid():
            return self._cached_token or ""

        url = f"{self.api_endpoint}/Auth/{self.location}/Accounts/{self.account_id}/AccessToken"
        params = {"allowEdit": str(allow_edit).lower()}

        response = requests.get(url, headers=self._headers(), params=params, timeout=30)
        response.raise_for_status()

        token = self._parse_token_response(response)
        self._cached_token = token
        self._token_expiration = time.time() + self.token_ttl
        return token

    def upload_video_from_url(self, payload: UploadUrlRequest) -> Dict[str, Any]:
        token = self.get_access_token(allow_edit=True)
        url = f"{self.api_endpoint}/{self.location}/Accounts/{self.account_id}/Videos"
        params: Dict[str, Any] = {
            "accessToken": token,
            "name": payload.name,
            "description": payload.description,
            "privacy": payload.privacy,
            "videoUrl": str(payload.video_url),
        }

        response = requests.post(url, params=params, timeout=120)
        response.raise_for_status()

        video_id = response.json().get("id")
        if not video_id:
            raise ValueError("Upload response did not include a video ID.")

        result: Dict[str, Any] = {"videoId": video_id, "state": response.json().get("state", "Uploaded")}

        if payload.wait_for_index:
            index_payload = self.wait_for_index(
                video_id=video_id,
                language=payload.language or self.default_language,
                timeout_seconds=payload.poll_timeout_seconds,
                interval_seconds=payload.poll_interval_seconds,
            )
            result["state"] = index_payload.get("state")
            if payload.include_index_payload:
                result["index"] = index_payload

        return result

    def wait_for_index(
        self,
        video_id: str,
        language: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        interval_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        timeout = timeout_seconds or self.default_timeout
        interval = interval_seconds or self.default_interval
        language_to_use = language or self.default_language
        deadline = time.time() + timeout

        latest_payload: Dict[str, Any] = {}
        while time.time() < deadline:
            latest_payload = self.get_video_index(video_id, language_to_use)
            state = latest_payload.get("state")
            if state in {"Processed", "Failed"}:
                return latest_payload
            time.sleep(interval)

        return latest_payload

    def get_video_index(self, video_id: str, language: Optional[str] = None) -> Dict[str, Any]:
        token = self.get_access_token(allow_edit=False)
        language_to_use = language or self.default_language

        url = f"{self.api_endpoint}/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"
        params = {"accessToken": token, "language": language_to_use}

        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()


video_indexer_api = VideoIndexerApi()
app = FastAPI(
    title="Azure Video Indexer helper",
    description="Simple wrapper for Azure Video Indexer so it can run on Render.com",
    version="1.0.0",
)


def _translate_error(error: Exception) -> HTTPException:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        detail = error.response.text or str(error)
        return HTTPException(status_code=error.response.status_code, detail=detail)
    return HTTPException(status_code=400, detail=str(error))


@app.get("/healthz")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/videos/url")
def upload_video(payload: UploadUrlRequest) -> Dict[str, Any]:
    try:
        return video_indexer_api.upload_video_from_url(payload)
    except Exception as exc:  # noqa: BLE001 - surface detailed error messages via HTTPException
        raise _translate_error(exc) from exc


@app.get("/videos/{video_id}")
def get_video_index(video_id: str, language: Optional[str] = None) -> Dict[str, Any]:
    try:
        return video_indexer_api.get_video_index(video_id, language)
    except Exception as exc:  # noqa: BLE001
        raise _translate_error(exc) from exc
