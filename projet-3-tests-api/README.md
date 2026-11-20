# Projet 3 · Agent « libre de droits » de tests d'API

Ce dossier contient le prototype d'agent de tests d'API réalisé à l'automne 2026 dans le cours MGL805 par Christophe Kruger, Jordan Tchinda Lontsi et Octave Emmanuel Faye. À partir d'une spécification OpenAPI et de l'URL d'une API en marche, un modèle local (Ollama) génère des scénarios de test ; le programme y ajoute des scénarios négatifs indépendants du modèle, écrit une suite Pytest, l'exécute et produit des rapports HTML et JSON, sans exposer les secrets utilisés.

- **Guide d'installation, d'exécution et état du prototype** : [`GUIDE.md`](GUIDE.md)
- **Code de l'équipe et son README d'origine** : [`code-depart/`](code-depart/)

Le dépôt d'origine de l'équipe était privé et n'est plus accessible ; le code a été republié par un membre de l'équipe à https://github.com/ckruger1204/api-test-clone (licence MIT). La copie de ce dossier assure qu'il reste disponible aux équipes suivantes.

## Démarrage rapide

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-3-tests-api/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -r examples/demo_flask_api/requirements.txt
python -m pytest -q
```

La dernière commande doit afficher `160 passed`. Pour exécuter l'agent contre l'API de démonstration, suivez les sections 4 et 5 du guide : il faut d'abord obtenir un jeton d'authentification.
