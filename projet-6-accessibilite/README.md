# Projet 6 · Agent d'accessibilité

L'agent de Naoufel Bezzat, Thierry Carl-Henry Joseph, Alpha Kabinet Keita et Gabriel Gefin (automne 2026) évalue l'accessibilité d'une page web entièrement sur un portable, avec un modèle à poids ouverts. Une seule session de navigateur (Playwright) charge la page et alimente trois flux : un flux de code (axe-core) pour les violations que des règles peuvent décider, un flux clavier scripté (ordre et visibilité du focus, pièges clavier, fermeture d'une fenêtre modale par Échap) et un flux visuel qui soumet des captures d'écran au modèle vision-langage `qwen2.5vl:7b` servi par Ollama. Chaque constat est relié à son critère WCAG.

- **Dépôt de l'équipe (licence MIT, version 1.0.0)** : https://github.com/thierryjosephpro/agent-a11y
- **Installation** : le `README` du dépôt. Les pages de test avec défauts injectés sont dans `test_page/`.

## Ce que le prototype enseigne

- Les flux déterministes (code et clavier) forment une base fiable ; le flux clavier révèle des défauts qu'aucun autre flux ne voit ;
- Le petit modèle local a signalé trois constats visuels sur une page conforme, et la stabilité de son compte reflétait la répétition du même verdict, pas sa justesse ;
- Une invite longue et restrictive a fait taire le modèle ; une invite courte et directive a débloqué la détection ;
- Le même modèle a donné des résultats différents sur deux machines : le couple modèle et matériel doit être traité comme une dépendance versionnée ;
- Chaque constat visuel doit être vérifié contre la structure de la page, et rejeté automatiquement s'il la contredit.

Pour amener ces flux dans l'architecture du projet 1, voir la section 13 de `../projet-1-revue-de-code/GUIDE.md`.
