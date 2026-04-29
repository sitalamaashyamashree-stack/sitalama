from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests
import re
import os
import subprocess
import glob

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 10000))


def clean_files():
    for f in glob.glob("input.*"):
        try:
            os.remove(f)
        except:
            pass

    for f in glob.glob("output.*"):
        try:
            os.remove(f)
        except:
            pass


@app.route("/")
def home():
    return "MXF to MP4 Backend Live"


@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.get_json()
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        clean_files()

        # Google Drive file id detect
        file_id = None

        m1 = re.search(r"/d/([^/]+)", url)
        m2 = re.search(r"id=([^&]+)", url)

        if m1:
            file_id = m1.group(1)
        elif m2:
            file_id = m2.group(1)

        if not file_id:
            return jsonify({"error": "Invalid Google Drive Link"}), 400

        # direct download link
        direct = f"https://drive.google.com/uc?export=download&id={file_id}"

        # download source file
        r = requests.get(direct, stream=True)

        if r.status_code != 200:
            return jsonify({"error": "Unable to download file"}), 400

        with open("input.mxf", "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        # convert to mp4 using ffmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-i", "input.mxf",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "output.mp4"
        ]

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if process.returncode != 0:
            return jsonify({
                "error": "FFmpeg conversion failed",
                "details": process.stderr.decode("utf-8", errors="ignore")
            }), 500

        return send_file(
            "output.mp4",
            as_attachment=True,
            download_name="video.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
