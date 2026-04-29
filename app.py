from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests
import subprocess
import os
import re
import uuid

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

PORT = int(os.environ.get("PORT", 10000))


# -----------------------------
# Home Route
# -----------------------------
@app.route("/")
def home():
    return "Video Converter Backend Running"


# -----------------------------
# Convert Route
# -----------------------------
@app.route("/convert", methods=["POST", "OPTIONS"])
def convert():

    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # -----------------------------
        # Extract Google Drive File ID
        # -----------------------------
        file_id = None

        m1 = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if m1:
            file_id = m1.group(1)

        if not file_id:
            m2 = re.search(r"id=([a-zA-Z0-9_-]+)", url)
            if m2:
                file_id = m2.group(1)

        if not file_id:
            return jsonify({"error": "Invalid Google Drive link"}), 400

        # -----------------------------
        # Temp filenames
        # -----------------------------
        uid = str(uuid.uuid4())[:8]

        input_file = f"/tmp/input_{uid}.mxf"
        output_file = f"/tmp/output_{uid}.mp4"

        # -----------------------------
        # Download file from Google Drive
        # -----------------------------
        session = requests.Session()

        base_url = "https://drive.google.com/uc?export=download"

        response = session.get(base_url, params={"id": file_id}, stream=True)

        token = None
        for key, value in response.cookies.items():
            if "download_warning" in key:
                token = value

        if token:
            response = session.get(
                base_url,
                params={
                    "id": file_id,
                    "confirm": token
                },
                stream=True
            )

        with open(input_file, "wb") as f:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        # -----------------------------
        # Convert with FFmpeg
        # -----------------------------
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output_file
        ]

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if process.returncode != 0:
            return jsonify({
                "error": "FFmpeg conversion failed",
                "details": process.stderr.decode(errors="ignore")
            }), 500

        # -----------------------------
        # Send MP4 file
        # -----------------------------
        return send_file(
            output_file,
            as_attachment=True,
            download_name="video.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
