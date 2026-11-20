# Résultats du prototype original

Ce document résume la validation rapportée par les auteurs du prototype original (Akinotcho, Brahollari, Hassan, Keddam, Kodio et St-Amour, 2026). Le rapport et le code originaux sont publiés sous les licences CC BY 4.0 et MIT à https://github.com/manelkdm/code-review.

## Revue réelle du 9 novembre 2026

Une revue a été exécutée avec `qwen2.5-coder:7b` sur une machine hébergée par GitHub, sur la demande de fusion 4 du dépôt original. Le ticket demandait une fonction `subtract(a, b)` traitant les nombres positifs, négatifs et décimaux. La demande ajoutait :

- une fonction `substract(a, b)`, qui fait l'opération mais porte le mauvais nom ;
- une fonction `square_root(a)`, qui n'était pas demandée ;
- deux tests de `square_root`, et aucun test de la soustraction.

Les vérifications déterministes ont réussi : Ruff, Bandit et Gitleaks n'ont rien signalé, pytest a réussi 55 tests (les 53 tests de l'assistant de l'époque et les 2 ajoutés par la demande) et la couverture des lignes de `example_app` était de 90 %.

Les sept agents ont terminé leurs analyses en environ 15 minutes sur le processeur. La recommandation était `corrections_recommandees` (`changes_recommended` dans la version actuelle). Les agents ont détecté le nom non conforme et l'absence de tests de la soustraction. Plusieurs agents n'ont pas clairement relié `substract` à la fonction `subtract` demandée, et certains ont signalé des erreurs dans des tests de soustraction que la demande ne contenait pas.

Une seule revue réelle ne permet pas de mesurer statistiquement la précision, le rappel ou les gains de productivité. La section 10 de `GUIDE.md` et le dossier `evaluation/` donnent la méthode.
