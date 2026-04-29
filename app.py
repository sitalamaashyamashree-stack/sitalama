from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests, re, os

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "Backend Live"

@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.get_json()
        url = data["url"]

        if "drive.google.com" in url:
            m = re.search(r'/d/([^/]+)', url)
            file_id = m.group(1)

            direct = f"https://drive.google.com/uc?export=download&id={file_id}"

            r = requests.get(direct, stream=True)

            with open("video.mp4","wb") as f:
                for chunk in r.iter_content(1024*1024):
                    f.write(chunk)

            return send_file("video.mp4", as_attachment=True)

        return jsonify({"error":"Only Google Drive supported now"}),400

    except Exception as e:
        return jsonify({"error":str(e)}),500

app.run(host="0.0.0.0", port=10000)
