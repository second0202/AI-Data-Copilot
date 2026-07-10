from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AI Data Copilot"
    VERSION: str = "0.1.0"

    # LLM Settings
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4-turbo-preview"

    # Storage Settings
    DATABASE_URL: str = "sqlite:///./data/ai_data_copilot.db"
    DUCKDB_PATH: str = "./data/analytics.duckdb"
    VECTOR_DB_PATH: str = "./data/vector_db"
    PORT: int = 8000

settings = Settings()
