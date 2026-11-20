# Guide du laboratoire : assistant de revue de code (projet 1)

Ce guide accompagne le projet 1 du cours MGL805 (Vérification et assurance qualité de logiciels) à l'ÉTS. Il contient tout ce qu'il faut pour installer, exécuter, vérifier et évaluer l'assistant de revue de code : les commandes, les résultats attendus et le dépannage. Le chapitre 5 du livre *Software Quality Assurance* (en préparation) présente la même démarche en anglais ; ses numéros de section sont indiqués entre parenthèses lorsqu'ils sont utiles.

Le laboratoire permet :

- d'installer l'assistant sur votre ordinateur et de vérifier l'installation (sections 2 à 5) ;
- de reproduire la revue réelle de la demande de soustraction (sections 6 et 7) ;
- d'exécuter l'assistant dans GitHub Actions sur une demande de fusion de votre propre dépôt (section 8) ;
- de reproduire l'expérience de la preuve falsifiée (section 9) ;
- de mesurer la précision et le rappel de l'assistant (section 10).

La section 13 renvoie aux prototypes d'accessibilité et de sécurité des autres équipes, et la section 14 explique comment démarrer votre propre assistant à partir du gabarit.

L'assistant a été conçu par Azhar Akinotcho, Pamela Brahollari, Hadi Hassan, Manel Keddam, Djibril Kodio et Louis Félix St-Amour dans le cadre du projet de session de l'automne 2026 (dépôt d'origine : https://github.com/manelkdm/code-review, licence MIT ; rapport sous licence CC BY 4.0). Cette version a été traduite en anglais pour le livre et enrichie ; le code, les messages et les rapports de l'assistant sont donc en anglais. Voir `docs/RESULTATS_ORIGINAUX.md`.

**Conventions.** Les commandes sont écrites pour un terminal Unix : le Terminal de macOS ou de Linux, ou WSL 2 sous Windows. L'invite `%` représente le terminal et ne doit pas être tapée. Sauf indication contraire, exécutez les commandes depuis le dossier `projet-1-revue-de-code`, avec l'environnement virtuel activé. Toutes les commandes de ce guide sont aussi regroupées dans `exemples_commandes.md`, prêtes à copier.

---

## 1. Vue d'ensemble du laboratoire

Le laboratoire comporte deux parties. Dans la **partie A**, vous installez l'assistant sur votre ordinateur, vous exécutez les vérifications déterministes dans le même conteneur isolé que le flux de travail GitHub, et vous exécutez les sept agents localement avec un modèle à poids ouverts servi par Ollama. La partie A ne demande pas de compte GitHub. Dans la **partie B**, vous publiez l'assistant dans votre propre dépôt GitHub et vous le regardez réviser une vraie demande de fusion sur les machines de GitHub.

Le dossier contient :

| Chemin | Contenu |
|---|---|
| `review/` | L'assistant : connecteurs, sept agents, orchestrateur, vérification d'ancrage, règle de décision, rapports |
| `scripts/collect_evidence.py` | Collecteur de preuves (Ruff, Bandit, Gitleaks, pytest, couverture) |
| `.github/workflows/` | Les trois flux de travail GitHub Actions (voir `docs/GITHUB_ACTIONS.md`) |
| `Dockerfile.runner` | Image du conteneur isolé de collecte des preuves |
| `compose.yaml` | Serveur Ollama local |
| `lab/` | Scénarios et scripts du laboratoire |
| `evaluation/` | Défauts injectés et script de calcul des mesures |
| `tests/` | Les 65 tests unitaires de l'assistant |
| `verify.sh` | Exécute les vérifications de ce guide et compare les résultats aux valeurs attendues |
| `exemples_commandes.md` | Toutes les commandes de ce guide |

## 2. Prérequis

- **Git**, pour obtenir le dépôt et construire les dépôts du laboratoire (version 2.28 ou plus récente) ;
- **Python 3.11 ou plus récent** ; les commandes ont été vérifiées avec Python 3.12 ;
- **Docker Desktop** (ou Docker Engine sous Linux), installé et démarré, pour le conteneur de preuves et le serveur Ollama ;
- environ **10 Go d'espace disque libre** : environ 4,7 Go pour le modèle, le reste pour les images Docker ;
- **16 Go de mémoire** recommandés pour le modèle de 7 milliards de paramètres ; avec 8 Go au total, utilisez le petit modèle `qwen2.5-coder:1.5b` (section 4) ;
- pour la **partie B seulement**, un compte GitHub et l'outil en ligne de commande `gh`.

Vérifiez les versions :

```
% git --version
% python3 --version
% docker --version
```

## 3. Installation

Obtenez le dépôt du cours, créez un environnement virtuel Python dans le dossier du projet et installez l'assistant avec les extras du laboratoire, qui ajoutent pytest et son module de couverture :

```
% git clone https://github.com/aapril/mgl805-assistants-aql.git
% cd mgl805-assistants-aql/projet-1-revue-de-code
% python3 -m venv .venv
% source .venv/bin/activate
% python -m pip install -e ".[lab]"
% chmod +x verify.sh lab/*.sh
```

**Démarrer le serveur Ollama.** Sur un **Mac**, utilisez l'application Ollama native (recommandé) : elle utilise le processeur graphique Apple et chaque agent répond en environ une minute. Dans Docker, le modèle s'exécute sur le processeur central seulement et, sur un portable, chaque agent peut dépasser la limite de 8 minutes de l'assistant (section 11).

```
% brew install --cask ollama
% open -a Ollama
% ollama pull qwen2.5-coder:7b
```

Sous **Linux, Windows (WSL 2) ou sur une machine dotée d'une carte graphique NVIDIA**, le conteneur est la méthode la plus portable. Le fichier `compose.yaml` le démarre sous le nom `sqa-ollama`, sur le port 11434, avec un volume Docker qui conserve les modèles téléchargés. Téléchargez le modèle une seule fois ; cela prend quelques minutes :

```
% docker compose up -d
% docker compose exec ollama ollama pull qwen2.5-coder:7b
```

Construisez l'image du conteneur de preuves. C'est la même image que celle du flux de travail PR Evidence Checks, avec Python, Ruff, Bandit, pytest et Gitleaks :

```
% docker build -f Dockerfile.runner -t ai-review-runner:local .
```

## 4. Autres méthodes d'installation

- **macOS.** Utilisez l'application Ollama native, comme à la section 3. Docker Desktop pour Mac ne donne pas aux conteneurs l'accès au processeur graphique Apple ; un modèle conteneurisé est donc généralement trop lent pour les sept agents. Les commandes du guide fonctionnent sans changement avec l'application native, qui écoute sur le même port 11434. N'exécutez pas les deux : arrêtez le conteneur avec `docker compose down` avant de démarrer l'application native, et téléchargez de nouveau le modèle avec `ollama pull`. Si vous devez garder le conteneur, augmentez le délai accordé à chaque agent avec `export OLLAMA_TIMEOUT=1800` et prévoyez une heure ou plus.
- **Windows.** Utilisez WSL 2 pour toutes les commandes. L'installateur natif d'Ollama pour Windows peut remplacer le conteneur.
- **Linux.** Le conteneur peut utiliser une carte graphique NVIDIA si le NVIDIA Container Toolkit est installé ; Ollama peut aussi être installé nativement.
- **8 Go de mémoire.** Utilisez le modèle de 1,5 milliard de paramètres de la même famille. Téléchargez-le avec `ollama pull qwen2.5-coder:1.5b` (application native) ou `docker compose exec ollama ollama pull qwen2.5-coder:1.5b` (conteneur), et ajoutez `--model qwen2.5-coder:1.5b` aux commandes `review.cli local` (ou `OLLAMA_MODEL=qwen2.5-coder:1.5b` pour `verify.sh`). La revue est plus rapide mais nettement moins juste, ce qui est en soi une observation utile pour la section 10.
- **Mac avec 8 Go de mémoire.** N'exécutez pas le modèle 7B : ses poids (4,7 Go) et la fenêtre de contexte de 32 768 jetons demandée par l'assistant (environ 1,8 Go) dépassent ce que macOS laisse libre ; le système écrit sur le disque et le Mac cesse de répondre. Procédez en deux temps. D'abord, avec Docker Desktop démarré, chargez les données du laboratoire et collectez les preuves (section 6). Ensuite, quittez complètement Docker Desktop, démarrez l'application Ollama native et exécutez les agents avec le modèle 1.5B. Deux variables allègent encore la charge : `export OLLAMA_NUM_CTX=8192` réduit la fenêtre de contexte et `export OLLAMA_NUM_THREAD=4` laisse des cœurs libres pour le système. Sur un Mac Apple Silicon de 8 Go, les sept agents ont terminé en environ une minute avec le modèle 1.5B. Exécutez plutôt le modèle 7B sur les machines de GitHub (partie B, section 8), qui offrent 16 Go.
- **Aucune installation locale.** Passez directement à la partie B (section 8) ; tout s'exécute sur les machines de GitHub.

## 5. Vérifier l'installation

**Tests unitaires.** Les 65 tests unitaires de l'assistant vérifient ses règles sans appeler GitHub ni Ollama, grâce à des services simulés. Les dernières lignes doivent être :

```
% python -m unittest discover -s tests
...
Ran 65 tests in 0.214s

OK
```

La durée varie d'un ordinateur à l'autre.

**Démonstration.** La démonstration parcourt tout le pipeline avec un modèle simulé et affiche le dossier du rapport produit (un identifiant d'exécution aléatoire) :

```
% python -m review.cli demo
runs/2f8b0b1094c7416b805685d7452eae2b
```

Le fichier `report.md` de ce dossier doit commencer par la recommandation `human_review_required` et la mention « SIMULATED DEMONSTRATION: no model or analysis tool was run. »

**Modèle.** Le serveur Ollama doit afficher le modèle, d'une taille d'environ 4,7 Go (ou 1 Go pour le 1.5B) :

```
% ollama list                                # application native
% docker compose exec ollama ollama list     # conteneur
```

**Script de vérification.** Le script `verify.sh` exécute ces vérifications ainsi que celles des sections 6 et 9, et compare chaque résultat à la valeur attendue. Il prend deux à trois minutes et doit se terminer par la ligne `10 checks passed, 0 deviations` :

```
% ./verify.sh
```

Avec l'option `RUN_MODEL=1`, il exécute aussi les sept agents avec le vrai modèle, ce qui ajoute une onzième vérification :

```
% RUN_MODEL=1 ./verify.sh
```

## 6. Charger les données du laboratoire

Les données de ce laboratoire ne sont pas des tables, mais des dépôts : une application à réviser, une modification proposée et les preuves produites par les outils.

**Construire l'application à réviser.** Le script `lab/make-lab-repo.sh` crée un dépôt Git contenant la petite calculatrice du dossier `example_app` et ses tests, la valide, puis applique la demande de fusion du scénario de soustraction dans un second commit. Il écrit aussi le diff de la demande à côté du dépôt :

```
% lab/make-lab-repo.sh ~/sqa-lab/subtract subtract
Repository ready: /Users/vous/sqa-lab/subtract (HEAD 9c41e07)
Diff of the pull request: /Users/vous/sqa-lab/subtract.diff
```

L'identifiant du commit sera différent chez vous. Le script n'écrase jamais un dossier existant.

**Collecter les preuves.** Le script `lab/collect-evidence.sh` exécute le conteneur de preuves sur le dépôt avec exactement les mêmes options d'isolement que le flux de travail : pas de réseau, système de fichiers en lecture seule, aucune capacité Linux, aucune élévation de privilèges, et des limites de mémoire, de processeurs et de processus :

```
% lab/collect-evidence.sh ~/sqa-lab/subtract ~/sqa-lab/out
Evidence written: /Users/vous/sqa-lab/out/evidence.json
```

**Normaliser les preuves.** La normalisation vérifie le schéma des preuves et leur commit :

```
% python -m review.ci normalize \
    --input ~/sqa-lab/out/evidence.json \
    --head $(git -C ~/sqa-lab/subtract rev-parse HEAD) \
    --output ~/sqa-lab/subtract.json
Evidence structure and commit verified.
This does not attest their authenticity.
```

La deuxième ligne est importante : la section 9 montre pourquoi.

**Ce que disent les preuves.** Pour le scénario de soustraction, Ruff, Bandit et Gitleaks ne signalent rien, pytest exécute 5 tests qui réussissent tous et la couverture des lignes de l'application est de 90 %. La barrière du flux de preuves les accepte :

```
% python -m review.ci gate --input ~/sqa-lab/subtract.json \
    --head $(git -C ~/sqa-lab/subtract rev-parse HEAD)
```

La commande n'affiche rien et retourne 0 lorsqu'elle accepte. Aucun des trois défauts injectés n'est visible pour les outils déterministes.

## 7. Exécuter les sept agents (exemple commenté)

Le ticket du scénario, `lab/issue-subtract.md`, demande une fonction `subtract(a, b)` qui retourne `a - b` (AC-1), qui traite les nombres positifs, négatifs et décimaux (AC-2) et qui est couverte par des tests unitaires des cas nominal, négatif et décimal (AC-3). La demande de fusion, `lab/pr-subtract.patch`, nomme la fonction `substract`, ajoute une fonction `square_root` que personne n'a demandée et ajoute deux tests qui portent tous deux sur `square_root`.

La commande `local` exécute les sept agents sur un fichier de ticket et un diff, sans GitHub :

```
% python -m review.cli local \
    --issue-file lab/issue-subtract.md \
    --diff ~/sqa-lab/subtract.diff \
    --evidence ~/sqa-lab/subtract.json
Report saved: runs/c73878d62d7141a3ae610764a9a5602a
Recommendation: changes_recommended
```

Sur un portable sans carte graphique, les sept agents prennent de 10 à 20 minutes ; avec l'application Ollama native sur un Mac Apple Silicon, quelques minutes. Ajoutez `--model demo` pour tester le pipeline sans modèle.

Lisez le rapport :

```
% cat "$(ls -td runs/*/ | head -1)report.md"
```

**Ce qu'il faut observer.**

- Chacun des trois défauts injectés a-t-il été trouvé par au moins un agent ?
- Un agent a-t-il établi que `substract` est la fonction demandée sous un mauvais nom ?
- Un agent a-t-il affirmé quelque chose de faux, par exemple que des tests de la soustraction ont été ajoutés ?
- Les sévérités sont-elles calibrées ? L'ajout de `square_root` est-il jugé critique ?
- Les constats indiquent-ils le fichier concerné ?
- Une preuve porte-t-elle la marque *NOT FOUND in the diff or issue* ou *found in the ISSUE ONLY* ? Ces marques sont ajoutées par la vérification d'ancrage (plus bas), pas par le modèle.

**Exemple avec le petit modèle.** Le 20 novembre 2026, le scénario a été exécuté sur un Mac de 8 Go avec `--model qwen2.5-coder:1.5b`. L'exécution a pris environ une minute et a recommandé `changes_recommended`, mais pour des raisons largement fausses : seul D3 (aucun test de la soustraction) a été trouvé, l'agent 1 a affirmé que le ticket ne contenait aucun critère d'acceptation, et l'agent 3 a cité le diff comme preuve en renommant la fonction `subtract`, corrigeant ainsi en silence le défaut même qu'il aurait dû signaler. La précision était de 0,25 et le rappel de 0,33. Le rapport complet et son évaluation sont dans `docs/RUN_2026-11-20_QWEN_1.5B.md`.

**La vérification d'ancrage.** Les contrats de `review/models.py` vérifient qu'une preuve est une chaîne de la bonne longueur, pas qu'elle est vraie. Depuis cette exécution, `review/grounding.py` vérifie mécaniquement chaque citation qu'il peut : chaque ligne d'un extrait de diff, chaque fragment de code entre accents graves, le fichier nommé par un constat et la preuve de chaque critère extrait par l'agent 1, qui doit citer le ticket mot pour mot. La vérification indique aussi où chaque citation a été trouvée :

- *found in the diff* : toutes les citations se trouvent dans le diff ;
- *found in the ISSUE ONLY* : la citation existe dans le ticket, mais pas dans le diff ; elle ne prouve rien sur le code, et une raison demande à une personne de vérifier que le nom est implanté ;
- *NOT FOUND* : la citation n'existe nulle part ; le constat ne compte plus dans une demande de corrections et la revue est renvoyée à une personne.

Aucune de ces marques ne peut rendre la décision plus favorable. Une preuve rédigée en prose ne peut pas être vérifiée ainsi et ne porte aucune marque. Le champ `grounded` est calculé par le programme et retiré du schéma montré au modèle, qui ne peut donc pas déclarer ses propres preuves vérifiées. `tests/test_grounding.py` rejoue l'extrait de l'agent 3 et la preuve de l'agent 2.

**Ce que la vérification a montré.** Exécuté de nouveau sur le même Mac, le modèle 1.5B a produit exactement le même texte, mot pour mot, pour les sept agents : avec une température de 0, le même modèle sur la même machine se répète. Le premier constat de l'agent 3 a été marqué *NOT FOUND*, parce que `def subtract(a, b):` n'apparaît pas dans le diff. Les constats des agents 2 et 4, qui affirment que « le diff ajoute une fonction `subtract` », sont marqués *found in the ISSUE ONLY* : le nom vient de l'exigence et ne figure pas dans le diff, ce qui met sous les yeux du réviseur le défaut D1, qu'aucun agent n'avait signalé.

**Variabilité.** Puisqu'une exécution se répète à l'identique sur la même machine avec le même modèle, la répéter n'apporte rien. Pour observer la variabilité, changez un élément à la fois : le modèle, sa version, la machine ou le serveur d'inférence.

## 8. Exécuter l'assistant dans GitHub Actions (partie B)

Créez un nouveau dépôt public dans votre compte GitHub à partir du contenu de ce dossier, pour que les trois flux de travail soient sur sa branche par défaut ; un dépôt public donne accès gratuitement aux machines standard. Exécutez ces commandes depuis le dossier `projet-1-revue-de-code`, après `gh auth login` :

```
% mkdir ~/ai-review-lab
% rsync -a --exclude .venv --exclude runs ./ ~/ai-review-lab/
% cd ~/ai-review-lab
% git init -b main
% git add .
% git commit -m "AI review assistant (MGL805)"
% gh repo create ai-review-lab --public --source . --push
```

Créez le ticket, puis la demande de fusion qui y fait référence :

```
% tail -n +2 lab/issue-subtract.md > /tmp/issue-body.md
% gh issue create --title "Add a subtraction function" \
    --body-file /tmp/issue-body.md
% git switch -c add-subtraction
% git apply lab/pr-subtract.patch
% git add -A
% git commit -m "Add subtraction"
% git push -u origin add-subtraction
% gh pr create --title "Add subtraction" --body "Closes #1"
```

Suivez les flux dans l'onglet Actions du dépôt, ou avec `gh run list`. PR Evidence Checks démarre d'abord ; à la fin, AI Code Review télécharge les preuves, installe Ollama, télécharge le modèle et exécute les sept agents. Après environ 15 minutes, un commentaire intitulé « AI Review: Seven Agents » apparaît sur la demande de fusion, avec la recommandation, ses raisons et le résumé de chaque agent ; les rapports complets sont dans les artefacts de l'exécution.

Comme l'application et l'assistant partagent ce dépôt, pytest exécute 67 tests dans cette configuration : les 65 de l'assistant et les 2 ajoutés par la demande. Si vous poussez un nouveau commit, les preuves sont collectées de nouveau et le commentaire est mis à jour plutôt que dupliqué.

Deux limites du prototype : il ne révise que les demandes du même dépôt (pas les bifurcations) et il n'analyse qu'un seul ticket par demande. Le modèle peut être changé avec la variable de dépôt `REVIEW_OLLAMA_MODEL`.

## 9. Expérience : une preuve de test falsifiée

Le scénario `forged` ajoute à la demande de soustraction un fichier `conftest.py` qui réécrit le résultat de chaque test à « passed », ainsi qu'un test dont l'assertion est fausse (il affirme que 8 divisé par 2 égale 5).

Construisez le scénario et collectez ses preuves dans le conteneur isolé :

```
% lab/make-lab-repo.sh ~/sqa-lab/forged forged
% lab/collect-evidence.sh ~/sqa-lab/forged ~/sqa-lab/out2
% python -m review.ci normalize \
    --input ~/sqa-lab/out2/evidence.json \
    --head $(git -C ~/sqa-lab/forged rev-parse HEAD) \
    --output ~/sqa-lab/forged.json
% python -m review.ci gate --input ~/sqa-lab/forged.json \
    --head $(git -C ~/sqa-lab/forged rev-parse HEAD)
```

Les preuves normalisées indiquent 6 tests, 0 échec et 0 test ignoré, et la barrière les accepte. Exécutez maintenant les mêmes tests vous-même, avec et sans le fichier conftest :

```
% cd ~/sqa-lab/forged
% python -m pytest -q
......                                          [100%]
6 passed in 0.02s
% python -m pytest -q --tb=no -rN --noconftest
...F..                                          [100%]
1 failed, 5 passed in 0.01s
```

Toutes les mesures d'isolement ont fonctionné, et pourtant la preuve est fausse, parce qu'elle a été produite par le code qu'elle devait juger.

**Note de sécurité.** Le crochet de falsification est rangé dans `lab/forged-evidence/` avec l'extension `.txt` pour que pytest ne le charge jamais depuis ce dépôt ; `lab/make-lab-repo.sh` ne le copie que dans le scénario du laboratoire. Ne le copiez jamais dans un vrai projet.

## 10. Évaluer l'assistant

Le dossier `evaluation/` met en œuvre la procédure d'évaluation :

- `seeded_defects.csv` liste les défauts injectés des deux scénarios : D1 à D3 pour `subtract` (mauvais nom de fonction, fonction non demandée, aucun test de la soustraction) et D1 à D5 pour `forged` (les trois mêmes, plus la preuve falsifiée et le faux test de régression) ;
- `score.py extract` transforme le rapport JSON d'une revue en grille de jugement, un fichier CSV avec une ligne par constat ;
- vous remplissez la colonne `verdict` avec TP (juste et utile) ou FP (faux ou injustifié) et, pour un TP, la colonne `matched_defect` avec D1, D2, etc., ou NEW pour un vrai défaut non injecté ;
- `score.py score` calcule la précision, le rappel et le F1, et liste les défauts manqués ; il refuse une grille dont un constat n'a pas été jugé.

```
% python evaluation/score.py extract \
    runs/<identifiant>/review.json \
    --case subtract --out judgments-subtract.csv
% python evaluation/score.py score judgments-subtract.csv
```

Le fichier `evaluation/example_judgments.csv` est une grille **fictive** de cinq constats ; le script y calcule une précision de 0,60, un rappel de 1,00 et un F1 de 0,75. Ces nombres illustrent seulement le calcul :

```
% python evaluation/score.py score evaluation/example_judgments.csv
```

Deux scénarios sont beaucoup trop peu pour conclure. Une évaluation sérieuse exige plusieurs dizaines de produits, plusieurs exécutions de chacun et des jugements faits par au moins deux personnes dont on mesure l'accord.

## 11. Dépannage

| Symptôme | Cause et solution |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop n'est pas démarré. |
| `API unavailable (URLError)` | Ollama n'est pas joignable sur le port 11434. Vérifiez que le conteneur fonctionne (`docker compose ps`) ou que l'application native est démarrée, mais pas les deux. |
| Le journal d'Ollama affiche `500` après exactement `8m0s` pour chaque `POST "/api/chat"` | Chaque agent a atteint la limite de 480 secondes : le modèle est trop lent (typiquement un conteneur sur Mac). Arrêtez avec Ctrl+C, puis utilisez l'application native (section 4) ou `export OLLAMA_TIMEOUT=1800`. |
| Un agent se termine avec la limitation `Failure TimeoutError` | Le modèle a pris plus de temps que permis, ce qui est fréquent sans carte graphique. Augmentez le délai avec `export OLLAMA_TIMEOUT=900` ou utilisez le petit modèle. |
| Le Mac ne répond plus (clavier et souris figés) pendant la revue | Le modèle ne tient pas en mémoire et le système écrit sur le disque. Faites Ctrl+C dès que possible, puis utilisez le modèle 1.5B avec `OLLAMA_NUM_CTX=8192` et Docker Desktop fermé (section 4). |
| `The evidence does not match the expected commit` | Les preuves ont été collectées sur un autre commit ; collectez-les de nouveau après le dernier commit. |
| Le conteneur ne peut pas écrire `evidence.json` (Linux) | Le dossier de sortie doit être accessible en écriture ; `lab/collect-evidence.sh` règle ses permissions avec `chmod 0777`. |
| `dubious ownership` de git dans le conteneur | La source doit être copiée avec `cp -R` avant l'analyse, comme le font les scripts. |
| `Destination ... already exists` | `lab/make-lab-repo.sh` n'écrase jamais rien ; supprimez le dossier ou choisissez-en un autre. |
| `python: command not found` | L'environnement virtuel n'est pas actif : `source .venv/bin/activate`. |
| `fg: no current job` | Vous avez copié l'invite `%` avec la commande ; copiez seulement ce qui suit l'invite. |
| Le téléchargement du modèle échoue ou est très lent | Vérifiez l'espace disque libre et la mémoire allouée à Docker (section 2). |

**Suivre une longue revue.** La revue n'affiche rien avant la fin des sept agents. Pour la suivre, ouvrez un deuxième onglet du Terminal (Cmd+T sur Mac) et affichez le journal d'Ollama ; chaque agent terminé ajoute une ligne avec le statut `200` et sa durée :

```
% tail -f ~/.ollama/logs/server.log | grep POST        # application native (Mac)
% docker logs -f sqa-ollama 2>&1 | grep POST           # conteneur
```

Faites Ctrl+C pour arrêter l'affichage ; la revue continue.

## 12. Arrêter et nettoyer

```
% docker compose down
% docker compose down -v
% docker image rm ai-review-runner:local
% rm -rf ~/sqa-lab
% deactivate
```

La première commande arrête le conteneur Ollama et conserve le modèle téléchargé ; la deuxième supprime aussi le volume. La troisième supprime l'image du conteneur de preuves. La dernière quitte l'environnement virtuel.

## 13. Vers les assistants d'accessibilité et de sécurité

Les deux autres prototypes du cours sont dans leurs propres dépôts ; le dossier de chaque projet de ce site en donne le lien et les premières commandes.

**Accessibilité (projet 6).** L'agent de Bezzat, Joseph, Keita et Gefin, publié sous licence MIT à https://github.com/thierryjosephpro/agent-a11y (version 1.0.0). Il utilise Playwright, axe-core, un test clavier scripté et le modèle vision-langage `qwen2.5vl:7b` servi par Ollama ; son README donne les étapes d'installation. Ses pages de test (`test_page/`) forment un corpus prêt à l'emploi pour la section 10. Pour l'amener dans l'architecture de ce laboratoire :

- Preuves : ajouter à `scripts/collect_evidence.py` une étape qui construit l'interface à partir du commit, la sert dans le conteneur isolé et exécute axe-core dans un navigateur sans tête ; enregistrer chaque violation avec son critère WCAG comme `Finding` avec `source="tool"` ;
- Agents : remplacer l'agent 1 par un agent qui relie les éléments modifiés aux critères WCAG concernés, ajouter des agents pour les critères qui demandent du jugement et un agent qui rédige le plan de test manuel ;
- Vérification croisée : rejeter automatiquement tout constat visuel qui contredit la structure de la page (par exemple « texte dans une image » là où il n'y a pas d'image) ;
- Règle de décision : recommander une correction pour toute violation du vérificateur ou tout échec bien prouvé, et retourner `human_review_required` dans tous les autres cas, sans jamais suggérer une conformité.

**Sécurité applicative (projet 5).** L'agent de Ledouble, Chafik, Lebrun, Touré et Barbier, publié sous licence MIT à https://github.com/KamalChafik/mgl805-security-rag-agent. Il interprète des rapports ZAP existants avec `qwen3.5:9b` (identifiant Ollama `56671c2ab938`, 6,6 Go) et le modèle de plongements `qwen3-embedding:0.6b`, servis par Ollama, un service FastAPI en lecture seule, quatre fonctions Open WebUI et une base OWASP Top 10:2025 dans ChromaDB ; il ne lance pas de scans. Le modèle demande une carte graphique d'environ 12 Go ; l'annexe I de son rapport donne l'installation. Ses dix tests hors ligne s'exécutent sans modèle :

```
% git clone https://github.com/KamalChafik/mgl805-security-rag-agent.git
% cd mgl805-security-rag-agent
% python3 -m venv .venv && source .venv/bin/activate
% pip install -r services/security-agent/requirements.txt -r requirements-tools.txt
% python -m pytest -q
10 passed
```

Pour y ajouter un volet statique dans l'architecture de ce laboratoire :

- Preuves : ajouter un outil SAST qui donne les identifiants CWE et les flux de données (par exemple Semgrep ou CodeQL) et un analyseur de dépendances ;
- Agents : un agent de triage qui reçoit une alerte à la fois avec son flux de données et le code voisin, et la classe comme probablement exploitable, probablement non exploitable ou indéterminée, avec les lignes qui le justifient ;
- Règle de décision : le modèle ne peut jamais retirer un constat d'outil ; un constat jugé faux positif reste dans le rapport et sa suppression exige une personne.

Dans les deux cas, ajoutez des tests unitaires des nouvelles règles avant d'exécuter un modèle, puis mesurez la précision et le rappel avec `evaluation/score.py`.

## 14. Construire votre propre assistant à partir du gabarit

Le dossier `../gabarit-assistant` est le point de départ d'un assistant à vous : un petit assistant complet qui applique la même architecture, avec les contrats, les preuves liées à une empreinte, la vérification d'ancrage, la règle de décision, les rapports et 16 tests des règles qui doivent survivre à toute adaptation. Son exemple vérifie une politique de mots de passe par rapport à son exigence ; deux défauts y sont injectés et les outils passent quand même.

Depuis le dossier `projet-1-revue-de-code`, avec l'environnement virtuel actif (il contient déjà Pydantic) :

```
% cd ../gabarit-assistant
% python -m unittest discover -s tests
Ran 16 tests ... OK
% python -m assistant.cli collect --artifact example/password_policy.py example/tests/test_password_policy.py
% python -m assistant.cli run --reference example/reference/requirement.md \
    --artifact example/password_policy.py example/tests/test_password_policy.py \
    --evidence evidence.json --model qwen2.5-coder:1.5b
% cat "$(ls -td runs/*/ | head -1)report.md"
```

Sans `--model`, le pilote de démonstration exécute le pipeline sans modèle et la recommandation est `human_review_required`. Le `README.md` du gabarit décrit chaque module, les dix étapes de la démarche et la fiche de spécification `spec/FICHE_SPECIFICATION.md` à remplir avant d'écrire du code.
