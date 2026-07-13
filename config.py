import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'utp-mark-calculator-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///utp_marks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Gemini API (using official SDK)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')

    # Fallback to Ollama if no Gemini key (for local dev)
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1')
    OLLAMA_VISION_MODEL = os.environ.get('OLLAMA_VISION_MODEL', 'llama3.2-vision')
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

    USE_CLOUD = bool(GEMINI_API_KEY)
