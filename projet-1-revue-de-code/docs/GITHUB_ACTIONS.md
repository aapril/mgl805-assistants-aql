# GitHub Actions : revue de code assistée par l'IA

Le projet utilise trois flux de travail GitHub Actions pour tester l'assistant, collecter les preuves et exécuter la revue par les sept agents (voir `GUIDE.md`, section 8).

| Flux de travail | Rôle |
|---|---|
| `tests.yml`, Reviewer Unit Tests | Exécute les tests unitaires de l'assistant et la démonstration. |
| `evidence.yml`, PR Evidence Checks | Exécute Ruff, Bandit, Gitleaks et pytest sur le code de la demande de fusion, dans un conteneur isolé. |
| `ai-review.yml`, AI Code Review | Exécute les sept agents avec Ollama et publie le résumé sur la demande de fusion. |

## Fonctionnement

1. Une demande de fusion est ouverte ou mise à jour avec un ticket GitHub lié (`Closes #N`).
2. Les tests de l'assistant et la collecte des preuves démarrent automatiquement.
3. Les preuves sont produites dans un conteneur Docker sans accès réseau.
4. À la fin de la collecte, le flux IA lit le diff, le ticket et les preuves.
5. Les sept agents analysent ces informations avec Ollama.
6. Un commentaire de synthèse est publié ou mis à jour sur la demande de fusion. Les rapports Markdown et JSON sont conservés comme artefacts pendant 14 jours.

Le flux IA s'exécute même si certaines vérifications ont échoué, afin de signaler les problèmes détectés.

## Exécution et sécurité

Les flux s'exécutent sur des machines temporaires hébergées par GitHub. Aucune installation locale ni aucun jeton personnel n'est nécessaire.

Le flux de preuves a des permissions en lecture seule et exécute les analyseurs dans un conteneur sans réseau, sans capacités et avec une source en lecture seule. Le flux IA, qui peut écrire des commentaires, ne récupère que la branche par défaut et n'exécute jamais le code de la demande ; il traite l'artefact de preuves comme une donnée non fiable et vérifie son schéma et son commit avant de l'utiliser.

Le modèle est `qwen2.5-coder:7b`, exécuté sur le processeur. Il peut être changé avec la variable de dépôt `REVIEW_OLLAMA_MODEL` (Settings, Secrets and variables, Actions, Variables).

## Limites

- Seules les demandes du même dépôt sont révisées ; les bifurcations sont ignorées.
- Un seul ticket GitHub est analysé par revue.
- La portée de l'analyse statique et de la couverture est fixée dans `evidence.yml` (par défaut `example_app`) et peut être changée avec les variables `REVIEW_SCAN_PATH` et `REVIEW_COVERAGE_SOURCE`.
- Les résultats de l'IA soutiennent la revue ; ils ne constituent jamais une approbation automatique.
