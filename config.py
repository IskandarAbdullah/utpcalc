import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'utp-mark-calculator-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///utp_marks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Groq API (free cloud AI - no local GPU needed)
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
    GROQ_VISION_MODEL = os.environ.get('GROQ_VISION_MODEL', 'llama-3.2-11b-vision-preview')

    # Fallback to Ollama if no Groq key (for local dev)
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1')
    OLLAMA_VISION_MODEL = os.environ.get('OLLAMA_VISION_MODEL', 'llama3.2-vision')
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

    USE_GROQ = bool(GROQ_API_KEY)
