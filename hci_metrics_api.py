@app.route("/api/metrics")
def hci_metrics():
    config = load_config()
    
    # เปลี่ยน method เป็น GET แบบใช้ AWS4 (ถ้าคุณมีฟังก์ชัน get แบบ AWS4)
    response = aws4_post(
        "/janus/20180725/hosts",     # ✅ แก้ path
        scp_ip=config["scp_ip"],
        access_key=config["access_key"],
        secret_key=config["secret_key"],
        payload={}                   # ไม่มี payload
    )

    if not response or "data" not in response:
        return jsonify([])

    # สร้าง metrics จาก response (อาจต้องเปลี่ยน field name ตามที่ response ส่งกลับมา)
    metrics = []
    for host in response["data"]:
        metrics.append({
            "host_name": host.get("name", "N/A"),
            "cpu_usage": host.get("cpu_usage", 0),
            "memory_usage": host.get("mem_usage", 0)
        })

    return jsonify(metrics)
