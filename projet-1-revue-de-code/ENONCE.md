# Projet 1 · Agent de revue de code « libre de droits » : de la version 1 à la version 2

Du ticket Jira à la clôture de la revue et à la fusion dans la branche `main`, le processus de revue de code peut être amélioré avec l'assistance de l'IA générative. Ce projet poursuit le travail de l'équipe de l'automne 2026 : partez de son prototype, mesurez-le, puis améliorez-le.

## Ressources du site d'accompagnement

- [Guide du laboratoire](GUIDE.md) : installation, exemple commenté, GitHub Actions, preuve falsifiée, évaluation et dépannage ;
- [Commandes prêtes à copier](exemples_commandes.md) ;
- [Résultats de la version 1 avec le modèle 7B](docs/RESULTATS_ORIGINAUX.md) et [avec le modèle 1.5B](docs/RUN_2026-11-20_QWEN_1.5B.md) ;
- [Scénario de laboratoire](lab/) et [trousse d'évaluation](evaluation/) ;
- [Gabarit pour construire un assistant](../gabarit-assistant/) et sa [fiche de spécification](../gabarit-assistant/spec/FICHE_SPECIFICATION.md) ;
- [Dépôt d'origine de l'équipe](https://github.com/manelkdm/code-review).

## Ce que l'équipe a livré

Le prototype enchaîne sept agents spécialisés sur un modèle local (qwen2.5-coder via Ollama) dans GitHub Actions. Les preuves déterministes (Ruff, Bandit, Gitleaks, pytest, couverture) sont collectées dans un conteneur isolé. Les sorties sont validées par des contrats Pydantic stricts. La recommandation est calculée par une règle, jamais par le modèle. Cette architecture est solide.

## Ce que les essais ont montré

Sur la demande de soustraction, le modèle 7B a recommandé des corrections pour de bonnes raisons, mais plusieurs agents ont affirmé des faits faux. Toutes les sévérités étaient au maximum et aucun constat n'indiquait de fichier. Avec le modèle 1.5B, la décision est restée juste pour de mauvaises raisons : précision 0,25, rappel 0,33. Un agent a même « corrigé » la faute de frappe dans l'extrait qu'il citait comme preuve ; la vérification d'ancrage ajoutée depuis le détecte maintenant (guide, section 7). Enfin, un fichier `conftest.py` ajouté par la demande peut falsifier les résultats de tests (guide, section 9).

## Comment font les outils commerciaux

- [Code Review de Claude Code](https://claude.com/blog/code-review) : plusieurs agents inspectent la demande en parallèle, vérifient leurs constats pour réduire les faux positifs et les classent par sévérité ; l'outil n'approuve jamais une fusion, et une revue coûte en moyenne de 15 à 25 $ ;
- [Gemini Code Assist sur GitHub](https://developers.google.com/gemini-code-assist/docs/review-github-code) : revue initiale à l'ouverture de la demande, commandes `/gemini review` et `/gemini summary`, guide de style du dépôt et seuil de sévérité configurable ;
- [CodeRabbit](https://www.coderabbit.ai), [Greptile](https://www.greptile.com) et [Bito](https://bito.ai) : Greptile indexe toute la base de code, Bito permet de discuter un commentaire avec l'agent ;
- [PR-Agent](https://github.com/The-PR-Agent/pr-agent) : la référence libre, maintenue par la communauté et auto-hébergeable.

## Améliorations demandées pour la version 2

- Partir vraiment du ticket Jira : connecteur Jira (API REST ou serveur MCP) à la place du ticket GitHub, et traçabilité ticket, critères, constats, décision, fusion ;
- Ajouter un agent de vérification qui doit confirmer ou rejeter chaque constat avant sa publication ;
- Exiger le fichier et la ligne de chaque constat et publier des commentaires en ligne ;
- Calibrer les sévérités : seuil configurable, et sévérité calculée par des règles plutôt que reprise du modèle ;
- Fournir du contexte au-delà du diff : fichiers voisins, guide de style du dépôt, historique des revues ;
- Conserver et étendre la vérification d'ancrage (`review/grounding.py`) : chaque citation doit être trouvée dans le diff, et non seulement dans le ticket ;
- Exiger une revue humaine dès qu'une demande modifie la configuration des tests (`conftest.py`, `pytest.ini`) ;
- Épingler le modèle par son empreinte et les actions GitHub par leur SHA ;
- Mesurer avant de comparer : un corpus d'au moins dix demandes avec défauts injectés, la précision et le rappel sur plusieurs exécutions, puis une comparaison avec PR-Agent et un outil commercial sur ce même corpus (justesse, temps, coût).

## Livrables

- Le code de la version 2, dans un dépôt public sous licence MIT, avec un `README` et un guide d'installation en français ;
- Un test unitaire pour chaque amélioration, écrit avant d'exécuter un modèle ;
- Le corpus, les grilles de jugement et les mesures avant et après chaque amélioration (`evaluation/score.py`) ;
- Un rapport qui distingue ce qui a été observé, ce qui a été mesuré et ce qui reste à démontrer.
