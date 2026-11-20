# Projet 5 · Agent de sécurité applicative

L'agent de Clement Ledouble, Kamal Chafik, Leelou Lebrun, Coumba Leonie Samb Touré et Ted Barbier (automne 2026) aide à interpréter les rapports du scanner dynamique ZAP de façon traçable. Un modèle local (`qwen3.5:9b` servi par Ollama) n'accède aux données que par quatre fonctions : résumer le dernier rapport, lister ses constats, détailler un constat et chercher dans une base OWASP Top 10:2025 indexée dans ChromaDB. Un service FastAPI en lecture seule lit les rapports ; l'agent ne lance pas de scans.

- **Dépôt de l'équipe** : https://github.com/KamalChafik/mgl805-security-rag-agent
- **Installation complète** : le `README` du dépôt et l'annexe I du rapport de l'équipe. Le modèle demande une carte graphique d'environ 12 Go.

## Premiers pas sans modèle

Les dix tests hors ligne s'exécutent sans modèle ni scanner, sur un rapport ZAP synthétique :

```
git clone https://github.com/KamalChafik/mgl805-security-rag-agent.git
cd mgl805-security-rag-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/security-agent/requirements.txt -r requirements-tools.txt
python -m pytest -q
```

La dernière commande doit afficher `10 passed`. Le rapport synthétique est dans `tests/fixtures/synthetic-zap.json`.

## Ce que le prototype enseigne

- Les contrôles placés dans le programme (risque et confiance copiés du rapport, mention « not independently validated », identifiants obtenus d'un appel précédent) valent mieux que des consignes dans le prompt ;
- Un catalogue d'outils trop large a fait choisir au modèle un outil de calendrier au lieu des fonctions ZAP ;
- Une base de connaissances injectée automatiquement a produit une réponse d'apparence documentée qui ne reposait sur aucune lecture du rapport : il faut valider sur les traces d'exécution, pas sur la qualité du texte ;
- Le rapport doit séparer ce qui est observé (le scanner), inféré (le modèle) et confirmé (un test distinct) ;
- Le lancement de scans exige une liste de cibles autorisées, le mode passif par défaut, l'approbation humaine du mode actif et un journal d'audit, imposés par le serveur.

Pour ajouter un volet statique (SAST) dans l'architecture du projet 1, voir la section 13 de `../projet-1-revue-de-code/GUIDE.md`.
