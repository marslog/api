import hashlib
import hmac
import requests
import datetime
import json
from pprint import pprint

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    return sign(kService, 'aws4_request')

def aws4_post(path, scp_ip, access_key, secret_key, payload):
    method = 'POST'
    service = 'open-api'
    region = 'cn-south-1'
    endpoint = f'https://{scp_ip}{path}'
    content_type = 'application/json'

    t = datetime.datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    request_body = json.dumps(payload)
    payload_hash = hashlib.sha256(request_body.encode('utf-8')).hexdigest()

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
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

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
        res = requests.post(endpoint, headers=headers, data=request_body, verify=False)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ POST request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
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
        print(f"Error loading config: {str(e)}")
        return None

def generate_vm_payload():
    az_id = "d25b387b-ecb5-44f3-8e17-9c81516e208f"
    image_id = "5624ccc9-5c2b-4f1e-9c64-f001e6099591"  # ✅ Windows 10 image ID
    vpc_id = "bcab8abd-6689-43c7-9ba3-5d445925ca16"
    subnet_id = "7ad463da-d3e6-471f-ac18-8475f59d24e6"
    vif_id = "vif-00112233445566778899"  # ⚠️ ต้องแทนที่ด้วยค่า VIF จริงที่ระบบอนุญาต
    storage_tag_id = "8a34ef9a-8be3-40f3-b5a4-b8ef68e79db2"

    return {
        "az_id": az_id,
        "location": {"id": "cluster"},
        "storage_tag_id": storage_tag_id,
        "image_id": image_id,
        "cores": 2,
        "sockets": 1,
        "memory_mb": 4096,
        "count": 1,
        "name": "Terraform_Windows10",
        "disks": [{
            "type": "derive_disk",
            "size_mb": 81920
        }],
        "networks": [{
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "vif_id": vif_id,
            "connect": 1,
            "model": "virtio"
        }],
        "power_on": 1
    }

def write_payload_to_file(payload, filename="payload.json"):
    try:
        with open(filename, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n✅ {filename} created successfully.")
    except IOError as e:
        print(f"\n❌ Failed to write payload to file {filename}: {e}")

if __name__ == "__main__":
    config = load_config()
    if not config:
        print("Failed to load configuration. Please check terraform.tfvars file.")
        exit(1)

    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    scp_ip = config.get("scp_ip")

    if not all([access_key, secret_key, scp_ip]):
        print("Missing required configuration in terraform.tfvars")
        exit(1)

    vm_payload = generate_vm_payload()
    write_payload_to_file(vm_payload)

    print("\n--- Creating VM ---")
    response = aws4_post("/janus/20180725/servers", scp_ip, access_key, secret_key, vm_payload)
    if response:
        print("\n✅ VM Created Successfully:")
        print(json.dumps(response, indent=2))
    else:
        print("\n❌ VM creation failed.")
