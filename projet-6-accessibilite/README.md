# Projet 6 · Agent d'accessibilité

L'agent de Naoufel Bezzat, Thierry Carl-Henry Joseph, Alpha Kabinet Keita et Gabriel Gefin (automne 2026) évalue l'accessibilité d'une page web selon les critères WCAG, entièrement sur un portable, avec un modèle à poids ouverts. Une seule session de navigateur (Playwright) charge la page et alimente trois flux : un flux de code (axe-core) pour les violations que des règles peuvent décider, un flux clavier scripté (ordre et visibilité du focus, pièges clavier, fermeture d'une fenêtre modale par Échap) et un flux visuel qui soumet des captures d'écran au modèle vision-langage `qwen2.5vl:7b` servi par Ollama. Chaque constat est relié à son critère WCAG.

- **Guide d'utilisation, résultats et pistes d'amélioration** : [`GUIDE.md`](GUIDE.md)
- **Code de l'équipe et son README** : [`code-depart/`](code-depart/), copie du dépôt de l'équipe (licence MIT, version 1.0.0) : https://github.com/thierryjosephpro/agent-a11y

## Démarrage rapide (sans modèle)

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-6-accessibilite/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python run.py --no-visual test_page/index.html
```

La dernière commande audite la page de test en quelques secondes et produit une dizaine de constats des flux code et clavier ; le rapport est dans `output/rapport.html`. Pour le flux visuel, voir la section 3 du guide.

## Ce que le prototype enseigne

- Les flux déterministes (code et clavier) forment une base fiable ; le flux clavier révèle des défauts qu'aucun autre flux ne voit ;
- Le petit modèle local a signalé trois constats visuels sur une page conforme, et la stabilité de son compte reflétait la répétition du même verdict, pas sa justesse ;
- Une invite longue et restrictive a fait taire le modèle ; une invite courte et directive a débloqué la détection ;
- Le même modèle a donné des résultats différents sur deux machines : le couple modèle et matériel doit être traité comme une dépendance versionnée ;
- Chaque constat visuel doit être vérifié contre la structure de la page, et rejeté automatiquement s'il la contredit.
