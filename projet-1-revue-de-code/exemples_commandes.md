# Commandes du laboratoire (projet 1)

Toutes les commandes de `GUIDE.md`, dans l'ordre, regroupées par section. Les commandes sont écrites sans l'invite `%` : copiez-les telles quelles, une ligne à la fois (les lignes qui commencent par des espaces continuent la ligne précédente).

## 2. Prérequis

```
git --version
python3 --version
docker --version
```

## 3. Installation

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-1-revue-de-code
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[lab]"
chmod +x verify.sh lab/*.sh
```

```
brew install --cask ollama
open -a Ollama
ollama pull qwen2.5-coder:7b
```

```
docker compose up -d
docker compose exec ollama ollama pull qwen2.5-coder:7b
```

```
docker build -f Dockerfile.runner -t ai-review-runner:local .
```

## 5. Vérifier l'installation

```
python -m unittest discover -s tests
```

```
python -m review.cli demo
```

```
ollama list                                # application native
docker compose exec ollama ollama list     # conteneur
```

```
./verify.sh
```

```
RUN_MODEL=1 ./verify.sh
```

## 6. Charger les données du laboratoire

```
lab/make-lab-repo.sh ~/sqa-lab/subtract subtract
```

```
lab/collect-evidence.sh ~/sqa-lab/subtract ~/sqa-lab/out
```

```
python -m review.ci normalize \
    --input ~/sqa-lab/out/evidence.json \
    --head $(git -C ~/sqa-lab/subtract rev-parse HEAD) \
    --output ~/sqa-lab/subtract.json
```

```
python -m review.ci gate --input ~/sqa-lab/subtract.json \
    --head $(git -C ~/sqa-lab/subtract rev-parse HEAD)
```

## 7. Exécuter les sept agents (exemple commenté)

```
python -m review.cli local \
    --issue-file lab/issue-subtract.md \
    --diff ~/sqa-lab/subtract.diff \
    --evidence ~/sqa-lab/subtract.json
```

```
cat "$(ls -td runs/*/ | head -1)report.md"
```

## 8. Exécuter l'assistant dans GitHub Actions (partie B)

```
mkdir ~/ai-review-lab
rsync -a --exclude .venv --exclude runs ./ ~/ai-review-lab/
cd ~/ai-review-lab
git init -b main
git add .
git commit -m "AI review assistant (MGL805)"
gh repo create ai-review-lab --public --source . --push
```

```
tail -n +2 lab/issue-subtract.md > /tmp/issue-body.md
gh issue create --title "Add a subtraction function" \
    --body-file /tmp/issue-body.md
git switch -c add-subtraction
git apply lab/pr-subtract.patch
git add -A
git commit -m "Add subtraction"
git push -u origin add-subtraction
gh pr create --title "Add subtraction" --body "Closes #1"
```

## 9. Expérience : une preuve de test falsifiée

```
lab/make-lab-repo.sh ~/sqa-lab/forged forged
lab/collect-evidence.sh ~/sqa-lab/forged ~/sqa-lab/out2
python -m review.ci normalize \
    --input ~/sqa-lab/out2/evidence.json \
    --head $(git -C ~/sqa-lab/forged rev-parse HEAD) \
    --output ~/sqa-lab/forged.json
python -m review.ci gate --input ~/sqa-lab/forged.json \
    --head $(git -C ~/sqa-lab/forged rev-parse HEAD)
```

```
cd ~/sqa-lab/forged
python -m pytest -q
python -m pytest -q --tb=no -rN --noconftest
```

## 10. Évaluer l'assistant

```
python evaluation/score.py extract \
    runs/<identifiant>/review.json \
    --case subtract --out judgments-subtract.csv
python evaluation/score.py score judgments-subtract.csv
```

```
python evaluation/score.py score evaluation/example_judgments.csv
```

## 11. Dépannage

```
tail -f ~/.ollama/logs/server.log | grep POST        # application native (Mac)
docker logs -f sqa-ollama 2>&1 | grep POST           # conteneur
```

## 12. Arrêter et nettoyer

```
docker compose down
docker compose down -v
docker image rm ai-review-runner:local
rm -rf ~/sqa-lab
deactivate
```

## 13. Vers les assistants d'accessibilité et de sécurité

```
git clone https://github.com/KamalChafik/mgl805-security-rag-agent.git
cd mgl805-security-rag-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r services/security-agent/requirements.txt -r requirements-tools.txt
python -m pytest -q
```

## 14. Construire votre propre assistant à partir du gabarit

```
cd ../gabarit-assistant
python -m unittest discover -s tests
python -m assistant.cli collect --artifact example/password_policy.py example/tests/test_password_policy.py
python -m assistant.cli run --reference example/reference/requirement.md \
    --artifact example/password_policy.py example/tests/test_password_policy.py \
    --evidence evidence.json --model qwen2.5-coder:1.5b
cat "$(ls -td runs/*/ | head -1)report.md"
```
