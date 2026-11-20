# Guide du projet 3 : agent de tests d'API

Ce guide explique comment installer et exécuter le prototype d'agent de tests d'API, comment il fonctionne et ce qu'une équipe peut améliorer. Il complète le README d'origine de l'équipe, dans [`code-depart/README.md`](code-depart/README.md).

**Conventions.** Les commandes sont écrites pour un terminal Unix (Terminal de macOS, Linux ou WSL 2 sous Windows), sans l'invite : copiez-les une ligne à la fois. Sauf indication contraire, exécutez-les depuis le dossier `projet-3-tests-api/code-depart`, avec l'environnement virtuel activé.

## 1. Fonctionnement

L'agent enchaîne cinq étapes. Une erreur arrête le pipeline.

| Étape | Qui | Rôle |
|---|---|---|
| Discovery | Programme | Charger et valider la spécification OpenAPI (YAML ou JSON) |
| Analysis | Programme | Extraire le contrat : points d'accès, schémas, sécurité exigée |
| Generation | **Modèle** et programme | Le modèle propose des scénarios par lots de points d'accès ; le programme les valide contre le contrat, ajoute des scénarios négatifs fixes et écrit la suite Pytest |
| Execution | Programme | Exécuter Pytest et journaliser chaque requête et chaque réponse |
| Reporting | Programme | Produire le résumé et les rapports JSON et HTML |

Plusieurs choix de conception vont dans le sens de l'architecture du cours :

- les scénarios du modèle sont validés : l'identifiant d'opération, la méthode et le chemin doivent correspondre au contrat, sinon le scénario est rejeté ;
- l'authentification d'un scénario est déduite du contrat (sécurité déclarée dans la spécification), jamais de la réponse du modèle ;
- des scénarios négatifs sont produits par le code, indépendamment du modèle : jeton absent, jeton invalide, chaque champ requis manquant, chaque champ de type incorrect ;
- le fichier de tests est généré à partir d'un gabarit, et non écrit par le modèle ;
- les secrets sont lus dans des variables d'environnement et masqués dans les journaux et les rapports.

## 2. Installation

Prérequis : Python 3.11 ou plus récent. Ollama et un modèle (par exemple `qwen2.5-coder:1.5b`) ne sont nécessaires que pour générer des scénarios avec le modèle.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-3-tests-api/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -r examples/demo_flask_api/requirements.txt
```

La deuxième commande `pip` installe les dépendances de l'API de démonstration (Flask, SQLAlchemy, JWT). Contrairement à ce qu'indique le README d'origine, elles ne font pas partie des dépendances du projet.

## 3. Vérifier l'installation

```
python -m pytest -q
```

Les 160 tests unitaires du prototype doivent réussir (`160 passed`). La commande `python -m ruff check src tests` signale par contre 26 écarts de style : les corriger est un premier travail simple.

## 4. Démarrer l'API de démonstration et obtenir un jeton

L'API de démonstration est un petit blogue (utilisateurs, articles, commentaires, catégories, étiquettes, mentions « j'aime ») protégé par JWT, avec sa spécification OpenAPI de 33 opérations. Dans un premier terminal :

```
cd examples/demo_flask_api
python run.py
```

Elle écoute sur `http://127.0.0.1:5000`. Elle s'exécute en mode débogage de Flask : ne la rendez jamais accessible depuis le réseau.

Dans un second terminal, créez un compte et conservez le jeton retourné dans une variable d'environnement :

