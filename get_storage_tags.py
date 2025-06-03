import hashlib
import hmac
import requests
import datetime
import json

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    return sign(kService, 'aws4_request')

def aws4_get(path, scp_ip, access_key, secret_key):
    method = 'GET'
    service = 'open-api'
    region = 'cn-south-1'
    endpoint = f'https://{scp_ip}{path}'
    content_type = 'application/json'

    t = datetime.datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')
    payload_hash = hashlib.sha256("".encode('utf-8')).hexdigest()

    canonical_headers = (
        f'content-type:{content_type}\n'
        f'host:{scp_ip}\n'
        f'x-amz-content-sha256:{payload_hash}\n'
        f'x-amz-date:{amz_date}\n'
    )
    signed_headers = 'content-type;host;x-amz-content-sha256;x-amz-date'

    canonical_request = f"{method}\n{path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n" + \
                     hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    signing_key = getSignatureKey(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    authorization_header = (
        f'{algorithm} Credential={access_key}/{credential_scope}, '
        f'SignedHeaders={signed_headers}, Signature={signature}'
    )

    headers = {
        'Content-Type': content_type,
        'X-Amz-Date': amz_date,
        'X-Amz-Content-Sha256': payload_hash,
        'Authorization': authorization_header
    }

    try:
        res = requests.get(endpoint, headers=headers, verify=False)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ GET request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def load_config():
    try:
        with open("terraform.tfvars") as f:
            config = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"')
            return config
    except Exception as e:
        print(f"❌ Error loading terraform.tfvars: {e}")
        return None

if __name__ == "__main__":
    config = load_config()
    if not config:
        print("❌ Failed to load terraform.tfvars")
        exit(1)

    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    scp_ip = config.get("scp_ip")

    if not all([access_key, secret_key, scp_ip]):
        print("❌ Missing configuration values")
        exit(1)

    print("📡 Fetching storage-tag list from SCP...")
    response = aws4_get("/janus/20180725/storage-tags", scp_ip, access_key, secret_key)
    if response and response.get('success'):
        print("\n✅ Storage Tags:")
        for tag in response.get('data', []):
            print(f"🗂️ ID: {tag.get('id')} | Name: {tag.get('name')}")
    else:
        print("\n❌ Failed to fetch storage-tag list")
