# Gabarit pour construire votre propre assistant d'AQL

Ce dossier contient un petit assistant d'AQL complet que vous pouvez exécuter, lire en une heure et adapter. Il applique l'architecture des trois prototypes du cours (revue de code, accessibilité, sécurité) et en garde, sous une forme générique, les leçons : contrats stricts, preuves déterministes liées à une empreinte, vérification d'ancrage, règle de décision calculée par le programme et décision finale humaine.

| Module | Rôle |
|---|---|
| `assistant/contracts.py` | Schémas stricts pour chaque échange ; champs réservés au programme |
| `assistant/artifact.py` | L'artefact évalué et son empreinte |
| `assistant/evidence.py` | Outils déterministes, liés à l'empreinte de l'artefact |
| `assistant/agents.py` | **À adapter.** Une question étroite par agent, avec ses entrées |
| `assistant/llm.py` | Modèle local par Ollama (température 0, schéma, une seule relance) et pilote de démonstration |
| `assistant/grounding.py` | Chaque citation est-elle dans l'artefact, seulement dans la référence, ou nulle part ? |
| `assistant/decision.py` | **À adapter avec soin.** La recommandation, calculée par des règles |
| `assistant/pipeline.py` | Ordre fixe des agents ; les échecs restent visibles |
| `assistant/report.py` | Markdown pour les personnes, JSON pour l'évaluation et l'audit |
| `assistant_config.json` | **À adapter.** Nom de l'assistant et outils déterministes |
| `spec/FICHE_SPECIFICATION.md` | **À remplir en premier.** La fiche de spécification, avec les réponses de l'exemple |
| `evaluation/` | Défauts injectés et calcul de la précision et du rappel |
| `tests/` | 16 tests des règles qui doivent survivre à toute adaptation |

L'exemple est un **assistant de conformité aux exigences** : il vérifie une petite politique de mots de passe (`example/`) par rapport à son exigence (`example/reference/requirement.md`). Deux défauts y sont injectés : la longueur minimale est de 8 au lieu de 12, et aucun test ne couvre un mot de passe sans chiffre. La vérification de syntaxe et les tests unitaires passent quand même ; trouver les défauts est le travail des agents. Le code et les rapports sont en anglais, comme dans le projet 1.

## Essayer (10 minutes)

Depuis ce dossier, avec Python 3.11 ou plus récent. Copiez les commandes sans l'invite.

```
python3 -m venv .venv
source .venv/bin/activate
pip install "pydantic>=2,<3"
python -m unittest discover -s tests
python -m assistant.cli collect --artifact example/password_policy.py example/tests/test_password_policy.py
python -m assistant.cli run --reference example/reference/requirement.md --artifact example/password_policy.py example/tests/test_password_policy.py --evidence evidence.json
```

Les tests doivent afficher `Ran 16 tests` puis `OK`, la collecte `syntax: passed` et `unit tests: passed`, et la dernière commande `Recommendation: human_review_required`. Elle a utilisé le pilote de démonstration : aucun modèle n'a été exécuté, rien n'a été jugé, et la règle de décision demande donc une personne.

Pour utiliser un modèle local, démarrez Ollama, téléchargez un modèle (`ollama pull qwen2.5-coder:1.5b`, ou `qwen2.5-coder:7b` avec 16 Go de mémoire) et ajoutez `--model qwen2.5-coder:1.5b` à la commande `run`. Lisez le rapport avec `cat "$(ls -td runs/*/ | head -1)report.md"`.

Jugez ensuite les constats et calculez les mesures :

```
python evaluation/score.py extract runs/<identifiant>/report.json --case password --out judged.csv
python evaluation/score.py score judged.csv
```

## Construire le vôtre, en dix étapes

1. **Spécifier.** Copiez ce dossier, puis remplissez `spec/FICHE_SPECIFICATION.md` pour votre problème, avant tout code.
2. **Oracle.** Remplacez `example/reference/` par vos documents de référence.
3. **Preuves.** Listez vos outils dans `assistant_config.json` ; chaque commande doit retourner 0 lorsque sa vérification réussit.
4. **Agents.** Réécrivez `assistant/agents.py` : une question étroite par agent, le moins d'entrées possible, des instructions courtes.
5. **Modèle.** Choisissez le modèle et l'ordinateur à cette étape seulement, une fois connus l'oracle, les preuves et les questions laissées au modèle.
6. **Contrats.** Gardez `contracts.py`. Si vous changez une énumération, changez avec elle la règle de décision et ses tests.
7. **Capacités.** N'accordez à l'assistant que les fichiers, réseaux et accès dont il a besoin.
8. **Règle de décision.** Adaptez `decision.py` et gardez les quatre règles testées dans `tests/test_assistant.py` : un échec d'outil l'emporte sur le modèle ; des preuves absentes ou périmées renvoient à une personne ; une preuve non ancrée ne compte jamais ; aucun résultat ne signifie « approuvé ». Testez-la avec le pilote de démonstration avant d'exécuter un modèle.
9. **Corpus et mesures.** Injectez des défauts dans quelques artefacts, ajoutez des artefacts corrects et un artefact qui tente de manipuler l'assistant, listez-les dans `evaluation/seeded_defects.csv`, puis mesurez la précision et le rappel. Changez le modèle ou la machine pour observer la variabilité ; sur la même machine avec le même modèle, les exécutions se répètent généralement à l'identique.
10. **Configuration et plan.** Enregistrez les versions du code, des instructions, du modèle (avec son empreinte) et des outils, et décrivez l'assistant dans votre plan d'AQL.

## Limites du gabarit

Le gabarit est un point de départ pour apprendre, pas un produit. Il exécute les outils de l'artefact sur votre ordinateur (dans un pipeline, isolez-les comme dans `../projet-1-revue-de-code`), il lit des fichiers entiers (les gros artefacts demandent une stratégie de contexte) et sa vérification d'ancrage ne vérifie que des citations : les constats rédigés en prose demandent toujours une personne.
