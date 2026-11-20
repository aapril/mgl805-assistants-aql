# Projet 1 · Agent de revue de code « libre de droits »

Ce dossier contient l'assistant de revue de code du projet 1 du cours MGL805 : sept agents, un modèle à poids ouverts exécuté localement avec Ollama, des preuves déterministes collectées dans un conteneur isolé, une vérification d'ancrage des preuves et une règle de décision calculée par le programme. L'assistant **recommande ; il n'approuve et ne fusionne jamais**. Une personne prend la décision finale.

- **Instructions complètes** (installation, exemple commenté, GitHub Actions, preuve falsifiée, évaluation, dépannage) : [`GUIDE.md`](GUIDE.md)
- **Toutes les commandes, prêtes à copier** : [`exemples_commandes.md`](exemples_commandes.md)

Conception originale : Azhar Akinotcho, Pamela Brahollari, Hadi Hassan, Manel Keddam, Djibril Kodio et Louis Félix St-Amour, automne 2026 (dépôt d'origine : https://github.com/manelkdm/code-review). Le code, les messages et les rapports de cette version sont en anglais, comme dans le livre ; la documentation est en français. Voir `docs/RESULTATS_ORIGINAUX.md` (revue avec le modèle 7B) et `docs/RUN_2026-11-20_QWEN_1.5B.md` (revue avec le modèle 1.5B).

## Contenu

| Chemin | Contenu |
|---|---|
| `review/` | L'assistant : connecteurs, sept agents, orchestrateur, vérification d'ancrage, règle de décision, rapports |
| `scripts/collect_evidence.py` | Collecteur de preuves (Ruff, Bandit, Gitleaks, pytest, couverture) |
| `.github/workflows/` | Les trois flux GitHub Actions (voir `docs/GITHUB_ACTIONS.md`) |
| `Dockerfile.runner`, `compose.yaml` | Conteneur de preuves et serveur Ollama local |
| `lab/` | Scénarios `subtract` (revue réelle) et `forged` (preuve falsifiée) |
| `evaluation/` | Défauts injectés et calcul de la précision et du rappel |
| `tests/` | Les 65 tests unitaires de l'assistant |
| `verify.sh` | Compare les résultats de votre installation aux valeurs attendues |

## Démarrage rapide

Commandes pour un terminal Unix (Terminal de macOS, Linux, ou WSL 2 sous Windows), sans l'invite `%`.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-1-revue-de-code
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[lab]"
chmod +x verify.sh lab/*.sh
python -m unittest discover -s tests
```

La dernière commande doit afficher `Ran 65 tests` puis `OK`. Installez ensuite Ollama et un modèle (section 3 du guide ; avec 8 Go de mémoire, utilisez `qwen2.5-coder:1.5b`, section 4), puis suivez les sections 5 à 7 du guide pour vérifier l'installation et exécuter la revue du scénario de soustraction.
