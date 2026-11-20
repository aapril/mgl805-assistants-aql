# Guide du projet 5 : agent de sécurité applicative

Ce guide explique comment fonctionne le prototype d'agent de sécurité applicative, comment l'essayer sans infrastructure, comment l'installer complètement et ce qu'une équipe peut améliorer. Il complète le README de l'équipe, dans [`code-depart/README.md`](code-depart/README.md), qui donne l'installation détaillée.

**Conventions.** Les commandes sont écrites pour un terminal Unix (Terminal de macOS, Linux ou WSL 2 sous Windows), sans l'invite : copiez-les une ligne à la fois. Sauf indication contraire, exécutez-les depuis le dossier `projet-5-securite/code-depart`.

## 1. Fonctionnement

Un scanner de sécurité dynamique comme ZAP produit des dizaines d'alertes. Chacune porte deux attributs indépendants : le **risque** (gravité si l'alerte est fondée : High, Medium, Low ou Informational) et la **confiance** (certitude du scanner). Interpréter un rapport demande de l'expertise : séparer risque et confiance, relier chaque alerte à sa faiblesse CWE, retrouver les recommandations OWASP et rédiger un compte rendu pour les développeurs. L'agent assiste ce travail avec un modèle exécuté localement, pour que les rapports de sécurité ne quittent jamais l'organisation.

| Composant | Rôle |
|---|---|
| ZAP et DVWA | Le scanner, et une application volontairement vulnérable qui sert de cible |
| Security Agent (FastAPI) | Lit les rapports JSON de ZAP dans un dossier monté en lecture seule ; cinq opérations en lecture seulement, aucun lancement de scan |
| OWASP Report Bridge | Quatre fonctions Python offertes au modèle dans Open WebUI : résumer le dernier rapport, lister les constats, détailler un constat, chercher dans la base OWASP |
| ChromaDB | Base vectorielle de l'OWASP Top 10:2025 (161 passages) |
| Ollama | `qwen3.5:9b` pour l'analyse et `qwen3-embedding:0.6b` pour les plongements, sur une machine avec carte graphique |
| Open WebUI | Interface de conversation, qui exécute les appels de fonctions du modèle |

Plusieurs contrôles sont placés dans le programme plutôt que dans les consignes au modèle :

- le risque et la confiance sont copiés du rapport dans deux champs distincts ;
- chaque constat porte la mention « Not independently validated », écrite par le service et non par le modèle ;
- l'identifiant d'un constat doit venir d'un appel précédent ;
- une recommandation n'est attribuée à OWASP que si elle figure dans un passage réellement retrouvé ;
- le modèle n'accède aux données que par les quatre fonctions, et chaque appel laisse une trace.

