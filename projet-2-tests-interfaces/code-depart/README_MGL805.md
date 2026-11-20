# Jira/Zephyr → Supabase RAG & Fine-Tuning Pipeline

This project parses Jira user stories, Zephyr test cases, and Balsamiq
wireframes, uploads them to Supabase, generates embeddings for a RAG
("RAG Embeddings") table, and fine-tunes a Qwen VLM on the resulting
dataset.

## 1. Prerequisites

-   Python 3.10+ (project was built against modern versions of `torch`,
    `transformers`, and `sentence-transformers` --- see
    `requirements.txt`)
-   A Supabase project with a service-role key
-   macOS with Apple Silicon if you plan to run `fine_tuning_qwen.py`
    (it uses `mlx-community` / `mlx_vlm` for local fine-tuning)

## 2. Installation

``` bash
# from the project root
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

> `mlx_vlm` (used by `fine_tuning_qwen.py` for LoRA training) is not
> listed in `requirements.txt` and is only available on macOS/Apple
> Silicon. Install it separately if you intend to run fine-tuning:
>
> ``` bash
> pip install mlx-vlm
> ```

## 3. Environment variables and Supabase setup

Each student team should create and use **its own Supabase project**.
The original MiBioKey Supabase credentials are **not
distributed** with this repository.

A copy/export of the reference database may be provided separately so
that a team can restore the required schema and project data into its
own Supabase environment. Supabase Storage objects (including Balsamiq
wireframe images) must be transferred separately from the PostgreSQL
database when applicable.

Copy `.env.example` to `.env` at the project root and fill in the values
for **your team's Supabase project**:

``` env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_KEY=
```

-   `SUPABASE_URL`: URL of the team's Supabase project.
-   `SUPABASE_SERVICE_KEY`: service-role key used by the
    ingestion/fine-tuning scripts when privileged database access is
    required. **Never commit or share this key.**
-   `SUPABASE_KEY`: key expected by `pipe_src/config.py`. Use the key
    appropriate to the team's implementation and access policies.

The pipeline scripts resolve `PARENT_DIR = SCRIPT_DIR.parent` and load
`.env` from the project root. `fine_tuning_qwen.py` calls
`load_dotenv()` without an explicit path, so run it from the project
root (or export the variables in the shell).

The repository intentionally contains only `.env.example`; the real
`.env` must remain local and is excluded by `.gitignore`.

> **Security:** never publish a real Supabase service-role key on
> Moodle, Git, Teams, email, or in source code. Each team is responsible
> for its own credentials.

## 4. Expected data layout

The embedding pipelines look for **use case folders** named `UC-*`
inside a data directory, each containing:

    data/
    ├── training_data/              # embedding_valid_pipeline.py --split train
    │   └── UC-01/
    │       ├── story.md            # any *.md file
    │       ├── tests_zephyr.json   # any *tests_zephyr*.json file
    │       └── meta.json           # optional
    ├── validation_data/             # embedding_valid_pipeline.py --split validation
    │   └── UC-02/
    │       ├── story.md
    │       ├── tests_zephyr.json
    │       └── meta.json

-   `embedding_pipeline.py` (older, train-only script) expects this
    instead: `PARENT_DIR / "data" / "training-data"` (note the hyphen,
    not underscore). Prefer `embedding_valid_pipeline.py`, which
    supersedes it and supports both splits.

### `story.md` format

    # Story: UC-01 — PROJ-123

    ## Titre
    ...

    ## Statut Jira
    ...

    ## Module
    ...

    ## Description
    ...

    ## Acceptance Criteria
    ...

### `tests_zephyr.json` format

``` json
{
  "story_key": "PROJ-123",
  "testCases": [
    {
      "key": "PROJ-T1",
      "name": "...",
      "status": "...",
      "objective": "...",
      "precondition": "...",
      "folder": "...",
      "steps": [
        {"step": "...", "expected_result": "..."}
      ]
    }
  ]
}
```

### `meta.json` (optional)

Any extra metadata you want merged into the embedding row, e.g. `id`,
`complexity`, `mockup_ref`, `notes`, `zephyr_test_keys`.

## 5. Supabase tables

Make sure the following tables exist before running the pipeline:

  -----------------------------------------------------------------------
  Table                            Used for
  -------------------------------- --------------------------------------
  `JIRA User Stories`              Training stories

  `Zephyr Tests`                   Training tests

  `Validation JIRA User Stories`   Validation stories

  `Validation Zephyr Tests`        Validation tests

  `RAG Embeddings`                 Embedded content (train split only)

  `Balsamiq Wireframes`            Wireframe metadata, used by
                                   fine-tuning
  -----------------------------------------------------------------------

`RAG Embeddings` needs at least: `source_key` (unique/conflict key),
`story_key`, `embeddings` (vector, dimension **1024** to match
`Qwen/Qwen3-Embedding-0.6B`), `content`, `metadata` (jsonb).

## 6. Running the ingestion pipeline

``` bash
# Ingest + embed the training split only
python embedding_valid_pipeline.py --split train

# Ingest the validation split (uploaded raw, not embedded)
python embedding_valid_pipeline.py --split validation

# Do both in one run
python embedding_valid_pipeline.py --split all
```

Notes: - Only the `train` split downloads the
`Qwen/Qwen3-Embedding-0.6B` model and writes to `RAG Embeddings`;
`validation` only uploads raw rows. - The script upserts on `issue_key`
/ `test_key` / `source_key`, so re-running it is safe. - Missing `.md`
or `tests_zephyr.json` files in a `UC-*` folder are logged as
warnings/errors and do not stop the run; a summary of all errors prints
at the end.

## 7. Fine-tuning

Once training and validation data exist in Supabase (including uploaded
wireframe images in the `balsamiq_wireframes` storage bucket):

``` bash
python fine_tuning_qwen.py
```

This will: 1. Pull stories + linked wireframes + linked Zephyr tests
from Supabase for both splits, downloading wireframe images into
`./data/wireframe_images/{training_frames,validation_frames}/<story_key>/`.
2. Format everything into `data/train.jsonl` and `data/valid.jsonl` for
`mlx_vlm`. 3. Write a `lora_config.yaml` runtime config and launch
`python -m mlx_vlm.lora --config lora_config.yaml`. 4. Report whether
`adapters/adapters.safetensors` and `adapters/adapter_config.json` were
produced.

Adjust `LORA_CONFIG` and `TRAINING_CONFIG` in `fine_tuning_qwen.py` to
change rank/alpha/dropout, learning rate, batch size, iterations, etc.

## 8. MGL805 handoff

This repository contains source code and configuration examples, but
**no real Supabase credentials**.

The original LoRA adapters are not included. The previous fine-tuning
run was performed only once and without the validation dataset; the
resulting adapter files are no longer available. If the fine-tuning
approach is retained, the team should therefore rerun the training and
evaluate the resulting model using an appropriate validation protocol.

The current project should be treated as a prototype to continue rather
than as a production-ready end-to-end application.

## 9. Known gaps / things to double check before relying on this

-   `utils.py` imports `pipe_src as config`, but the config module here
    is `config.py` at the project root --- update that import (or your
    package layout) before using `derive_endpoint_type`.
-   `main.py` is currently empty; there is no single entry point that
    runs ingestion + fine-tuning end-to-end.
-   Wireframe ingestion/embedding into `RAG Embeddings` is a documented
    TODO in both embedding pipeline scripts --- wireframes are only
    consumed later, during fine-tuning.
