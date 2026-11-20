# Projet 7 · Agent « libre de droits » d'évaluation de l'architecture et de la dette technique

Ce dossier contient un prototype d'agent qui évalue l'architecture et la dette technique d'un dépôt Python avec un modèle Qwen exécuté localement. Il suit la même architecture que les autres assistants du site : **le programme mesure et décide, le modèle classe et explique, une personne approuve.**

- **Instructions complètes** (fonctionnement, règles d'architecture et portes de qualité, sécurité, utilisation de Qwen, adaptation à votre dépôt, limites, références) : [`GUIDE.md`](GUIDE.md)

## Démarrage rapide

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-7-architecture-dette-technique
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
python -m debtagent.cli run --model demo
cat "$(ls -td runs/*/ | head -1)report.md"
```

Les tests affichent `Ran 27 tests` puis `OK`. La dernière commande montre le rapport sur le dépôt de démonstration (`demo_repo/`, un petit service de bibliothèque qui contient des défauts d'architecture et de la dette injectés) : il recommande `changes_recommended`, parce que cinq des six portes de qualité échouent. Pour utiliser Qwen, voir la section 6 du guide.

L'agent lit et analyse le code sans jamais l'importer ni l'exécuter.
