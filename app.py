from flask import Flask, request, send_file
from flask_cors import CORS
import yt_dlp
import glob, os

app = Flask(__name__)
CORS(app)

@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    url = data['url']

    for f in glob.glob('video.*'):
        try:
            os.remove(f)
        except:
            pass

    opts = {
        'format':'best',
        'outtmpl':'video.%(ext)s',
        'merge_output_format':'mp4'
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return send_file('video.mp4', as_attachment=True)

app.run(host='0.0.0.0', port=10000)
