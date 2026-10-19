"""API client for Microtek (Deye OEM) Solar Inverter Web Interface."""

import asyncio
import base64
import json
import logging
import random
import re
from typing import Any, Dict, Optional

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


def _zero_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + b"\x00" * pad_len


def _aes_encrypt(plaintext: str, key_str: str) -> str:
    key = key_str.encode("utf-8")
    data = _zero_pad(plaintext.encode("utf-8"), 16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(key))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")


def _aes_decrypt(ciphertext_b64: str, key_str: str) -> str:
    key = key_str.encode("utf-8")
    clean = ciphertext_b64
    idx = clean.rfind("result_end")
    if idx != -1:
        clean = clean[:idx]
    clean = clean.strip()
    raw = base64.b64decode(clean)
    cipher = Cipher(algorithms.AES(key), modes.CBC(key))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(raw) + decryptor.finalize()
    return decrypted.decode("utf-8", errors="ignore").rstrip("\x00")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    start_tag = "json_start"
    end_tag = "json_end"
    start_idx = text.find(start_tag)
    end_idx = text.find(end_tag)
    if start_idx == -1 or end_idx == -1:
        return None
    json_str = text[start_idx + len(start_tag) : end_idx].strip()
    try:
        return json.loads(json_str)
    except Exception as err:
        _LOGGER.error("Failed to parse JSON: %s. Raw: %s", err, json_str)
        return None


STATIC_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqzhyBCTXdPrJ0coIrazG
n/cthPy+35Gp8RAbUahmatXowz1utkNYmunT4yIp74kk6Aw83mfgDr6+27/8ylGD
oafIrIiDK/A0OHaGOrVMSfH60t1RPcMD7QXFBRUSX5P8C5rYSt9ANloKJRScHn0R
RrkcfQ9eIkQ7xw3toP6l1u+bmQob8pnp9W3V0vbQkX66F/Cn8uwoyiHD4ou4zCZl
5yUDPxCCgyLw4NMUf/J0pIdw5Cbo51oBxn6LOMX6h5kP82TbyvHqyJRE9LPn295T
P1PL3QSHVqGXoBlXXnqK3OSwgD0SdywgsRYe4IdRiPKFJqmuq/GSlzV8AohqPzB9
twIDAQAB
-----END PUBLIC KEY-----"""


class MicrotekSolarApi:
    """Microtek solar logger API client."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Initialize API client."""
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        # Always use dedicated session with force_close=True for this embedded HTTP/1.0 server
        self._session: Optional[aiohttp.ClientSession] = None
        self._owns_session = True
        self._session_key: Optional[str] = None
        self._authenticated = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self._session

    async def close(self) -> None:
        """Close session if owned."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _raw_get(self, relative_path: str, retries: int = 3) -> str:
        """Perform raw GET request with retries."""
        url = f"http://{self.host}/{relative_path}"
        headers = {
            "User-Agent": "Mozilla/5.0 (HomeAssistant)",
            "Connection": "close",
        }
        for attempt in range(retries):
            try:
                session = await self._get_session()
                async with session.get(url, headers=headers) as resp:
                    return await resp.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug(
                    "Request to %s failed (attempt %d/%d): %s",
                    relative_path,
                    attempt + 1,
                    retries,
                    err,
                )
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(0.5)
        return ""

    async def async_authenticate(self) -> bool:
        """Exchange RSA/AES session key and log in."""
        _LOGGER.debug("Authenticating with Microtek inverter at %s", self.host)

        # 1. Fetch RSA Public Key or fallback to static key
        pem_bytes = STATIC_PUBLIC_KEY.encode()
        try:
            req_path = base64.b64encode(f"require.cgi?t={random.random()}".encode()).decode()
            resp_text = await self._raw_get(req_path)
            start = resp_text.find("-----BEGIN PUBLIC KEY-----")
            end = resp_text.find("-----END PUBLIC KEY-----")
            if start != -1 and end != -1:
                pem_bytes = resp_text[start : end + len("-----END PUBLIC KEY-----")].strip().encode()
        except Exception as err:
            _LOGGER.debug("Could not fetch fresh public key (%s), using fallback", err)

        public_key = serialization.load_pem_public_key(pem_bytes)

        # 2. Generate 16-digit AES session key
        session_key = str(random.randint(1000000000000000, 9999999999999999))
        enc_key = public_key.encrypt(session_key.encode("utf-8"), padding.PKCS1v15())
        enc_key_b64 = base64.b64encode(enc_key).decode("ascii")

        # 3. Send session key
        send_url = f"send.cgi?key={enc_key_b64}&t={random.random()}"
        send_path = base64.b64encode(send_url.encode()).decode()
        send_resp = await self._raw_get(send_path)
        if "set_success" not in send_resp and "result_end" not in send_resp:
            raise ConnectionError(f"Session key negotiation failed: {send_resp}")

        self._session_key = session_key

        # 4. Login
        await asyncio.sleep(0.2)
        login_url = (
            f"login.cgi?user={self.username}&password={self.password}&t={random.random()}"
        )
        login_path = _aes_encrypt(login_url, session_key)
        login_resp_raw = await self._raw_get(login_path)
        login_resp = _aes_decrypt(login_resp_raw, session_key)

        if "login_success" not in login_resp:
            raise PermissionError(f"Login failed on {self.host}. Check credentials.")

        self._authenticated = True
        _LOGGER.debug("Authentication successful with Microtek inverter")
        return True

    async def async_get_data(self) -> Dict[str, Any]:
        """Fetch status data, re-authenticating if needed."""
        if not self._authenticated or not self._session_key:
            await self.async_authenticate()

        status_url = f"status.cgi?t={random.random()}"
        status_path = _aes_encrypt(status_url, self._session_key)

        try:
            raw_resp = await self._raw_get(status_path)
            dec_resp = _aes_decrypt(raw_resp, self._session_key)
        except Exception as err:
            _LOGGER.warning("Error fetching status, attempting re-auth: %s", err)
            await self.async_authenticate()
            status_path = _aes_encrypt(status_url, self._session_key)
            raw_resp = await self._raw_get(status_path)
            dec_resp = _aes_decrypt(raw_resp, self._session_key)

        # Check for token timeout or invalid output
        if "token_timeout" in dec_resp or "json_start" not in dec_resp:
            _LOGGER.info("Session expired, re-authenticating...")
            await self.async_authenticate()
            status_path = _aes_encrypt(status_url, self._session_key)
            raw_resp = await self._raw_get(status_path)
            dec_resp = _aes_decrypt(raw_resp, self._session_key)

        parsed = _extract_json(dec_resp)
        if not parsed:
            raise ValueError(f"Invalid status response received: {dec_resp[:100]}")

        return parsed
