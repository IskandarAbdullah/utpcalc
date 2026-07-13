import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'utp-mark-calculator-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///utp_marks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenRouter API (free models available)
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
    OPENROUTER_VISION_MODEL = os.environ.get('OPENROUTER_VISION_MODEL', 'meta-llama/llama-4-scout:free')

    # Fallback to Ollama if no OpenRouter key (for local dev)
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1')
    OLLAMA_VISION_MODEL = os.environ.get('OLLAMA_VISION_MODEL', 'llama3.2-vision')
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

    USE_CLOUD = bool(OPENROUTER_API_KEY)
