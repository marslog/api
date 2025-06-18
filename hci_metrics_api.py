from flask import Flask, jsonify
import json
from create_vm_aws4 import aws4_post, load_config

app = Flask(__name__)

@app.route("/api/metrics")
def hci_metrics():
    config = load_config()
    payload = {}
    response = aws4_post(
        "/janus/20180725/servers/list",
        scp_ip=config["scp_ip"],
        access_key=config["access_key"],
        secret_key=config["secret_key"],
        payload=payload
    )

    if not response or "data" not in response:
        return jsonify([])

    metrics = []
    for vm in response["data"].get("data", []):
        metrics.append({
            "name": vm["name"],
            "cpu": vm.get("cpu_usage", 0),
            "memory": vm.get("mem_usage", 0)
        })

    return jsonify(metrics)
