from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests
import subprocess
import os
import re
import uuid
import tempfile

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 10000"))


# ------------------------
# Home
# ------------------------
@app.route("/")
def home():
    return "Video Converter Running"


# ------------------------
# Convert Route
# ------------------------
@app.route("/convert", methods=["POST", "OPTIONS"])
def convert():

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "No URL"}), 400

        # ---------- Extract Google Drive ID ----------
        file_id = None

        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if m:
            file_id = m.group(1)

        if not file_id:
            m = re.search(r"id=([a-zA-Z0-9_-]+)", url)
            if m:
                file_id = m.group(1)

        if not file_id:
            return jsonify({"error": "Invalid Drive link"}), 400

        # ---------- Temp Files ----------
        uid = str(uuid.uuid4())[:8]

        input_file = f"/tmp/input_{uid}.mxf"
        output_file = f"/tmp/output_{uid}.mp4"

        # ---------- Download from Drive ----------
        session = requests.Session()

        base = "https://drive.google.com/uc?export=download"

        r = session.get(base, params={"id": file_id}, stream=True)

        token = None
        for k, v in r.cookies.items():
            if "download_warning" in k:
                token = v

        if token:
            r = session.get(
                base,
                params={"id": file_id, "confirm": token},
                stream=True
            )

        with open(input_file, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        # ---------- Convert ----------
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if process.returncode != 0:
            return jsonify({
                "error": "ffmpeg failed",
                "details": process.stderr.decode(errors="ignore")
            }), 500

        return send_file(
            output_file,
            as_attachment=True,
            download_name="video.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
