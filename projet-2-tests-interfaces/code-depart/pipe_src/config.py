import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Finds base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")