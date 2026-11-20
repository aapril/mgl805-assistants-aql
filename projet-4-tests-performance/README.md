# Projet 4 · Agent « libre de droits » de tests de performance

Ce dossier contient un prototype d'agent qui effectue des tests de performance d'une application web avec un modèle Qwen exécuté localement. Il suit la même architecture que les autres assistants du site : **le modèle propose et explique, le programme mesure et décide, une personne approuve.**

- **Instructions complètes** (installation, fonctionnement, sécurité, utilisation de Qwen, adaptation à votre application, limites) : [`GUIDE.md`](GUIDE.md)

## Démarrage rapide

Dans un premier terminal, l'application de démonstration (un petit service de bibliothèque qui contient deux défauts de performance injectés) :

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-4-tests-performance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m perfagent.cli demo-app
```

Dans un second terminal, depuis le même dossier :

```
source .venv/bin/activate
python -m unittest discover -s tests
python -m perfagent.cli run --model demo
cat "$(ls -td runs/*/ | head -1)report.md"
```

Les tests affichent `Ran 17 tests` puis `OK` ; la dernière commande montre un rapport qui recommande `changes_recommended`, parce que les deux défauts injectés font échouer deux exigences de performance. Pour utiliser Qwen, voir la section 5 du guide.

**N'exécutez des tests de charge que sur une application qui vous appartient ou que vous êtes explicitement autorisé à tester.**
