import os
import re
import json
import glob
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client
from pathlib import Path

"""
**FOR TRAINING DATASET**

Pipeline script for parsing, embedding, and uploading Jira user stories and Zephyr tests
into Supabase. In addition, for the embedded content, it uploads the data into a central 
"RAG Embeddings" table for applying RAG techniques later on.

TO DO: Automate the movement and parsing of wireframes from the bucket into it's appropriate table in 
the Supabase DB and embedding them into the RAG Embeddings table.
"""

# ||=============== Model & Data Paths ===============||

#Constructs the absolute path to the dataset-test-gen folder
SCRIPT_DIR = Path(__file__).resolve().parent  # Get the directory containing this script
PARENT_DIR = SCRIPT_DIR.parent  # Move up one level 
DATASET_DIR = PARENT_DIR / "data" / "training-data"  # Access a folder in the parent directory

load_dotenv(PARENT_DIR / ".env") # Load environment variables 

# Load embedding model
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024

RAG_TABLE = "RAG Embeddings"

# Load Supabase credentials 
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "YOUR_SERVICE_KEY")

# ||=============== Parsing ===============||

def parse_story(filepath):
    """Parses the story.md file into a python dictionary"""

    # Reads the the markdown file
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    def extract(header, text):
        """Extracts content after any header prefixed with # or ##"""
        pattern = rf"##\s*{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    # Captures everything after "Story:" and until the next new line
    top_line = re.search(r"^#\s*Story\s*:\s*(.*)", content, re.MULTILINE)

    # Capture and store the use case id and issue key which are stored on the first line and separated by '-'
    use_case_id, issue_key = "", ""
    if top_line:
        parts = top_line.group(1).split("—")
        if len(parts) == 2:
            use_case_id = parts[0].strip()
            issue_key = parts[1].strip()

    # returns all parsed data that will later be stored in the Supabase DB 
    return {
        "issue_key": issue_key,
        "use_case_id": use_case_id,
        "titre": extract("Titre", content),
        "statut_jira": extract("Statut Jira", content),
        "module": extract("Module", content),
        "description": extract("Description", content),
        "critères_acceptances": extract("Acceptance Criteria", content),
    }


def parse_tests(filepath):
    """Parses the tests_zephyr.json file into a list of python dictionaries"""

    # Reads the json file
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f) # Returns the parsed json as a dictionary using json.load()

    # Captures associated story key
    story_key = data["story_key"]

    rows = []

    # Captures the details within the listed tests under "testCases"
    for tc in data["testCases"]:
        rows.append({
            "test_key": tc["key"],
            "story_key": story_key,
            "name": tc["name"],
            "status": tc["status"],
            "objective": tc["objective"],
            "precondition": tc["precondition"],
            "folder": tc["folder"],
            "steps": tc["steps"],  # jsonb column takes the list directly
        })
    # Returns a list of all the dictionaries containing the parsed test details
    return rows

def parse_meta(filepath):
    """Parses meta.json into a python dictionary if present"""
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f) # Returns the parsed meta.json as a dictionary using json.load()
        except Exception as e:
            print(f"  Warning reading {filepath}: {e}")
    return {}

# ||=============== Embedding ===============||

def generate_embedding(model, text):
    """Embeds the given text using the provided model and returns a list of floats"""
    return model.encode(text, normalize_embeddings=True).tolist()

# ||=============== RAG Upload Helper ===============||

def upsert_rag_embedding(supabase, *, source_key, story_key, embedding, content=None, metadata=None):
    """Writes a single row into the central RAG Embeddings table"""
    supabase.table(RAG_TABLE).upsert({
        "source_key": source_key,
        "story_key": story_key,
        "embeddings": embedding,
        "content": content, # Changed according to if it's a story or test
        "metadata": metadata or {},
    }, on_conflict="source_key").execute()

# ||=============== Main ===============||

