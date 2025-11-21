from flask import Flask, request, send_file, jsonify
from gtts import gTTS
from io import BytesIO
from pydub import AudioSegment, effects
import os

app = Flask(__name__)

def change_pitch(sound: AudioSegment, octaves=0.0):
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    pitched = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    return pitched.set_frame_rate(44100)

def change_speed(sound: AudioSegment, speed=1.0):
    return effects.speedup(sound, playback_speed=speed) if abs(speed-1.0)>0.01 else sound

PRESETS = {
  "deep_american": {"lang":"en","tld":"com","pitch_octaves":-0.28,"speed":0.92},
  "deep_calm": {"lang":"en","tld":"com","pitch_octaves":-0.35,"speed":0.9},
  "clear_neutral": {"lang":"en","tld":"co.uk","pitch_octaves":0.0,"speed":1.0},
  "english_female": {"lang":"en","tld":"co.uk","pitch_octaves":0.12,"speed":1.02},
  "hindi_male": {"lang":"hi","tld":"co.in","pitch_octaves":-0.05,"speed":1.0},
  "hindi_female": {"lang":"hi","tld":"co.in","pitch_octaves":0.15,"speed":1.03},
  "robotic": {"lang":"en","tld":"com","robotic":True},
  "fast_narrator": {"lang":"en","tld":"com","pitch_octaves":0.0,"speed":1.35},
  "mixed_deep": {"lang":"en","tld":"com","pitch_octaves":-0.2,"speed":0.95}
}

@app.route("/")
def index():
    return "TTS backend OK"

@app.route("/tts", methods=["POST"])
def tts():
    data = request.json or {}
    text = data.get("text","").strip()
    preset = data.get("preset","clear_neutral")
    fmt = data.get("format","mp3")

    if not text:
        return jsonify({"error":"No text provided"}), 400

    settings = PRESETS.get(preset, PRESETS["clear_neutral"])
    lang = settings.get("lang","en")
    tld = settings.get("tld","com")

    tts = gTTS(text=text, lang=lang, tld=tld)
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    sound = AudioSegment.from_file(buf, format="mp3")

    if settings.get("robotic"):
        sound = sound.low_pass_filter(3000).set_channels(1)
    else:
        octaves = settings.get("pitch_octaves", 0.0)
        if abs(octaves) > 0.001:
            sound = change_pitch(sound, octaves)
        speed = settings.get("speed", 1.0)
        if abs(speed-1.0) > 0.01:
            sound = change_speed(sound, speed)

    out = BytesIO()
    ext = "mp3"
    if fmt == "wav":
        sound.export(out, format="wav")
        mime = "audio/wav"
        ext = "wav"
    else:
        sound.export(out, format="mp3", bitrate="192k")
        mime = "audio/mpeg"
        ext = "mp3"
    out.seek(0)

    return send_file(out, as_attachment=True, download_name=f"tts.{ext}", mimetype=mime)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
