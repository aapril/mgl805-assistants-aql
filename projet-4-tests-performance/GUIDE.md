# Guide du projet 4 : agent de tests de performance

Ce guide explique comment installer et utiliser le prototype d'agent de tests de performance, comment il fonctionne et comment l'adapter à votre application. Le code, les messages et les rapports de l'agent sont en anglais, comme ceux des autres prototypes du site ; la documentation est en français.

**Conventions.** Les commandes sont écrites pour un terminal Unix (Terminal de macOS, Linux ou WSL 2 sous Windows), sans l'invite : copiez-les une ligne à la fois. Sauf indication contraire, exécutez-les depuis le dossier `projet-4-tests-performance`, avec l'environnement virtuel activé.

## 1. Fonctionnement

Un test de performance demande deux compétences que l'agent sépare soigneusement. Concevoir un scénario de charge réaliste et interpréter des résultats demandent du jugement : c'est le rôle du modèle. Mesurer des temps de réponse et décider si une exigence est respectée demandent de la rigueur : c'est le rôle du programme.

| Étape | Qui | Module |
|---|---|---|
| 1. Vérifier que la cible est autorisée | Programme | `perfagent/safety.py` |
| 2. Proposer un scénario de charge à partir des exigences de performance et du catalogue des points d'accès | **Qwen** (planificateur) | `perfagent/llm.py` |
| 3. Borner le scénario : points d'accès du catalogue seulement, nombre maximal d'utilisateurs et durée maximale | Programme | `perfagent/safety.py` |
| 4. Générer la charge et mesurer les percentiles de latence, les erreurs et le débit | Programme | `perfagent/loadgen.py` |
| 5. Évaluer chaque exigence à la charge qu'elle précise | Programme | `perfagent/slo.py` |
| 6. Expliquer les résultats : exigences non respectées, goulots probables, prochaines mesures | **Qwen** (analyste) | `perfagent/llm.py` |
| 7. Vérifier que chaque nombre et chaque point d'accès cités par le modèle ont été mesurés | Programme | `perfagent/grounding.py` |
| 8. Recommander : corrections, revue humaine, ou prêt pour l'approbation humaine | Programme | `perfagent/decision.py` |

L'oracle est le fichier `examples/slo.json`, écrit par des personnes : chaque exigence nomme une métrique (par exemple le 95e percentile de latence d'un point d'accès), un seuil et le nombre d'utilisateurs simultanés auquel elle doit tenir. Une exigence mesurée avec moins d'utilisateurs que prévu n'est ni respectée ni échouée : elle est « non mesurée », et une personne doit décider. Le modèle ne décide jamais si l'application est assez rapide.

## 2. Sécurité

Un test de charge est un déni de service contrôlé. **N'exécutez des tests que sur une application qui vous appartient ou que vous êtes explicitement autorisé à tester, dans un environnement de test et jamais en production.** Trois contrôles sont imposés par le programme, quoi que propose le modèle :

- l'agent refuse toute cible dont l'hôte n'est pas dans `allowed_hosts` de `perf_config.json` (par défaut `127.0.0.1` et `localhost`), avant même d'appeler le modèle ;
- le scénario ne peut contenir que les points d'accès du catalogue ; un point d'accès inventé par le modèle est retiré ;
- le nombre d'utilisateurs et la durée sont plafonnés (par défaut 50 utilisateurs et 120 secondes).

Chaque ajustement est noté dans le rapport et renvoie le résultat à une revue humaine. Un test vérifie qu'un plan agressif (900 utilisateurs et un point d'accès `/admin/purge`) est bien ramené dans les limites.

## 3. Installation

