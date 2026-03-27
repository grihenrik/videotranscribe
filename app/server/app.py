from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)  # This will allow the extension to call the backend

@app.route('/transcribe', methods=['POST'])
def transcribe_video():
    """
    This endpoint receives a video URL and returns a mock transcription.
    In a real application, this is where you would call the YouTube API 
    and your transcription model.
    """
    data = request.get_json()
    video_url = data.get('videoUrl')

    if not video_url:
        return jsonify({"error": "videoUrl is required"}), 400

    print(f"Received request to transcribe: {video_url}")

    # Simulate a long-running transcription process
    time.sleep(3)

    # Mock transcription result
    mock_transcription = "Hello, this is a mock transcription of the video. In a real application, this text would be the actual transcribed content from the video."

    return jsonify({"transcription": mock_transcription})

if __name__ == '__main__':
    app.run(port=5050, debug=True)
