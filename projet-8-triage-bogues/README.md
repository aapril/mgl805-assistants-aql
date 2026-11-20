# Projet 8 · Agent « libre de droits » de triage des bogues et d'analyse des causes

Ce dossier contient un prototype d'agent qui trie les erreurs d'un journal de préproduction, les relie aux validations Git du dernier déploiement, confirme la cause par une reproduction et rédige des rapports de bogue avec un modèle Qwen exécuté localement. Il suit la même architecture que les autres assistants du site : **le programme rassemble les preuves et décide, le modèle rédige, une personne confirme chaque cause et chaque correctif.**

- **Instructions complètes** (fonctionnement, preuves, sécurité, utilisation de Qwen, adaptation à votre projet, limites, références) : [`GUIDE.md`](GUIDE.md)

## Démarrage rapide

Prérequis : Python 3.11 ou plus récent, et Git.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-8-triage-bogues
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
python -m triageagent.cli demo-build
python -m triageagent.cli run --model demo --allow-execution
cat "$(ls -td runs/*/ | head -1)report.md"
```

Les tests affichent `Ran 26 tests` puis `OK`. La commande `demo-build` crée le dépôt Git de démonstration dans `demo_work/` (un petit service de bibliothèque, avec cinq validations et deux déploiements) ; le journal de préproduction est `examples/staging.log`. Le rapport recommande `regressions_found` : deux erreurs sont apparues après le déploiement `v2`, et la reproduction confirme la validation qui a causé chacune.

L'option `--allow-execution` exécute des tests de reproduction écrits par des personnes sur des copies du code. Ne l'utilisez qu'avec un dépôt dont vous faites confiance au code.
