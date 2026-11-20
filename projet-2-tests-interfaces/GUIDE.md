# Guide du projet 2 : agent de tests d'interfaces utilisateurs

Ce guide explique comment installer le code de départ du projet 2, créer votre propre base Supabase, ingérer des données d'exemple et comprendre l'état exact du code. L'énoncé du travail est dans [`ENONCE.md`](ENONCE.md).

Le code de départ a été écrit par Andrew Phillips à l'été 2026. Il prépare des données Jira (récits utilisateurs), Zephyr (cas de test) et Balsamiq (maquettes), calcule des plongements vectoriels stockés avec pgvector dans Supabase et contient un script d'affinage (fine-tuning) d'un modèle Qwen multimodal pour générer des cas de test. C'est un **moteur à compléter**, pas encore un agent : le pipeline d'inférence et de RAG n'existe pas, et l'affinage n'a été exécuté qu'une fois, sans jeu de validation ; ses adaptateurs ne sont plus disponibles.

**Conventions.** Les commandes sont écrites pour un terminal Unix (Terminal de macOS, Linux ou WSL 2 sous Windows), sans l'invite : copiez-les une ligne à la fois. Sauf indication contraire, exécutez-les depuis le dossier `projet-2-tests-interfaces/code-depart`.

## 1. Contenu du dossier

| Chemin | Contenu |
|---|---|
| `code-depart/embedding_script/embedding_valid_pipeline.py` | Ingestion des récits et des cas de test dans Supabase, et plongements du jeu d'entraînement dans `RAG Embeddings` |
| `code-depart/embedding_script/embedding_pipeline.py` | Ancienne version, entraînement seulement ; ne plus l'utiliser |
| `code-depart/fine_tuning_src/fine_tuning_qwen.py` | Extraction depuis Supabase, mise en forme JSONL et affinage LoRA avec `mlx_vlm` (Mac Apple Silicon) |
| `code-depart/pipe_src/` | Début d'un pipeline (`config.py`, `utils.py`) ; `main.py` est vide |
| `code-depart/README_MGL805.md` | Le README d'origine d'Andrew, en anglais |
| `schema.sql` | Schéma Supabase reconstitué à partir du code (le schéma d'origine n'était pas fourni) |
| `exemple-donnees/` | Un cas d'utilisation fictif complet (UC-00), dans le format attendu par le code |

Les données réelles du projet d'origine (16 cas d'utilisation, 86 cas de test Zephyr et leurs maquettes) ne sont pas publiées dans ce site ; voir la section 8.

## 2. Prérequis

- Python 3.10 ou plus récent ;
- un compte [Supabase](https://supabase.com) (le forfait gratuit suffit) et un projet créé par votre équipe ;
- environ 5 Go d'espace disque pour PyTorch et le modèle de plongements `Qwen/Qwen3-Embedding-0.6B`, téléchargé automatiquement à la première exécution ;
- pour l'affinage seulement : un Mac Apple Silicon et `mlx-vlm` ; le modèle `Qwen2.5-VL-7B-Instruct-4bit` demande beaucoup de mémoire, prévoyez 16 Go ou plus et ne tentez pas l'affinage sur un Mac de 8 Go.

## 3. Installation

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-2-tests-interfaces/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

L'installation est longue, car `requirements.txt` épingle PyTorch, Transformers et plusieurs bibliothèques qui ne servent pas toutes (par exemple `openai`, `google-genai`, `dashscope`). Alléger ce fichier fait partie du travail.

## 4. Créer votre base Supabase

1. Dans Supabase, créez un projet pour votre équipe.
2. Ouvrez **SQL Editor**, collez le contenu de `../schema.sql` et exécutez-le. Il active l'extension `vector`, crée les tables d'entraînement, de validation et `RAG Embeddings` (vecteurs de 1024 dimensions), un index HNSW et une fonction de recherche `match_rag_embeddings` pour le futur pipeline de RAG.
3. Ouvrez **Storage** et créez un compartiment nommé `balsamiq_wireframes` (utilisé par le script d'affinage).
4. Ouvrez **Project Settings, API** et notez l'URL du projet et la clé secrète (service role).
5. Créez le fichier `.env` à partir du modèle et remplissez-le :

```
cp .env.example .env
open -e .env
```

```
SUPABASE_URL=https://<votre-projet>.supabase.co
SUPABASE_SERVICE_KEY=<clé secrète du projet>
SUPABASE_KEY=<même clé, ou la clé publique selon votre usage>
```

Le fichier `.env` est exclu de Git par `.gitignore`. **Ne publiez jamais la clé secrète** : ni dans Git, ni dans Moodle, Teams ou un courriel, ni dans une capture d'écran. Si elle est exposée, régénérez-la.

## 5. Ingérer les données d'exemple

Copiez le cas fictif UC-00 dans le dossier lu par le script, puis lancez l'ingestion du jeu d'entraînement :

```
mkdir -p data/training_data
cp -R ../exemple-donnees/training_data/UC-00 data/training_data/
python embedding_script/embedding_valid_pipeline.py --split train
```

La première exécution télécharge le modèle de plongements. La sortie doit se terminer par une ligne de la forme `SUCCESS [TRAIN]: 1 stories, 2 tests uploaded, 3 embeddings written to 'RAG Embeddings'.` Dans Supabase (Table Editor), vérifiez les tables `JIRA User Stories`, `Zephyr Tests` et `RAG Embeddings`.

**Premier exercice d'assurance qualité.** Ouvrez la ligne DEMO-1 de `JIRA User Stories` : la colonne des critères d'acceptation est vide, alors que le récit en contient cinq. Ouvrez ensuite la colonne `content` des cas de test dans `RAG Embeddings` : les étapes y apparaissent sous la forme ` -> `, sans texte. La section 6 explique pourquoi. Le pipeline s'est exécuté sans erreur, et pourtant les données qui alimenteraient le RAG et l'affinage sont incomplètes : c'est exactement ce qu'un assistant d'AQL doit savoir détecter.

## 6. État du code de départ

Les constats suivants ont été vérifiés en lisant le code et, pour les deux premiers, en exécutant les fonctions d'analyse sur les données d'exemple et sur les données d'origine. Ils font partie du travail à faire.

| # | Constat | Effet |
|---|---|---|
| 1 | `parse_story` cherche l'en-tête `## Acceptance Criteria`, mais les 16 récits d'origine (et UC-00) utilisent `## Critères d'acceptation`. | Les critères d'acceptation sont vides dans la base, dans les plongements et dans les données d'affinage. |
| 2 | Les étapes Zephyr utilisent les clés `description` et `expectedResult`, mais le texte à vectoriser lit `step` et `expected_result`. | Les étapes des cas de test sont vectorisées sans contenu. |
| 3 | Le script d'affinage lit la colonne `critières_acceptances`, alors que l'ingestion écrit `critères_acceptances`. | Même si le constat 1 est corrigé, l'affinage ne recevrait pas les critères. |
| 4 | Pour le jeu de validation, l'ingestion écrit quand même dans `JIRA User Stories` et `Zephyr Tests` (noms codés en dur). | Les données de validation se retrouvent dans les tables d'entraînement : fuite de données. |
| 5 | Les noms des tables de validation diffèrent entre les deux scripts (`Validation JIRA User Stories` contre `JIRA User Stories Validation`). | `schema.sql` utilise les noms du script d'affinage ; il faut harmoniser le code. |
| 6 | Aucun script n'alimente `Balsamiq Wireframes` ni le compartiment `balsamiq_wireframes`, et rien n'est prévu pour Figma. | L'affinage ne reçoit aucune image ; les maquettes ne sont pas dans le RAG ; le passage à Figma est à construire (section 9). |
| 7 | `pipe_src/utils.py` importe `pipe_src as config` au lieu de `pipe_src.config`, et `pipe_src/main.py` est vide. | Il n'existe pas de point d'entrée de bout en bout. |
| 8 | Aucun dossier `validation_data` n'est fourni, et l'affinage d'origine a utilisé tous les cas. | Il faut constituer une partition entraînement, validation et test avant tout affinage. |
| 9 | `requirements.txt` épingle des dépendances inutiles, et `mlx_vlm` n'y figure pas. | Installation lourde, affinage limité à macOS. |
| 10 | Le pipeline d'inférence et de RAG (de l'exigence aux cas de test générés) n'existe pas. | C'est la brique principale à construire. |

## 7. Affinage (facultatif, Mac Apple Silicon)

Le script `fine_tuning_qwen.py` lit les tables de Supabase, télécharge les maquettes du compartiment, écrit `data/train.jsonl` et `data/valid.jsonl`, puis lance `python -m mlx_vlm.lora`. Ne l'exécutez qu'après avoir corrigé les constats 1 à 8 et constitué un jeu de validation : sinon, vous reproduiriez l'essai d'origine, qui n'est pas évaluable.

```
pip install mlx-vlm
python fine_tuning_src/fine_tuning_qwen.py
```

Exécutez-le depuis `code-depart` : il charge `.env` sans chemin explicite et écrit dans `./data` et `./adapters`.

## 8. Données réelles : collaboration avec l'équipe MiBioKey du CRCHUM

Le projet 2 se fait en collaboration avec l'équipe MiBioKey du Centre de recherche du CHUM (CRCHUM), qui développe une plateforme de gestion de biobanques. Les données d'Andrew proviennent de ce projet : 16 récits Jira, 86 cas de test Zephyr et les maquettes Balsamiq correspondantes. Elles suivent exactement le format de `exemple-donnees/` : un dossier `UC-xx` par cas d'utilisation, avec `story.md`, `tests_zephyr.json`, `meta.json` et un dossier `mockups/`.

Ces données ne sont pas publiques. Elles sont remises aux équipes par le professeur, en accord avec l'équipe MiBioKey et selon ses conditions d'utilisation. Elles contiennent notamment des liens vers les systèmes internes du projet (Jira, SharePoint) :

- ne les poussez jamais dans un dépôt public ; `data/training_data/`, `data/validation_data/` et `data/wireframe_images/` sont déjà exclus par le `.gitignore` de `code-depart` ;
- ne les envoyez à aucun service d'IA infonuagique : le modèle et les plongements s'exécutent localement, et c'est l'une des raisons d'être de ce projet ;
- ne publiez dans votre rapport ou votre présentation que des extraits approuvés par l'équipe MiBioKey ;
- passez par l'équipe MiBioKey pour toute question sur une exigence, une maquette ou un cas de test : ses analystes sont l'oracle du projet.

## 9. Passage de Balsamiq à Figma

L'équipe MiBioKey a décidé de passer de Balsamiq à Figma pour ses maquettes. Les récits existants restent liés à des maquettes Balsamiq (des images dans des documents Word) ; les nouveaux récits le seront à des cadres Figma. L'agent doit accepter les deux pendant la transition.

**Ce que Figma change.** Une maquette Balsamiq n'est qu'une image : seul le modèle peut la lire. Un fichier Figma est une structure : l'API donne l'arbre des nœuds de chaque cadre, avec le texte exact des libellés, des champs et des boutons, et elle peut aussi rendre chaque cadre en image. Le texte des nœuds devient une preuve déterministe : un cas de test généré qui cite le bouton « Enregistrer » peut être vérifié mécaniquement contre la maquette, comme la vérification d'ancrage du projet 1 vérifie les citations du diff.

**L'API REST de Figma.** Deux points d'accès suffisent :

- `GET https://api.figma.com/v1/files/<clé du fichier>` retourne l'arbre des nœuds ; on y trouve les cadres (`"type": "FRAME"`), leur nom, leur identifiant et le texte de leurs nœuds (`"type": "TEXT"`, champ `characters`) ;
- `GET https://api.figma.com/v1/images/<clé du fichier>?ids=<id1>,<id2>&format=png` retourne, pour chaque identifiant, une adresse temporaire de l'image du cadre, à télécharger aussitôt.

La clé du fichier et l'identifiant d'un nœud se lisent dans l'adresse Figma d'un cadre (`figma.com/design/<clé>/...?node-id=<id>`). L'authentification se fait avec un jeton d'accès personnel, envoyé dans l'en-tête `X-Figma-Token`, avec la seule portée `file_content:read`. Le jeton donne accès aux fichiers que son titulaire peut ouvrir : l'équipe MiBioKey doit partager ses fichiers avec le compte utilisé, ou fournir les exports.

**Contraintes.**

- Le nombre de requêtes est limité, et la limite dépend du forfait Figma ; exportez une seule fois les cadres utiles (images et texte des nœuds) dans un cache local, puis travaillez sur ce cache ;
- le jeton est un secret : mettez-le dans `.env` (`FIGMA_TOKEN=`), jamais dans le code, Git ou une capture d'écran ;
- les maquettes MiBioKey restent soumises aux mêmes règles que les autres données du projet (section 8).

**Modèle de données suggéré.** Plutôt qu'une table par outil, une seule table de maquettes qui garde l'origine de chacune :

```
create table if not exists "Maquettes" (
  id           bigint generated always as identity primary key,
  story_key    text references "JIRA User Stories"(issue_key) on delete cascade,
  source       text not null check (source in ('balsamiq', 'figma')),
  file_key     text,          -- Figma : clé du fichier
  node_id      text,          -- Figma : identifiant du cadre
  frame_name   text,
  image_path   text not null, -- chemin dans le compartiment de stockage
  textes       jsonb,         -- Figma : texte des nœuds, pour la vérification d'ancrage
  exported_at  timestamptz default now()
);
```

Le script d'affinage et le futur pipeline de RAG lisent alors cette table, quelle que soit l'origine de la maquette. La vérification d'ancrage des libellés ne s'applique qu'aux maquettes Figma ; pour les maquettes Balsamiq, elle reste à faire par une personne.

