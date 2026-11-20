# Projet 2 · Agent « libre de droits » de tests d'interfaces utilisateurs

## Mise en contexte

Concevez un agent « libre de droits » qui génère et vérifie des tests d'interfaces utilisateurs d'un logiciel. Le projet se fait en collaboration avec l'équipe MiBioKey du Centre de recherche du CHUM (CRCHUM), qui développe une plateforme de gestion de biobanques. Ses récits Jira, ses cas de test Zephyr et ses maquettes sont les données du projet, et ses analystes en sont l'oracle. L'équipe MiBioKey a décidé de passer de Balsamiq à Figma pour ses maquettes : l'agent doit suivre ce changement.

Vous poursuivez les travaux d'Andrew Phillips (été 2026), qui constituent surtout un moteur d'IA à intégrer dans un agent fonctionnel : préparation des données Jira, Zephyr et Balsamiq, plongements vectoriels avec pgvector dans Supabase et code d'affinage (fine-tuning) d'un modèle Qwen multimodal pour la génération de cas de test.

## Point de départ

Le code ingère les récits et les cas de test dans Supabase et calcule leurs plongements, mais il ne s'agit pas encore d'un agent :

- le pipeline d'inférence et de RAG n'existe pas ;
- l'affinage n'a été exécuté qu'une fois, sans jeu de validation, et ses adaptateurs ne sont plus disponibles ;
- l'environnement virtuel et les accès Supabase ne sont pas fournis : votre équipe utilise son propre projet Supabase ;
- l'ingestion s'exécute sans erreur, alors que les critères d'acceptation et les étapes des cas de test arrivent vides dans la base et dans les plongements (guide, section 6).

## Collaboration avec l'équipe MiBioKey

- Les données vous sont remises selon les conditions de l'équipe MiBioKey (guide, section 8) : elles restent hors de tout dépôt public et de tout service d'IA infonuagique ;
- Les questions sur les exigences, les maquettes et les cas de test passent par l'équipe MiBioKey ;
- Les cas de test générés sont revus par les analystes de l'équipe MiBioKey, qui jugent s'ils sont justes et utiles ; ce jugement sert au calcul de la précision ;
- Les résultats sont présentés à l'équipe MiBioKey en fin de session, avec seulement les extraits qu'elle a approuvés.

## Travail demandé

Le projet est calibré pour une petite équipe pendant une session. L'affinage du modèle et l'exécution automatique des tests sont **hors du périmètre obligatoire** : ils ne sont utiles que si la version sans affinage est déjà mesurée.

### Jalon 1 · Remettre le moteur en état (semaines 1 à 4)

- Installer le code avec votre propre Supabase et documenter chaque étape dans un guide reproductible ;
- Corriger les constats 1 à 5 de la section 6 du guide (critères d'acceptation vides, étapes vides, noms de colonnes et de tables, fuite des données de validation), chacun avec un test unitaire qui échoue avant la correction et réussit après ;
- Séparer les cas d'utilisation en deux jeux : un jeu pour le RAG et un jeu d'évaluation que le RAG ne voit jamais.

### Jalon 2 · Lire les maquettes Figma (semaines 5 à 7)

- Écrire un script qui exporte une seule fois, avec l'API REST de Figma, les cadres utiles des maquettes MiBioKey en images et le texte de leurs nœuds (libellés, champs, boutons), dans un cache local (guide, section 9) ;
- Ingérer ces maquettes dans Supabase, en gardant l'origine de chacune (Balsamiq ou Figma), et relier chaque récit Jira aux cadres qu'il concerne ;
- Gérer le jeton Figma comme la clé Supabase : portée en lecture seule, jamais dans le code ni dans Git.

### Jalon 3 · Générer des cas de test avec le RAG (semaines 8 à 11)

- Construire le pipeline d'inférence : à partir d'un récit Jira, retrouver les récits et cas de test semblables, puis générer des cas de test au format Zephyr avec un modèle local de base, sans affinage ;
- Valider chaque réponse du modèle contre un schéma strict ;
- Ancrer chaque cas généré : il cite le critère d'acceptation qu'il vérifie, et chaque libellé cité doit exister dans le texte des nœuds Figma ; cette vérification est faite par programme, pas par le modèle.

### Jalon 4 · Mesurer avec l'équipe MiBioKey (semaines 12 à 14)

- Générer les cas de test des récits du jeu d'évaluation et les soumettre aux analystes de l'équipe MiBioKey, qui jugent chaque cas juste et utile ou non ;
- Calculer la précision, la couverture des critères d'acceptation et la proportion de libellés ancrés, sur au moins deux exécutions ;
- Présenter les résultats à l'équipe MiBioKey, avec seulement les extraits qu'elle a approuvés.

### Pour aller plus loin (facultatif)

- Reprendre l'affinage du modèle Qwen multimodal avec le jeu d'évaluation du jalon 1, et le comparer à la version sans affinage ;
- Traduire les cas retenus en scripts Playwright exécutés sur un environnement de test de MiBioKey, en vérifiant chaque sélecteur contre le DOM réel.

## Livrables

- Le code dans un dépôt public sous licence MIT, avec un guide d'installation en français, sans les données de MiBioKey ni aucune clé ;
- Les tests unitaires des corrections et des règles, écrits avant d'exécuter un modèle ;
- Les grilles de jugement des analystes et les mesures du jalon 4 ;
- Un rapport court qui distingue ce qui a été observé, ce qui a été mesuré et ce qui reste à faire pour l'équipe suivante.

## Ressources du site d'accompagnement

- [Guide d'installation et état du code de départ](GUIDE.md), en particulier la section 6 (dix constats vérifiés) et la section 9 (passage à Figma) ;
- [Schéma Supabase reconstitué](schema.sql) et [cas d'utilisation fictif UC-00](exemple-donnees/training_data/UC-00/) ;
- [Code de départ d'Andrew Phillips](code-depart/) et son [README d'origine](code-depart/README_MGL805.md) ;
- [Gabarit pour construire un assistant](../gabarit-assistant/) et sa [fiche de spécification](../gabarit-assistant/spec/FICHE_SPECIFICATION.md) ;
- [Projet 1](../projet-1-revue-de-code/GUIDE.md), exemple complet d'architecture, de vérification d'ancrage et d'évaluation.
