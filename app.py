from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests
import subprocess
import os
import re
import glob
import uuid

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

PORT = int(os.environ.get("PORT", 10000))


# -----------------------------
# Helpers
# -----------------------------
def delete_temp():
    for f in glob.glob("input_*"):
        try:
            os.remove(f)
        except:
            pass

    for f in glob.glob("output_*"):
        try:
            os.remove(f)
        except:
            pass


def extract_drive_id(url):
    m1 = re.search(r"/d/([^/]+)", url)
    m2 = re.search(r"id=([^&]+)", url)

    if m1:
        return m1.group(1)
    if m2:
        return m2.group(1)

    return None


def download_drive_file(file_id, filename):
    session = requests.Session()

    URL = "https://drive.google.com/uc?export=download"

    response = session.get(URL, params={"id": file_id}, stream=True)

    token = None

    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            token = value

    if token:
        response = session.get(
            URL,
            params={"id": file_id, "confirm": token},
            stream=True
        )

    with open(filename, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return "Docker Video Converter Running"


@app.route("/convert", methods=["POST", "OPTIONS"])
def convert():
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        delete_temp()

        file_id = extract_drive_id(url)

        if not file_id:
            return jsonify({"error": "Invalid Google Drive link"}), 400

        uid = str(uuid.uuid4())[:8]

        input_file = f"input_{uid}.mxf"
        output_file = f"output_{uid}.mp4"

        # Download from Google Drive
        download_drive_file(file_id, input_file)

        # Convert with ffmpeg
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

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            return jsonify({
                "error": "FFmpeg failed",
                "details": result.stderr.decode(errors="ignore")
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
