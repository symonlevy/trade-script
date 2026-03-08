from flask import Flask, request, jsonify
import os, shutil, subprocess, tempfile

app = Flask(__name__)

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

def run_cmd(cmd, cwd=None):
    proc = subprocess.run(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return proc.returncode, proc.stdout, proc.stderr

@app.route("/transcribe", methods=["POST"])
def transcribe():
    url = request.json.get("url", "").strip() if request.is_json else ""
    lang = request.json.get("lang", "he").strip() if request.is_json else "he"

    if not url:
        return jsonify({"ok": False, "error": "missing url"}), 400

    tmp_dir = tempfile.mkdtemp(prefix="yt_trans_")
    audio_path = os.path.join(tmp_dir, "audio.m4a")
    transcript_path = os.path.join(tmp_dir, "audio.txt")

    try:
        # 1) הורדת אודיו
        cmd_dl = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-x", "--audio-format", "m4a",
            "-o", audio_path,
            url
        ]
        rc, out, err = run_cmd(cmd_dl)
        if rc != 0:
            return jsonify({
                "ok": False,
                "step": "download",
                "error": f"yt-dlp failed (rc={rc})",
                "stderr": err[:400]
            }), 500

        # 2) תמלול עם whisper CLI
        cmd_whisper = [
            "whisper",
            audio_path,
            "--model", WHISPER_MODEL,
            "--language", lang,
            "--task", "transcribe",
            "--output_format", "txt",
            "--output_dir", tmp_dir
        ]
        rc, out, err = run_cmd(cmd_whisper)
        if rc != 0:
            return jsonify({
                "ok": False,
                "step": "whisper",
                "error": f"whisper failed (rc={rc})",
                "stderr": err[:400]
            }), 500

        if not os.path.exists(transcript_path):
            return jsonify({"ok": False, "error": "transcript file not found"}), 500

        with open(transcript_path, "r", encoding="utf-8") as f:
            text = " ".join(f.read().split())

        return jsonify({"ok": True, "text": text, "chars": len(text)})

    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

@app.route("/health")
def health():
    return jsonify({"ok": True, "status": "running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

