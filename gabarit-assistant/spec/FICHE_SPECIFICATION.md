# Fiche de spécification d'un assistant d'AQL

Remplissez cette fiche **avant** d'écrire du code. Chaque réponse en italique est celle de l'exemple de ce dossier, l'assistant de conformité aux exigences ; remplacez-la par la vôtre.

## 1. Problème et utilisateurs

- Quelle tâche récurrente des développeurs ou des réviseurs l'assistant soutient-il ? Où perd-on du temps ou laisse-t-on passer des défauts aujourd'hui ?
  *Les réviseurs vérifient à la main qu'une modification satisfait l'exigence qu'elle implante ; les défauts d'exigence que les tests ne révèlent pas passent.*
- Qui lit sa sortie, et qu'en fait cette personne ?
  *Le réviseur de la modification, qui accepte ou rejette chaque constat.*
- À quelle famille d'agents appartient-il (revue de code, génération de tests, triage de bogues, conformité et préparation de livraison, sécurité) ?
  *Revue de code tenant compte du contexte.*

## 2. Oracle

- Par rapport à quoi juge-t-on qu'un résultat est « correct » ? Nommez les documents et leur version.
  *L'exigence de la modification (`example/reference/requirement.md`), avec des exigences numérotées REQ-n.*
- L'oracle est-il assez précis pour qu'une personne puisse décider ? Sinon, corrigez d'abord l'oracle.
  *Oui : chaque exigence est vérifiable.*

## 3. Preuves déterministes

- Que peuvent déjà décider les outils ? Listez chaque outil, ce qu'il vérifie et sa configuration.
  *La syntaxe (`py_compile`) et les tests unitaires de l'artefact. Les deux passent sur l'exemple, alors que deux défauts y sont injectés : les outils ne peuvent pas les voir.*
- Où les outils s'exécutent-ils, et l'artefact peut-il influencer leurs résultats ?
  *Ici, sur l'ordinateur du développeur. Dans un pipeline : un conteneur isolé, sans secrets ni réseau ; les tests restent sous le contrôle de l'artefact.*

## 4. Ce que le modèle ajoute

- Pour chaque agent : la question étroite à laquelle il répond, les entrées qu'il peut voir et ce qu'il ne doit jamais faire.
  *Agent `criteria` : extraire les exigences en lisant seulement la référence. Agent `conformance` : juger chaque critère par rapport à l'artefact en citant l'artefact ; ne jamais contredire un outil.*

## 5. Modèle et lieu d'exécution

- Modèles candidats (licence, taille, fenêtre de contexte) et ordinateurs disponibles.
  *qwen2.5-coder:1.5b sur un portable de 8 Go ; qwen2.5-coder:7b avec 16 Go.*
- Les données peuvent-elles quitter l'organisation ? *Non.*

## 6. Contrats et ancrage

- Quels champs le modèle remplit-il, et lesquels appartiennent au programme ? *Le programme possède `source`, `grounded` et la décision.*
- Que peut-on vérifier mécaniquement dans les réponses du modèle ? *Chaque citation de l'artefact et de la référence ; chaque critère recopié de la référence.*

## 7. Capacités et droits

- De quelles fonctions, fichiers, réseaux et accès l'assistant a-t-il besoin ? N'accordez rien d'autre.
  *Lire l'artefact et la référence ; appeler le modèle local. Aucune écriture, aucun réseau au-delà du serveur du modèle, aucun identifiant.*

## 8. Règle de décision et ce que l'assistant ne doit jamais faire

- Quand recommande-t-il des corrections ? Quand exige-t-il une revue humaine ? Quand peut-il dire « prêt pour l'approbation humaine » ?
  *Voir `assistant/decision.py`.*
- Que ne doit-il jamais faire ? *Approuver, fusionner ou supprimer un résultat d'outil.*

## 9. Corpus et mesures

- Défauts injectés, artefacts corrects et tentatives de manipulation.
  *`evaluation/seeded_defects.csv` : D1 (longueur minimale de 8 au lieu de 12) et D2 (aucun test d'un mot de passe sans chiffre).*
- Seuils de précision et de rappel exigés avant l'utilisation, et nombre d'exécutions.
  *À fixer par le groupe d'AQL, par exemple un rappel d'au moins 0,8 sur le corpus avant toute utilisation dans un pipeline.*

## 10. Configuration et plan d'AQL

- Versions enregistrées avec chaque rapport : code, instructions, modèle et son empreinte, outils, seuils.
- Qui approuve un changement de modèle ou d'instructions, et comment l'assistant figure-t-il dans le plan d'AQL ?
