from dotenv import load_dotenv
import os
import json
import yaml
import subprocess
from supabase import create_client, Client

"""
This script is designed to fine-tune the Qwen model using QLoRA for generating UI/UX unit tests from Jira user stories,
Balsamiq wirefrmes and Zephyr test cases.

Steps:

1. Load raw data from Supabase tables, including Jira user stories, Balsamiq wireframes, and Zephyr test cases.
2. Format the data into a structure suitable for VLM training, including multi-modal prompts with images and text.
3. Apply LoRA configuration for efficient fine-tuning.
4. Define training parameters 
5. Load and execute the Qwen model and tokenizer in 4-bit precision
6. Save the trained model and LoRA adapters for inference.
""" 

load_dotenv()

# ||=============== Model & Data Paths ===============||

MODEL_NAME = "mlx-community/Qwen2.5-VL-7B-Instruct-4bit" # mlx-community allows us run and fine-tune Qwen model locally on Mac 
DATA_DIR = "./data" # Root directory for storing formatted training data and other artifacts
BASE_IMAGES_DIR = os.path.join(DATA_DIR, "wireframe_images")  # Directory storing the downloaded wireframe images
ADAPTER_DIR = "./adapters"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "YOUR_SERVICE_KEY")
BUCKET_NAME = "balsamiq_wireframes"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Table mapping per split
SPLIT_CONFIGS = {
    "train": {
        "stories": "JIRA User Stories",
        "wireframes": "Balsamiq Wireframes",
        "tests": "Zephyr Tests",
        "frames_folder": "training_frames",
    },
    "validation": {
        "stories": "JIRA User Stories Validation",
        "wireframes": "Balsamiq Wireframes Validation",
        "tests": "Zephyr Tests Validation",
        "frames_folder": "validation_frames",
    },
}

# ||=============== Load and Format Dataset ===============||
"""Load dataset from local or remote source, and prepare for training"""

def load_raw_data(split="train"):
    """"Load raw data from Supabase tables and return as a list of dictionaries"""

    # Check initially if the directory exists, if not create it
    os.makedirs(BASE_IMAGES_DIR, exist_ok=True) 
    os.makedirs(DATA_DIR, exist_ok=True)

    config = SPLIT_CONFIGS[split]
    frames_dir_name = config["frames_folder"]

    print("Loading raw data from Supabase...")

    # Load raw data from Supabase tables according to the split config
    response = (
        supabase.table(config["stories"])
        .select(f"*, {config['wireframes']}(*), {config['tests']}(*)")
        .execute()
    )

    raw_stories = response.data
    loaded_data = []

    # Capture the needed elements of each story
    for story in raw_stories:
        # Skip stories that do not have an issue_key, as this is essential for connecting stories to their wireframes and tests.
        if not story.get("issue_key"):
            print("Warning: Skipping raw story record with missing issue_key.")
            continue

        story_key = story.get("issue_key")
        story_title = story.get("titre")
        story_status = story.get("statut_jira")
        story_module = story.get("module")
        story_description = story.get("description")
        acceptance_criteria = story.get("critières_acceptances")

        # Create a dedicated directory per use case / story key
        story_image_dir = os.path.join(BASE_IMAGES_DIR, frames_dir_name, story_key)
        os.makedirs(story_image_dir, exist_ok=True)
        
        # Locate the media files and capture the needed elements of each wireframe
        wireframes = []
        wireframe_records = story.get(config["wireframes"], [])
        for frame in wireframe_records:
            folder_path = frame.get("wireframe_path")

            if folder_path:
                clean_folder = folder_path.strip("/")
                raw_file_list = supabase.storage.from_(BUCKET_NAME).list(clean_folder)

                # Ensure raw_file_list is a valid list before sorting
                if not isinstance(raw_file_list, list):
                    continue

                # Sort files alphabetically so UI sequence (e.g. step_01, step_02) is preserved
                sorted_files = sorted(raw_file_list, key=lambda x: x.get("name", ""))
                for file in sorted_files:
                    file_name = file.get("name")
                    if file_name and file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                        remote_file_path = f"{clean_folder}/{file_name}"
                        local_file_path = os.path.join(story_image_dir, file_name)

                         # Download image to local disk cache if not already present
                        if not os.path.exists(local_file_path):
                            image_bytes = supabase.storage.from_(BUCKET_NAME).download(remote_file_path)
                            with open(local_file_path, "wb") as f:
                                f.write(image_bytes)

                        wireframes.append({
                            "frame_id": frame.get("id"),
                            "file_name": file_name,
                            "local_path": local_file_path  # Saved for VLM input
                        })

        # Capture the needed elements of each test
        zephyr_tests = []
        test_records = story.get(config["tests"], [])
        for test in test_records:
            zephyr_tests.append({
                "test_id": test.get("id"),
                "test_key": test.get("test_key"),
                "test_name": test.get("name"),
                "test_objective": test.get("objective"),
                "test_precondition": test.get("precondition"),
                "test_folder": test.get("folder"),
                "test_steps": test.get("steps")
            })

        # Append the story and its associated wireframes and tests to the loaded_data list
        loaded_data.append({
            "story_key": story_key,
            "story_title": story_title,
            "story_status": story_status,
            "story_module": story_module,
            "story_description": story_description,
            "acceptance_criteria": acceptance_criteria,
            "wireframes": wireframes,
            "zephyr_tests": zephyr_tests
        })

    return loaded_data

