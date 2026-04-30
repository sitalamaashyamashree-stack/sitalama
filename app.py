from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess
import os
import uuid
import requests

app = Flask(__name__)
CORS(app)

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


# 🔹 Convert Google Drive link → direct download
def get_drive_direct(url):
    if "drive.google.com" in url:
        if "file/d/" in url:
            file_id = url.split("file/d/")[1].split("/")[0]
        elif "id=" in url:
            file_id = url.split("id=")[1]
        else:
            return url
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


# 🔹 Download file properly (handles large Drive files)
def download_file(url, path):
    session = requests.Session()
    response = session.get(url, stream=True)

    # Handle Google confirm token
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            url = url + "&confirm=" + value
            response = session.get(url, stream=True)

    if response.status_code != 200:
        raise Exception("Download failed")

    with open(path, "wb") as f:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)


@app.route("/")
def home():
    return "Server running"


@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.get_json()
        video_url = data.get("url")

        if not video_url:
            return jsonify({"error": "No URL"}), 400

        video_url = get_drive_direct(video_url)

        input_file = f"{TEMP_DIR}/{uuid.uuid4()}.mxf"
        output_file = f"{TEMP_DIR}/{uuid.uuid4()}.mp4"

        # 🔽 Download
        download_file(video_url, input_file)

        # 🔄 Convert MXF → MP4
        cmd = [
            "ffmpeg",
            "-y",
            "-fflags", "+genpts",
            "-i", input_file,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-strict", "experimental",
            output_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({
                "error": "ffmpeg failed",
                "details": result.stderr
            }), 500

        return send_file(output_file, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