Prérequis : Python 3.11 ou plus récent. Le prototype n'utilise que la bibliothèque standard de Python et Pydantic.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-4-tests-performance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests
```

Les 14 tests doivent afficher `Ran 14 tests` puis `OK`, en une dizaine de secondes : certains démarrent l'application de démonstration et génèrent une vraie charge pendant une ou deux secondes.

## 4. Exécution avec l'application de démonstration

L'application de démonstration (`demo_app/app.py`) est un petit service de bibliothèque qui contient deux défauts de performance injectés :

- `GET /search` fait attendre chaque requête derrière un seul verrou, comme si le bassin de connexions à la base de données n'avait qu'une connexion : rapide pour un utilisateur, lent sous la charge ;
- `POST /reserve` échoue une fois sur 40 (2,5 % d'erreurs).

Dans un premier terminal, démarrez l'application :

```
python -m perfagent.cli demo-app
```

Dans un second terminal, exécutez l'agent sans modèle :

```
source .venv/bin/activate
python -m perfagent.cli run --model demo
cat "$(ls -td runs/*/ | head -1)report.md"
```

L'exécution dure une dizaine de secondes. Avec `--model demo`, aucun modèle n'est appelé : le scénario est un mélange uniforme des points d'accès et rien n'est interprété. Le rapport recommande `changes_recommended` : l'exigence PERF-1 échoue (95e percentile des recherches d'environ 400 ms pour un seuil de 300 ms) et l'exigence PERF-3 aussi (environ 2,5 % de réservations en erreur pour un seuil de 1 %). Les exigences PERF-2 et PERF-4 sont respectées. Les valeurs exactes varient un peu d'un ordinateur à l'autre.

Arrêtez l'application avec Ctrl+C dans le premier terminal.

## 5. Exécution avec Qwen

Démarrez Ollama, téléchargez un modèle, puis donnez son nom à l'agent :

```
ollama pull qwen2.5-coder:1.5b
python -m perfagent.cli run --model qwen2.5-coder:1.5b
cat "$(ls -td runs/*/ | head -1)report.md"
```

Avec 8 Go de mémoire, utilisez `qwen2.5-coder:1.5b` et fermez Docker Desktop ; avec 16 Go, `qwen2.5-coder:7b` planifie et explique mieux. Tout autre modèle Ollama capable de produire du JSON peut être essayé, par exemple `qwen3.5:9b` avec une carte graphique de 12 Go.

**Ce qu'il faut observer dans le rapport.**

- Le scénario proposé par Qwen : utilise-t-il le nombre d'utilisateurs que demandent les exigences ? Le mélange des requêtes est-il réaliste ? Le programme a-t-il dû l'ajuster ?
- L'analyse de Qwen : chaque constat porte une marque ajoutée par le programme, *numbers found in the measurements*, *SOME NUMBERS NOT MEASURED* ou *NOT FOUND*. Un constat qui cite un nombre jamais mesuré ne compte pas et renvoie le rapport à une personne.
- La recommandation : elle dépend seulement des exigences et des mesures, jamais de l'analyse de Qwen.

## 6. Adapter l'agent à votre application

1. Listez vos points d'accès dans `perf_config.json` (`catalog`) et l'hôte de votre environnement de test dans `allowed_hosts`.
2. Écrivez vos exigences de performance en langage naturel dans `examples/requirements.md` et sous forme mesurable dans `examples/slo.json`.
3. Gardez des limites basses tant que les mesures ne sont pas comprises.
4. Pour des charges sérieuses, remplacez `loadgen.py` par Locust, k6 ou JMeter, et convertissez leurs résultats au contrat `Measurement` de `perfagent/contracts.py` : le reste du pipeline ne change pas.

## 7. Limites du prototype

- Le générateur de charge s'exécute sur le même ordinateur que l'application de démonstration : il mesure les deux ensemble.
- Le générateur suit un modèle fermé : chaque utilisateur virtuel attend sa réponse avant d'envoyer la suivante, ce qui peut masquer une saturation que verrait un modèle ouvert à débit fixe.
- Les métriques du serveur (processeur, mémoire, base de données) ne sont pas collectées : l'analyste ne raisonne qu'à partir des temps de réponse.
- Une exécution est un échantillon : répétez-la avant de conclure.
- Le prototype n'a pas encore été évalué avec un modèle réel sur un corpus de défauts injectés : c'est une bonne première tâche pour une équipe.

## 8. Dépannage

| Symptôme | Cause et solution |
|---|---|
| `Target host '...' is not in allowed_hosts` | La cible n'est pas autorisée. Ajoutez son hôte à `allowed_hosts` seulement si vous avez le droit de la tester. |
| `Connection refused` ou toutes les requêtes en erreur | L'application de démonstration n'est pas démarrée dans le premier terminal. |
| `Address already in use` au démarrage de l'application | Une autre instance occupe le port 8099 ; arrêtez-la, ou utilisez `--port 8100` et `--target http://127.0.0.1:8100`. |
| L'analyse se termine par `Failure URLError` | Ollama n'est pas démarré ou le modèle n'est pas téléchargé (`ollama list`). Les mesures et la recommandation restent valides. |
| `fg: no current job` | Vous avez copié l'invite `%` avec la commande ; copiez seulement la commande. |
