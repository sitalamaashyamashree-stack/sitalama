from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess
import os
import uuid
import requests

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def get_google_drive_direct(url):
    if "drive.google.com" in url and "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


@app.route("/")
def home():
    return "Server Running"


@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.get_json()
        video_url = data.get("url")

        if not video_url:
            return jsonify({"error": "No URL provided"}), 400

        video_url = get_google_drive_direct(video_url)

        input_file = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.input")
        output_file = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.mp4")

        r = requests.get(video_url, stream=True)
        if r.status_code != 200:
            return jsonify({"error": "Download failed"}), 400

        with open(input_file, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-c:v", "libx264",
            "-c:a", "aac",
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
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
