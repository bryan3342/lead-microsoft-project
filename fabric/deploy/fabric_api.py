"""Thin REST client for Azure Resource Manager, Fabric and Power BI.

Authenticates with whoever is signed in to the Azure CLI, so no secrets are stored anywhere.
"""
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ARM = "https://management.azure.com"
FABRIC = "https://api.fabric.microsoft.com/v1"
POWERBI = "https://api.powerbi.com/v1.0/myorg"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
_AUDIENCE = {
    ARM: "https://management.azure.com",
    FABRIC: "https://api.fabric.microsoft.com",
    POWERBI: "https://analysis.windows.net/powerbi/api",
    ONELAKE: "https://storage.azure.com",
}
TOKEN_TTL_SECONDS = 30 * 60  # az tokens last about an hour; refresh well before that


class ApiError(RuntimeError):
    def __init__(self, status, url, body):
        super().__init__(f"HTTP {status} from {url}: {body}")
        self.status = status


def az(*args: str) -> str:
    exe = shutil.which("az")
    if not exe:
        sys.exit("Azure CLI not found. Install it from https://aka.ms/installazurecli and run: az login")
    result = subprocess.run([exe, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"az {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


class Client:
    def __init__(self, log=print):
        self._tokens = {}
        self.log = log

    def _token(self, base: str) -> str:
        cached = self._tokens.get(base)
        if not cached or time.time() - cached[1] > TOKEN_TTL_SECONDS:
            token = az("account", "get-access-token", "--resource", _AUDIENCE[base], "--query", "accessToken", "-o", "tsv")
            cached = self._tokens[base] = (token, time.time())
        return cached[0]

    def request(self, method: str, url: str, body=None):
        """Return (status, headers, parsed JSON or None). Retries throttling; raises ApiError on failure."""
        base = next(b for b in _AUDIENCE if url.startswith(b))
        data = None if body is None else json.dumps(body).encode()
        for _ in range(8):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self._token(base)}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read()
                    return resp.status, resp.headers, json.loads(raw) if raw.strip() else None
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
                if e.code == 429:
                    time.sleep(int(e.headers.get("Retry-After", "30")))
                    continue
                raise ApiError(e.code, url, text) from None
        raise ApiError(429, url, "still throttled after retries")

    def upload(self, workspace_id: str, lakehouse_id: str, path: str, data: bytes):
        """Write a file under the lakehouse's Files area, replacing any existing copy."""
        url = f"{ONELAKE}/{workspace_id}/{lakehouse_id}/Files/{path}"
        for method, query, body in (("PUT", "?resource=file", b""),
                                    ("PATCH", "?action=append&position=0", data),
                                    ("PATCH", f"?action=flush&position={len(data)}", b"")):
            req = urllib.request.Request(url + query, data=body, method=method, headers={
                "Authorization": f"Bearer {self._token(ONELAKE)}", "x-ms-version": "2023-11-03",
                "Content-Type": "application/octet-stream"})
            try:
                urllib.request.urlopen(req, timeout=300).close()
            except urllib.error.HTTPError as e:
                raise ApiError(e.code, url, e.read().decode(errors="replace")) from None

    def download(self, workspace_id: str, lakehouse_id: str, path: str) -> bytes:
        """Read a file from the lakehouse's Files area."""
        url = f"{ONELAKE}/{workspace_id}/{lakehouse_id}/Files/{path}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token(ONELAKE)}", "x-ms-version": "2023-11-03"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, url, e.read().decode(errors="replace")) from None

    def get(self, url):
        return self.request("GET", url)[2]

    def wait_operation(self, status, headers, body):
        """Follow a Fabric long-running operation to completion and return its result, if any."""
        op = headers.get("x-ms-operation-id")
        if status != 202 or not op:
            return body
        while True:
            time.sleep(int(headers.get("Retry-After", "5")))
            state = self.get(f"{FABRIC}/operations/{op}")
            if state["status"] == "Succeeded":
                try:
                    return self.get(f"{FABRIC}/operations/{op}/result")
                except ApiError as e:
                    if e.status in (400, 404):  # operations such as updateDefinition have no result
                        return None
                    raise
            if state["status"] in ("Failed", "Undefined"):
                raise RuntimeError(f"Fabric operation failed: {json.dumps(state.get('error', state))}")

    def fabric(self, method, path, body=None):
        return self.wait_operation(*self.request(method, f"{FABRIC}{path}", body))

    def list_all(self, path):
        url, items = f"{FABRIC}{path}", []
        while url:
            page = self.get(url)
            items += page.get("value", [])
            url = page.get("continuationUri")
        return items