def format_data_for_vlm(loaded_data, split = "train", output_dir = DATA_DIR):
    """Format the raw directories as jsonl and return train.jsonl for VLM training."""

    formatted_data = []

    for item in loaded_data:
        # The story_key is essential for linking the story to its wireframes and tests. If it's missing, we skip this record.
        if not item.get("story_key"):
            print(f"Warning: Skipping malformed record with missing story key.")
            continue

        # Capture the wireframes stored in the local disk cache. This will be the visual input for the VLM training.
        image_paths = [
            frame["local_path"] 
            for frame in item.get("wireframes", []) 
            if "local_path" in frame
        ]

        # Build the user prompt text for the VLM training including the story details. 
        # This will be the textual input for the VLM training.
        user_prompt_text = (
            f"Generate unit tests for the following Jira User Story:\n"
            f"Key: {item.get('story_key')}\n" # Can't be NULL, so no default value needed
            f"Module: {item.get('story_module', 'N/A')}\n"
            f"Title: {item.get('story_title', '')}\n"
            f"Status: {item.get('story_status', '')}\n"
            f"Description: {item.get('story_description', '')}\n"
            f"Acceptance Criteria: {item.get('acceptance_criteria', '')}"
        )

        # Built the muilt-media prompt for the VLM training. 
        # This includes both the visual input (images) and the textual input (user prompt).
        user_content = []
        for img_path in image_paths:
            user_content.append({"type": "image", "image": img_path})
        user_content.append({"type": "text", "text": user_prompt_text})    

        test_entries = []
        for test in item.get("zephyr_tests", []):
            # Skip tests that do not have a test_key, as this is essential for differentiating tests.
            if not test.get("test_key"):
                continue

            steps_json = json.dumps(test.get("test_steps", []))
            test_entries.append(
                f"Test Key: {test.get('test_key')}\n"
                f"Test Name: {test.get('test_name', '')}\n"
                f"Objective: {test.get('test_objective', '')}\n"
                f"Precondition: {test.get('test_precondition', '')}\n"
                f"Folder: {test.get('test_folder', '')}\n"
                f"Steps: {steps_json}"
            )

        assistant_response_text = "\n\n---\n\n".join(test_entries)

        # Skip stories that do not have associated Zephyr test cases
        if not assistant_response_text.strip():
            continue

        # Assemble mlx-vlm training data structure
        sample = {
            "images": image_paths,
            "messages": [
                {
                    "role": "user",
                 "content": user_content
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": assistant_response_text
                        }
                    ]    
                }
            ]
        }  
        formatted_data.append(sample)

    # Save the formatted data to appropriate '.jsonl' file accoriding to the use of the 'split' flag
    os.makedirs(output_dir, exist_ok=True)    

    filename = "train.jsonl" if split == "train" else "valid.jsonl"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        for entry in formatted_data:
            f.write(json.dumps(entry) + "\n")

    print(f"Formatted [{split}] data saved to {filename} for VLM training.")

# ||=============== Apply LoRA Configuration ===============||
"""Define elements such as rank (r), alpha, dropout, and set target_modules"""

LORA_CONFIG = {
    "fine_tune_type": "lora",
    "lora_parameters": {
        "keys": [ # Layers to inject rank adapters into
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj"
        ],
        "rank": 16,
        "alpha": 32, # Scaling factor for LoRA
        "dropout": 0.10, # Regularization to prevent overfitting      
    }
}

# ||=============== Apply Training Configuration ===============||
"""Define training parameters such as learning rate, batch size, epochs, and optimizer"""

TRAINING_CONFIG = {
    "train": True,
    "iters": 60, # ~3-4 epochs 
    "batch_size": 1, # 1 story per batch
    "val_batches": 5, # 5 validation batches per evaluation
    "grad_checkpoint": True, # Conserves VRAM
    "learning_rate": 1e-4,
    "warmup": 5,                  
    "lr_schedule": "cosine",
    "steps_per_eval": 10, 
    "steps_per_report": 5,
    "save_every": 20, # Save checkpoints every 20 steps
    "max_seq_length": 4096 # Context window token cap
}

# ||=============== Execute Training ===============||
"""Run the training loop, monitor loss, and save checkpoints"""

def train_model():
    """Train the Qwen model using the formatted dataset and LoRA configuration"""

    # Combine all configurations into a single dictionary for training
    full_config = {
        "model_name": MODEL_NAME,
        "data": DATA_DIR,
        "adapter_path": ADAPTER_DIR,
        **TRAINING_CONFIG,
        **LORA_CONFIG
    }

    # MLX expects a YAML configuration file for training, so we write the combined config to a YAML file.
    config_file = "lora_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(full_config, f, default_flow_style=False)

    print(f"Generated runtime config at {config_file}")

    # Launch MLX LoRA training loop
    subprocess.run(
        ["python", "-m", "mlx_vlm.lora", "--config", config_file],
        check=True
    )
    
# ||=============== Save Trained Model ===============||
"""Save LoRA adapters and optimized model for inference somewhere within the project directory or a specified path."""

def save_trained_model():
    """Save the trained LoRA adapters and optimized model for inference"""

    adapter_weights = os.path.join(ADAPTER_DIR, "adapters.safetensors")
    adapter_config = os.path.join(ADAPTER_DIR, "adapter_config.json")

    if os.path.exists(adapter_weights) and os.path.exists(adapter_config):
        print("SUCCESS: Fine-tuning completed!")
        print(f"    Adapter weights saved to: {adapter_weights}")
        print(f"    Adapter config saved to:  {adapter_config}")
    else:
        print("ERROR: Fine-tuning did not complete successfully. Check training logs for issues.")

if __name__ == "__main__":
    # Fetch & format Training split -> data/train.jsonl
    train_data = load_raw_data(split="train")
    format_data_for_vlm(train_data, split="train")

    # Fetch & format Validation split -> data/valid.jsonl
    val_data = load_raw_data(split="validation")
    format_data_for_vlm(val_data, split="validation")

    # Launch training
    train_model()
    save_trained_model()