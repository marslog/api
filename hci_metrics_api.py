from flask import Flask, jsonify
import json
from create_vm_aws4 import aws4_post, load_config

app = Flask(__name__)   # ✅ ต้องอยู่ก่อน @app.route

@app.route("/api/metrics")
def hci_metrics():
    config = load_config()
    response = aws4_post(
        "/janus/20180725/hosts",      # หรือ endpoint อื่นตาม API
        scp_ip=config["scp_ip"],
        access_key=config["access_key"],
        secret_key=config["secret_key"],
        payload={}
    )

    if not response or "data" not in response:
        return jsonify([])

    metrics = []
    for host in response["data"]:
        metrics.append({
            "host_name": host.get("name", "N/A"),
            "cpu_usage": host.get("cpu_usage", 0),
            "memory_usage": host.get("mem_usage", 0)
        })

    return jsonify(metrics)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
