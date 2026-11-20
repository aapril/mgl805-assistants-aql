# MGL805 · Assistants d'AQL fondés sur l'IA : site d'accompagnement

Site d'accompagnement des projets du cours **MGL805, Vérification et assurance qualité de logiciels**, à l'École de technologie supérieure (ÉTS), Montréal. Il contient le code, les instructions détaillées et les données de laboratoire (les énoncés des travaux sont publiés sur Moodle) des assistants d'assurance qualité logicielle construits par les équipes du cours, ainsi qu'un gabarit pour construire le vôtre.

Le rôle d'un groupe d'AQL n'est plus seulement d'auditer à la fin d'un projet : il fournit aussi aux développeurs des outils automatisés, et maintient des normes, des mesures et des audits légers pour s'assurer que ces outils sont bien utilisés. Les assistants de ce site appliquent tous la même architecture : l'artefact évalué n'est jamais digne de confiance, des outils déterministes produisent les preuves, un modèle à poids ouverts exécuté localement analyse ce que les outils ne peuvent pas décider, sous des contrats validés, une règle calcule la recommandation et une personne décide.

| Dossier | Contenu | Point de départ |
|---|---|---|
| [`projet-1-revue-de-code/`](projet-1-revue-de-code/) | Agent de revue de code : sept agents, preuves isolées, vérification d'ancrage, GitHub Actions, évaluation | [`GUIDE.md`](projet-1-revue-de-code/GUIDE.md) |
| [`projet-2-tests-interfaces/`](projet-2-tests-interfaces/) | Agent de tests d'interfaces : moteur RAG et affinage Qwen à compléter, passage de Balsamiq à Figma (code de départ d'Andrew Phillips) | [`GUIDE.md`](projet-2-tests-interfaces/GUIDE.md) |
| [`projet-3-tests-api/`](projet-3-tests-api/) | Agent de tests d'API : scénarios générés à partir d'une spécification OpenAPI, exécutés avec Pytest | [`GUIDE.md`](projet-3-tests-api/GUIDE.md) |
| [`projet-4-tests-performance/`](projet-4-tests-performance/) | Agent de tests de performance : Qwen planifie la charge et explique les résultats, le programme mesure et décide | [`GUIDE.md`](projet-4-tests-performance/GUIDE.md) |
| [`projet-5-securite/`](projet-5-securite/) | Agent d'interprétation traçable des rapports ZAP : modèle local, RAG sur l'OWASP Top 10, service en lecture seule | [`GUIDE.md`](projet-5-securite/GUIDE.md) |
| [`projet-6-accessibilite/`](projet-6-accessibilite/) | Agent d'accessibilité WCAG à trois flux : règles axe-core, test clavier scripté, modèle de vision local | [`GUIDE.md`](projet-6-accessibilite/GUIDE.md) |
| [`gabarit-assistant/`](gabarit-assistant/) | Gabarit pour construire votre propre assistant, avec sa fiche de spécification | [`README.md`](gabarit-assistant/README.md) |

## Environnement de travail

Les commandes sont écrites pour un terminal Unix : le Terminal de macOS ou de Linux, ou WSL 2 sous Windows. La plupart des projets demandent Git, Python 3.11 ou plus récent, Docker Desktop et Ollama. Un ordinateur de 8 Go de mémoire suffit avec les petits modèles (`qwen2.5-coder:1.5b`) ; les modèles de 7 milliards de paramètres demandent environ 16 Go. Sans ordinateur assez puissant, la partie B du projet 1 s'exécute entièrement sur les machines de GitHub.

## Livre

Le chapitre 5 du livre *Software Quality Assurance: Software Engineering Quality in the Age of AI, Automation, and Autonomous Systems* (Alain April, en préparation) présente ces prototypes en anglais ; son site d'accompagnement en anglais est distinct de celui-ci.

## Licences

Le matériel rédigé pour le cours est sous licence MIT (voir `LICENSE`). Le code repris des équipes conserve sa licence et ses avis de droit d'auteur, indiqués dans son dossier. Les données du projet 2 appartiennent au projet MiBioKey du CRCHUM et ne sont pas publiées dans ce site.
