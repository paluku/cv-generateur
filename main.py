import os
import uuid
import subprocess
from pathlib import Path

import whisper
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from xml.sax.saxutils import escape


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    "mp3", "wav", "m4a", "aac", "ogg", "flac",
    "mp4", "mkv", "avi", "mov", "webm", "mpeg", "mpg"
}

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 Go

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


print("Chargement du modèle Whisper...")
model = whisper.load_model("small")
print("Modèle Whisper chargé.")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def extract_audio(video_path, audio_path):
    """
    Convertit une vidéo/audio en WAV mono 16 kHz avec FFmpeg.
    """
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Erreur FFmpeg :\n" + result.stderr[-3000:]
        )


def create_txt(text, output_path):
    output_path.write_text(text, encoding="utf-8")


def create_pdf(text, output_path, title="Transcription"):
    styles = getSampleStyleSheet()

    body_style = styles["BodyText"]
    body_style.fontName = "Helvetica"
    body_style.fontSize = 10
    body_style.leading = 15
    body_style.alignment = TA_LEFT

    title_style = styles["Title"]

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    story = [
        Paragraph(escape(title), title_style),
        Spacer(1, 20),
    ]
    # Découpe en paragraphes pour rendre le PDF plus lisible.
    paragraphs = text.split("\n")

    for paragraph in paragraphs:
        if paragraph.strip():
            story.append(
                Paragraph(
                    escape(paragraph.strip()),
                    body_style
                )
            )
            story.append(Spacer(1, 8))

    document.build(story)


@app.route("/")
def index():
    return render_template("transcription.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "Aucun fichier envoyé."
        }), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({
            "success": False,
            "error": "Aucun fichier sélectionné."
        }), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({
            "success": False,
            "error": "Format de fichier non supporté."
        }), 400

    language = request.form.get("language", "").strip()

    job_id = uuid.uuid4().hex

    original_name = secure_filename(uploaded_file.filename)
    extension = Path(original_name).suffix.lower()

    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    audio_path = UPLOAD_DIR / f"{job_id}.wav"

    txt_path = OUTPUT_DIR / f"{job_id}.txt"
    pdf_path = OUTPUT_DIR / f"{job_id}.pdf"

    try:
        uploaded_file.save(input_path)

        # Conversion en audio WAV.
        extract_audio(input_path, audio_path)

        # Options Whisper.
        options = {
            "task": "transcribe",
            "fp16": False,
        }

        if language:
            options["language"] = language

        result = model.transcribe(
            str(audio_path),
            **options
        )

        text = result.get("text", "").strip()

        if not text:
            raise RuntimeError(
                "Aucun texte n'a pu être détecté dans le fichier."
            )

        create_txt(text, txt_path)
        create_pdf(text, pdf_path)

        return jsonify({
            "success": True,
            "text": text,
            "txt_url": f"/download/txt/{job_id}",
            "pdf_url": f"/download/pdf/{job_id}",
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:
        # Nettoyage des fichiers temporaires.
        for path in [input_path, audio_path]:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass


@app.route("/download/txt/<job_id>")
def download_txt(job_id):
    path = OUTPUT_DIR / f"{job_id}.txt"

    if not path.exists():
        return "Fichier introuvable.", 404

    return send_file(
        path,
        as_attachment=True,
        download_name="transcription.txt",
        mimetype="text/plain; charset=utf-8",
    )


@app.route("/download/pdf/<job_id>")
def download_pdf(job_id):
    path = OUTPUT_DIR / f"{job_id}.pdf"

    if not path.exists():
        return "Fichier introuvable.", 404

    return send_file(
        path,
        as_attachment=True,
        download_name="transcription.pdf",
        mimetype="application/pdf",
    )


@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "success": False,
        "error": "Fichier trop volumineux. Taille maximale : 2 Go."
    }), 413


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )