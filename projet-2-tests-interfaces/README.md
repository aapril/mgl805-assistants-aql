# Projet 2 · Agent « libre de droits » de tests d'interfaces utilisateurs

Ce dossier contient le code de départ du projet 2 du cours MGL805 : le moteur d'IA préparé par Andrew Phillips à l'été 2026 pour générer des cas de test d'interfaces à partir de récits Jira, de cas de test Zephyr et de maquettes Balsamiq. Il ingère ces données dans Supabase, calcule des plongements vectoriels (pgvector) et contient le code d'affinage d'un modèle Qwen multimodal. Le pipeline d'inférence et de RAG reste à construire, et l'équipe MiBioKey passant de Balsamiq à Figma, l'agent doit aussi lire les maquettes Figma (guide, section 9).

- **Guide d'installation et état du code** : [`GUIDE.md`](GUIDE.md)
- **Schéma de la base Supabase** : [`schema.sql`](schema.sql)
- **Cas d'utilisation fictif pour démarrer** : [`exemple-donnees/`](exemple-donnees/)
- **README d'origine (anglais)** : [`code-depart/README_MGL805.md`](code-depart/README_MGL805.md)

## Démarrage rapide

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-2-tests-interfaces/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Créez ensuite votre projet Supabase avec `schema.sql`, remplissez `.env` et ingérez le cas UC-00 (guide, sections 4 et 5). Lisez la section 6 du guide avant d'écrire du code : elle liste dix constats vérifiés sur l'état du code de départ.

Le projet se fait en collaboration avec l'équipe MiBioKey du CRCHUM. Les données réelles (récits Jira, cas de test Zephyr et maquettes Balsamiq du projet MiBioKey) ne sont pas publiées dans ce site ; elles sont remises aux équipes selon les conditions de l'équipe MiBioKey (guide, section 8).
