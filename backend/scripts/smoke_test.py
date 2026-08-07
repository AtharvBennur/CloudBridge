import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5000"


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


status, login = req("POST", "/auth/login", {"email": "test@example.com", "password": "password123"})
print("login", status, bool(login.get("token")))
token = login.get("token")

status, conn = req(
    "POST",
    "/aws-connections",
    {"aws_account_id": "595529182661", "aws_region": "us-east-1"},
    token,
)
print("create conn", status, conn)
cid = conn.get("id")

if cid:
    status, cf = req("GET", f"/aws-connections/{cid}/cloudformation-template", token=token)
    print("cf template", status, cf.get("download_filename") if status == 200 else cf)

    status, validate = req("POST", f"/aws-connections/{cid}/validate", token=token)
    print("validate", status, validate)
