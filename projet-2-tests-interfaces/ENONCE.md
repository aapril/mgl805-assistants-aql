# Projet 2 · Agent « libre de droits » de tests d'interfaces utilisateurs

Concevez un agent « libre de droits » qui génère et vérifie des tests d'interfaces utilisateurs d'un logiciel. Le projet se fait en collaboration avec l'équipe MiBioKey du Centre de recherche du CHUM (CRCHUM), qui développe une plateforme de gestion de biobanques : ses récits Jira, ses cas de test Zephyr et ses maquettes sont les données du projet, et ses analystes en sont l'oracle. L'équipe MiBioKey a décidé de passer de Balsamiq à Figma pour ses maquettes : l'agent doit suivre ce changement. Vous poursuivez les travaux d'Andrew Phillips (été 2026), qui constituent surtout un moteur d'IA à intégrer dans un agent fonctionnel : préparation des données Jira, Zephyr et Balsamiq, plongements vectoriels avec pgvector et code d'affinage d'un modèle Qwen multimodal pour la génération de cas de test.

## Ressources du site d'accompagnement

- [Guide d'installation et état du code de départ](GUIDE.md), en particulier la section 6 (dix constats vérifiés) ;
- [Schéma Supabase reconstitué](schema.sql) et [cas d'utilisation fictif UC-00](exemple-donnees/training_data/UC-00/) ;
- [Code de départ d'Andrew Phillips](code-depart/) et son [README d'origine](code-depart/README_MGL805.md) ;
- [Gabarit pour construire un assistant](../gabarit-assistant/) et sa [fiche de spécification](../gabarit-assistant/spec/FICHE_SPECIFICATION.md) ;
- [Projet 1, exemple complet](../projet-1-revue-de-code/GUIDE.md) d'architecture, de vérification d'ancrage et d'évaluation.

## Point de départ

Le code ingère les récits et les cas de test dans Supabase et calcule leurs plongements, mais il ne s'agit pas encore d'un agent. Le pipeline d'inférence et de RAG n'existe pas. L'affinage n'a été exécuté qu'une fois, sans jeu de validation, et ses adaptateurs ne sont plus disponibles. L'environnement virtuel et les accès Supabase ne sont pas fournis : votre équipe utilise son propre projet Supabase. Surtout, l'ingestion s'exécute sans erreur alors que les critères d'acceptation et les étapes des cas de test arrivent vides dans la base et dans les plongements (guide, section 6).

## Collaboration avec l'équipe MiBioKey

- Les données réelles vous sont remises selon les conditions de l'équipe MiBioKey (guide, section 8) : elles restent hors de tout dépôt public et de tout service d'IA infonuagique ;
- Les questions sur les exigences, les maquettes et les cas de test passent par l'équipe MiBioKey ;
- Les cas de test générés sont revus par les analystes de l'équipe MiBioKey, qui jugent s'ils sont justes et utiles : ce jugement sert au calcul de la précision ;
- Les résultats sont présentés à l'équipe MiBioKey en fin de session, avec seulement les extraits qu'elle a approuvés.

## Travail demandé

- Installer le code avec votre propre Supabase et documenter chaque étape dans un guide reproductible ;
- Corriger les constats de la section 6 du guide, chacun avec un test unitaire qui échoue avant la correction ;
- Passer de Balsamiq à Figma : extraire, avec l'API REST de Figma, les cadres des maquettes MiBioKey en images et le texte de leurs nœuds (libellés, champs, boutons), les ingérer dans Supabase et les intégrer au RAG, en gardant les maquettes Balsamiq des récits existants le temps de la transition (guide, section 9) ;
- Relier chaque récit Jira aux cadres Figma qu'il concerne (clé du fichier et identifiant du nœud), pour que la traçabilité récit, maquette, cas de test soit vérifiable ;
- Gérer le jeton Figma comme la clé Supabase : portée en lecture seule, jamais dans le code ni dans Git, et exporter une seule fois les maquettes dans un cache local, car l'API limite le nombre de requêtes ;
- Construire le pipeline d'inférence : à partir d'un récit Jira, retrouver les récits, cas de test et maquettes semblables, puis générer des cas de test au format Zephyr ;
- Établir une référence sans affinage (modèle Qwen multimodal de base avec RAG), puis reprendre l'affinage avec une partition entraînement, validation et test, et comparer les deux ;
- Traduire les cas de test générés en scripts Playwright exécutés sur une application de démonstration : le modèle propose, l'exécution tranche ;
- Ancrer chaque cas généré : il cite le critère d'acceptation et les éléments de la maquette qu'il vérifie ; chaque libellé cité doit exister dans le texte des nœuds Figma, et chaque sélecteur est vérifié contre le DOM réel avant l'exécution ;
- Prévenir les deux risques connus de cette famille d'agents : des oracles recopiés du comportement actuel au lieu de l'exigence, et des sélecteurs « auto-réparés » qui masquent une régression ;
- Mesurer sur un corpus : couverture des critères d'acceptation, proportion de cas exécutables, défauts injectés dans l'interface qui sont détectés, sur plusieurs exécutions ;
- Exiger qu'une personne revoie chaque cas généré avant qu'il entre dans la suite de tests ; ici, cette personne est un analyste de l'équipe MiBioKey.

## Livrables

- Le code dans un dépôt public sous licence MIT, avec un guide d'installation en français, **sans les données de MiBioKey** ni aucune clé ;
- Des tests unitaires pour chaque correction et chaque règle, écrits avant d'exécuter un modèle ;
- Le corpus, les grilles de jugement et les mesures, avec et sans affinage ;
- Un rapport qui distingue ce qui a été observé, ce qui a été mesuré et ce qui reste à démontrer.