Le rapport de l'équipe distingue ce qui est **observé** (les données du scanner), **inféré** (l'interprétation du modèle) et **confirmé** (ce qu'un test distinct a vérifié). Seule la première catégorie est garantie par le système.

## 2. Essayer sans infrastructure (10 minutes)

Les tests et les scripts d'analyse fonctionnent sans modèle, sans scanner et sans Docker, sur un rapport ZAP synthétique. Prérequis : Python 3.11 ou plus récent.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-5-securite/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/security-agent/requirements.txt -r requirements-tools.txt
python -m pytest -q
python scripts/summarize_zap_report.py tests/fixtures/synthetic-zap.json
```

Les tests doivent afficher `10 passed`. Le script de résumé recalcule, sans modèle, ce que l'agent doit retrouver dans le rapport :

```
Distinct alerts: 2
Affected instances: 2
  High: 1
  Medium: 0
  Low: 1
  Informational: 0
Alerts require independent validation before being called confirmed vulnerabilities.
```

C'est l'oracle de la vérification : chaque nombre que le modèle affirme sur un rapport doit correspondre à ce que calcule ce script.

## 3. Installation complète

L'installation complète déploie six services Docker et demande une infrastructure plus importante que les autres projets :

- une machine virtuelle Linux (Ubuntu Server 24.04 recommandé) avec Docker Engine et Compose v2, 4 processeurs, 8 Go de mémoire et 60 Go de disque, pour Open WebUI, ChromaDB, Security Agent, ZAP, DVWA et MariaDB ;
- une machine distincte avec une carte graphique NVIDIA d'environ 12 Go et Ollama, joignable depuis la machine virtuelle, avec les modèles `qwen3.5:9b` (identifiant `56671c2ab938`, 6,6 Go) et `qwen3-embedding:0.6b` (identifiant `ac6da0dfba84`, 639 Mo).

Suivez les sections 3 à 12 du [README de l'équipe](code-depart/README.md) : fichier `.env`, vérification d'Ollama, démarrage avec `./start.sh`, configuration de DVWA, de ZAP et d'Open WebUI, création de la base de connaissances OWASP, installation du Report Bridge et import des rapports. Les adresses IP de ce README sont celles du laboratoire de l'équipe ; remplacez-les par les vôtres. Vérifiez avec `ollama list` que l'identifiant des modèles est le même : un même nom peut désigner une autre version plus tard.

**Règles de sécurité.** DVWA est volontairement vulnérable : ne l'exposez jamais sur Internet ni sur un réseau partagé. N'analysez que des systèmes pour lesquels vous avez une autorisation explicite. L'interface de pilotage de ZAP (port 8090) ne doit pas être publiée sur le réseau, et sa clé ne doit jamais apparaître dans une capture d'écran, un commit ou une conversation.

## 4. Valider une réponse de l'agent

L'équipe ne juge pas un essai sur la qualité du texte produit, qui peut sembler convaincant sans reposer sur rien. Trois vérifications sont systématiques :

- la requête envoyée par le navigateur contient `tool_ids: ["owasp_report_bridge"]` ;
- les fonctions attendues apparaissent dans les traces d'exécution d'Open WebUI, avec leurs paramètres ;
- chaque nombre et chaque identifiant cités dans la réponse correspondent au JSON brut du rapport (section 2).

Deux pièges observés par l'équipe : avec les outils intégrés d'Open WebUI activés, le modèle a appelé un outil de calendrier au lieu des fonctions ZAP ; avec une base de connaissances attachée automatiquement, il a répondu à partir des passages injectés sans jamais lire le rapport. La réponse avait l'air documentée, mais ne reposait sur aucune donnée réelle.

## 5. État du prototype et pistes d'amélioration

Les constats suivants viennent du rapport de l'équipe, de son README et de la lecture du code ; les tests et le script de résumé ont été exécutés le 20 novembre 2026.

| # | Constat | Effet |
|---|---|---|
| 1 | L'interface de pilotage de ZAP (port 8090) ne répond pas : la connexion est acceptée puis fermée sans réponse. | L'agent ne peut que lire des rapports existants ; il ne peut pas lancer de scan. |
| 2 | Le service de lancement de scans contrôlés (liste de cibles autorisées, mode passif par défaut, approbation humaine du mode actif, limites, journal d'audit) est seulement conçu. | L'orchestration des scans reste entièrement à construire. |
| 3 | La vérification des réponses (nombres et identifiants contre le JSON brut) se fait à la main. | Rien n'empêche une réponse d'affirmer un nombre faux ; elle peut être automatisée comme la vérification d'ancrage du projet 1. |
| 4 | Les trois passages OWASP retrouvés pour une requête viennent souvent du même document, avec des distances presque identiques. | Faible diversité des sources ; la recherche n'a pas été évaluée sur un jeu de questions de référence. |
| 5 | La base de connaissances se limite à l'OWASP Top 10:2025. | Pas de procédures de vérification (OWASP WSTG), ni de données CVE, CISA KEV ou EPSS. |
| 6 | Aucune comparaison avec un outil commercial n'a été faite : selon l'équipe, les modèles hébergés refusent souvent les demandes à caractère offensif. | Une comparaison limitée à l'interprétation de rapports existants, tâche non offensive, reste possible. |
| 7 | Les images Docker utilisent des étiquettes mobiles (`main`, `stable`, `latest`). | L'installation n'est pas reproductible dans le temps. |
| 8 | Le projet Docker Compose unifié n'a pas été déployé de bout en bout sur une machine vierge. | L'installation documentée n'est pas encore confirmée. |
| 9 | L'infrastructure demande une machine virtuelle et une carte graphique de 12 Go. | Difficile à reproduire sur un portable ; une variante avec un modèle plus petit serait utile pour le cours. |
| 10 | La ligne de droit d'auteur de la licence indique « MGL825 ». | À corriger par les noms des auteurs. |

## 6. Dépannage

Le README de l'équipe (section 13) couvre les problèmes d'Ollama, de ChromaDB, de DVWA, de ZAP et des clés d'Open WebUI. Deux points s'ajoutent pour le cours :

| Symptôme | Cause et solution |
|---|---|
| `fg: no current job` | Vous avez copié l'invite `%` avec la commande ; copiez seulement la commande. |
| `Model qwen3.5:9b not found` alors que le modèle est installé | Ollama n'est probablement pas joignable depuis le conteneur (adresse IP, pare-feu, écoute limitée à `127.0.0.1`), et non absent ; voir la section 4.3 du README de l'équipe. |
