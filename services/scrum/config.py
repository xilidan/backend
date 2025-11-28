import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    API_VERSION = os.getenv("API_VERSION")
    BACKEND_API_URL = os.getenv("BACKEND_API_URL", "https://api.azed.kz/api/v1")
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "scrum_db")
    JIRA_API_URL = os.getenv("JIRA_API_URL","https://jira.azed.kz/api/jira")   

print(f"Loaded API Key: {Settings.AZURE_OPENAI_API_KEY[:5]}..." if Settings.AZURE_OPENAI_API_KEY else "API Key is None")

settings = Settings()
