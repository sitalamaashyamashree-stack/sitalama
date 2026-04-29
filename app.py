from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import re
import os
import glob
import subprocess

app = Flask(__name__)
CORS(app)

def clear_files():
    for f in glob.glob("video.*"):
        try:
            os.remove(f)
        except:
            pass

@app.route("/")
def home():
    return "Backend Live"

@app.route("/convert", methods=["POST"])
def convert():

    try:
        data = request.get_json()
        url = data["url"]

        clear_files()

        # Google Drive Support
        if "drive.google.com" in url:

            match = re.search(r'/d/([^/]+)', url)

            if not match:
                return jsonify({"error":"Invalid Drive Link"}),400

            file_id = match.group(1)

            direct = f"https://drive.google.com/uc?export=download&id={file_id}"

            r = requests.get(direct, stream=True)

            with open("video.mxf", "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)

            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", "video.mxf",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "video.mp4"
            ])

            return send_file("video.mp4", as_attachment=True)

        # Other Links
        opts = {
            "format":"best",
            "outtmpl":"video.%(ext)s",
            "merge_output_format":"mp4"
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        return send_file("video.mp4", as_attachment=True)

    except Exception as e:
        return jsonify({"error":str(e)}),500

app.run(host="0.0.0.0", port=10000)