def main():
    """
        Pipeline path:
            - Parse Jira user story, Zephyr test, and wireframe files into python dictionaries
            - Upload the raw (un-embedded) rows into their own source tables
            - Generate embeddings and upload them into the central RAG Embeddings table
    """

    # Verify key isn't fallback default
    if SUPABASE_SERVICE_KEY == "YOUR_SERVICE_KEY":
        raise ValueError("SUPABASE_SERVICE_KEY was not loaded from .env! Check your .env file location.")

    # Load Qwen embedding model
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Connect to Supabase DB
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Find every use case (UC-XX) folder under the data directory
    uc_folders = sorted(
        d for d in glob.glob(os.path.join(DATASET_DIR, "UC-*")) if os.path.isdir(d)
    )

    print(f"Found {len(uc_folders)} use case folder(s): {[os.path.basename(d) for d in uc_folders]}")

    stories_inserted = 0
    tests_inserted = 0
    embeddings_inserted = 0
    errors = []

    # Iterates through every use case folder and parses the story.md and tests_zephyr.json files, uploads them 
    # to their respective tables, generates embeddings, and uploads them to the RAG Embeddings table.
    for uc_folder in uc_folders:
        uc_name = os.path.basename(uc_folder)
        print(f"\nProcessing {uc_name} :")

        meta_path = os.path.join(uc_folder, "meta.json")
        uc_meta = parse_meta(meta_path)

        # Searches for the story .md file and the tests_zephyr .json file in the use case folder
        md_files = glob.glob(os.path.join(uc_folder, "*.md"))
        json_files = glob.glob(os.path.join(uc_folder, "*tests_zephyr*.json"))

        # Throws a warning if either the story.md or tests_zephyr.json file is missing in the use case folder
        if not md_files:
            errors.append(f"{uc_name}: no .md file found")
            print(f"  WARNING: no .md file found in {uc_folder}")
        if not json_files:
            errors.append(f"{uc_name}: no .json file found")
            print(f"  WARNING: no .json file found in {uc_folder}")

        # Parse, upload, and embed stories
        for md_path in md_files:
            try:
                # Parses the story.md file
                story = parse_story(md_path)

                # Uploads the parsed story data into the "JIRA User Stories" table in Supabase, using the issue_key 
                # as the unique identifier for upsert operations
                supabase.table("JIRA User Stories").upsert(
                    story, on_conflict="issue_key"
                ).execute()
                stories_inserted += 1
                print(f"  Uploaded story {story['issue_key']}")

                # Selects the text to embed from the story
                text_to_embed = f"{story['titre']}\n{story['description']}\n{story['critères_acceptances']}"
                embedding = generate_embedding(model, text_to_embed)

                # Merges parsed story data with attributes from meta.json
                story_metadata = {
                    "source_table": "JIRA User Stories",
                    "module": story.get("module") or uc_meta.get("module"),
                    "statut_jira": story.get("statut_jira"),
                    "use_case_id": story.get("use_case_id") or uc_meta.get("id"),
                    "complexity": uc_meta.get("complexity"),
                    "mockup_ref": uc_meta.get("mockup_ref"),
                    "notes": uc_meta.get("notes"),
                    "zephyr_test_keys": uc_meta.get("zephyr_test_keys", []),
                }

                # Embeds the story into the RAG Embeddings table
                upsert_rag_embedding(
                    supabase,
                    source_key=story["issue_key"],
                    story_key=story["issue_key"],
                    embedding=embedding,
                    content=text_to_embed,
                    metadata=story_metadata,
                )
                embeddings_inserted += 1
                print(f"  Embedded story {story['issue_key']}")
            except Exception as e:
                errors.append(f"{uc_name}: story error - {e}")
                print(f"  ERROR parsing/uploading {md_path}: {e}")

        # Parse, upload, and embed tests
        for json_path in json_files:
            try:
                # Parses the tests_zephyr.json file
                test_rows = parse_tests(json_path)

                # Uploads each parsed test row into the "Zephyr Tests" table in Supabase, using the test_key as the unique 
                # identifier for upsert operations
                for row in test_rows:
                    supabase.table("Zephyr Tests").upsert(
                        row, on_conflict="test_key"
                    ).execute()
                    tests_inserted += 1

                    # Selects the text to embed from the test
                    steps_text = "\n".join(
                        f"{s.get('step', '')} -> {s.get('expected_result', '')}"
                        for s in row.get("steps", [])
                    )
                    text_to_embed = (
                        f"{row['name']}\n{row.get('objective', '')}\n"
                        f"{row.get('precondition', '')}\n{steps_text}"
                    )
                    embedding = generate_embedding(model, text_to_embed)

                    # Merges parsed test data with attributes from meta.json
                    test_metadata = {
                        "source_table": "Zephyr Tests",
                        "status": row.get("status"),
                        "folder": row.get("folder"),
                        "use_case_id": uc_meta.get("id"),
                        "complexity": uc_meta.get("complexity"),
                    }

                    # Embeds the test into the RAG Embeddings table
                    upsert_rag_embedding(
                        supabase,
                        source_key=row["test_key"],
                        story_key=row["story_key"],
                        embedding=embedding,
                        content=text_to_embed,
                        metadata=test_metadata,
                    )
                    embeddings_inserted += 1

                print(f"  Uploaded and embedded {len(test_rows)} tests from {os.path.basename(json_path)}")
            except Exception as e:
                errors.append(f"{uc_name}: test error - {e}")
                print(f"  ERROR parsing/uploading {json_path}: {e}")

    print(
        f"\nSUCCESS: {stories_inserted} stories, {tests_inserted} tests, "
        f"{embeddings_inserted} embeddings written to '{RAG_TABLE}'."
    )
    if errors:
        print(f"\n  {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()