```
cd mgl805-assistants-aql/projet-3-tests-api/code-depart
source .venv/bin/activate
export API_TEST_AGENT_TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/register -H 'Content-Type: application/json' -d '{"username":"alice","email":"alice@example.com","password":"secret123"}' | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Si le compte existe déjà, remplacez `register` par `login` et ne gardez que `email` et `password` dans le corps de la requête. Le README d'origine n'explique pas cette étape : sans jeton, tous les tests des points d'accès protégés reçoivent 401.

## 5. Exécuter l'agent

Copiez la configuration d'exemple. L'agent lit `config.json` dans le dossier `code-depart` et n'accepte aucun argument en ligne de commande.

```
cp config.example.json config.json
api-test-agent
```

L'agent génère les scénarios lot par lot (quatre points d'accès par appel au modèle), exécute les tests et affiche un résumé. Les rapports sont dans `generated_tests/runs/<horodatage>/` ; ouvrez `report.html` dans un navigateur :

```
open "$(ls -td generated_tests/runs/*/ | head -1)report.html"
```

**Résultat de référence sans modèle.** Pour distinguer l'apport du modèle de celui du code, l'agent a été exécuté le 20 novembre 2026 avec un faux serveur de modèle qui ne retourne aucun scénario. Seuls les 63 scénarios négatifs produits par le code ont alors été exécutés :

- sans jeton, 49 réussis et 14 échoués : les tests de validation des corps de requête reçoivent 401 au lieu de 400 ;
- avec un jeton, 57 réussis et 6 échoués : les tests sur les commentaires reçoivent 404 au lieu de 400, parce que l'article ou le commentaire visé n'existe pas dans la base.

Ces échecs ne sont pas des défauts de l'API, mais des défauts de préparation des tests (authentification et données de départ). Ils montrent qu'un test qui échoue doit être analysé avant d'être rapporté comme un défaut. Avec un vrai modèle, le résumé indique aussi combien de points d'accès sont couverts par les scénarios du modèle ; dans l'exécution de référence, aucun ne l'était (`Endpoints: 0/33 covered`).

## 6. Les modes `load` et `view`

- `"mode": "load"` relit la suite sauvegardée (`generated_tests/scenarios.json`) et l'exécute sans appeler le modèle. On peut corriger ou compléter les scénarios à la main, puis relancer : c'est le moyen de faire réviser les scénarios par une personne avant de les conserver.
- `"mode": "view"` affiche une exécution passée sans relancer Pytest.

## 7. État du prototype et pistes d'amélioration

Les constats suivants ont été vérifiés en exécutant le prototype et en lisant son code.

| # | Constat | Effet |
|---|---|---|
| 1 | Le modèle choisit lui-même `expected_status`, sans obligation que ces codes soient documentés dans la spécification, et peut en donner plusieurs. | L'oracle peut venir du modèle plutôt que du contrat ; un scénario qui accepte `[200, 400, 404]` ne vérifie presque rien. |
| 2 | Aucune liste d'hôtes autorisés ; une section `servers:` de la spécification remplace `api_url`. | Les tests, y compris des `DELETE`, peuvent viser un autre serveur que prévu, voire un serveur de production. |
| 3 | Aucune préparation de données : les identifiants des chemins ne correspondent pas à des ressources existantes. | Faux échecs (404) et tests qui n'atteignent jamais la logique visée. |
| 4 | Le jeton doit être obtenu à la main. | Sans cette étape, les points d'accès protégés ne sont pas vraiment testés. |
| 5 | Le modèle est appelé par l'interface compatible OpenAI, sans schéma JSON imposé ; la réponse est nettoyée puis analysée, avec une seule relance. | Des lots entiers peuvent être perdus si un petit modèle ne produit pas un JSON valide. |
| 6 | La couverture ne compte que les scénarios du modèle, et aucune mesure ne compare les tests générés à des défauts connus. | On ne sait pas si l'agent trouve de vrais défauts. |
| 7 | Les dépendances de l'API de démonstration ne sont pas installées avec le projet, `model_options.max_endpoints` est ignoré, et `ruff` signale 26 écarts. | Installation et maintenance plus difficiles. |
| 8 | L'historique Git du dépôt d'origine est perdu : le dépôt public contient un seul commit. | La contribution de chaque membre n'est plus traçable ; les auteurs (Christophe Kruger, Jordan Tchinda Lontsi et Octave Emmanuel Faye) sont nommés dans le README de ce dossier, mais pas encore dans le fichier `LICENSE` ni dans `pyproject.toml`. |

## 8. Dépannage

| Symptôme | Cause et solution |
|---|---|
| `Config file not found` | `config.json` doit être dans le dossier `code-depart`, d'où la commande `api-test-agent` est lancée. |
| `ModuleNotFoundError: flask` | Les dépendances de l'API de démonstration ne sont pas installées : `pip install -r examples/demo_flask_api/requirements.txt`. |
| Tous les tests protégés reçoivent 401 | La variable `API_TEST_AGENT_TOKEN` n'est pas définie dans ce terminal (section 4). |
| `Model request failed` | Ollama n'est pas démarré ou le modèle n'est pas téléchargé (`ollama list`). |
| Tous les lots échouent avec un petit modèle | Le modèle ne produit pas de JSON valide ; essayez un modèle plus grand ou réduisez `batch_size`, et consultez `generated_tests/qwen_raw_responses.json`. |
| `fg: no current job` | Vous avez copié l'invite `%` avec la commande ; copiez seulement la commande. |
