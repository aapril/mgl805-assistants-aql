# Guide du projet 6 : agent d'accessibilité

Ce guide explique comment fonctionne le prototype d'agent d'accessibilité, comment l'essayer, ce que montrent ses résultats et ce qu'une équipe peut améliorer. Il complète le README de l'équipe, dans [`code-depart/README.md`](code-depart/README.md), qui détaille toutes les options.

**Conventions.** Les commandes sont écrites pour un terminal Unix (Terminal de macOS, Linux ou WSL 2 sous Windows), sans l'invite : copiez-les une ligne à la fois. Sauf indication contraire, exécutez-les depuis le dossier `projet-6-accessibilite/code-depart`, avec l'environnement virtuel activé.

## 1. Fonctionnement

L'agent évalue l'accessibilité d'une page web selon les critères WCAG, entièrement sur l'ordinateur de l'utilisateur. Une seule session de navigateur (Playwright) charge la page et alimente trois flux :

| Flux | Nature | Ce qu'il trouve |
|---|---|---|
| Code | Déterministe : axe-core injecté dans la page | Ce que des règles peuvent décider : contraste, texte alternatif absent, étiquettes, attributs ARIA, zoom désactivé |
| Clavier | Déterministe : parcours scripté avec la touche Tab | Ordre et visibilité du focus, pièges clavier, fenêtre modale qui ne se ferme pas avec Échap |
| Visuel | Modèle vision-langage local (`qwen2.5vl:7b` par Ollama) | Ce qui demande une perception : information portée par la couleur seule, texte dans une image, hiérarchie visuelle trompeuse |

L'enchaînement est fixe : l'équipe insiste sur le fait qu'il s'agit d'un flux de travail outillé, et non d'un agent autonome, parce qu'un outil de test doit être reproductible. Chaque constat, de chaque flux, est validé contre un schéma strict ; sa source est fixée par le programme, jamais par le modèle ; il est relié à son critère WCAG et à son niveau (A, AA, AAA). L'agrégation fusionne et ordonne les constats, puis écrit un rapport Markdown, un rapport HTML et un fichier JSON. Chaque exécution est journalisée avec sa configuration, son modèle et ses durées.

Un commutateur permet d'appeler un modèle commercial (Claude ou Gemini) à la place du modèle local, pour servir d'instrument de comparaison seulement.

## 2. Essayer sans modèle (10 minutes)

Les flux code et clavier fonctionnent sans Ollama. Prérequis : Python 3.10 ou plus récent.

```
git clone https://github.com/aapril/mgl805-assistants-aql.git
cd mgl805-assistants-aql/projet-6-accessibilite/code-depart
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python run.py --no-visual test_page/index.html
```

La dernière commande audite la page de test livrée avec le projet, qui contient des défauts injectés. Le 20 novembre 2026, elle a duré 5 secondes et produit 10 constats (7 du flux code, 3 du flux clavier) : deux images sans texte alternatif, trois contrastes insuffisants, un zoom désactivé, un lien sans texte, une fenêtre modale qui ne se ferme pas avec Échap, et le focus qui ne se déplace pas vers la modale. Les rapports sont dans le dossier `output/` :

```
open output/rapport.html
```

## 3. Exécution avec le modèle de vision

```
ollama pull qwen2.5vl:7b
python run.py test_page/index.html
```

Le modèle occupe environ 6 Go ; il demande un ordinateur de 16 Go de mémoire, ou une carte graphique. Sur un Mac de 8 Go, gardez l'option `--no-visual`. Les options de découpage des pages longues en tuiles (`AGENT_TILING`, `TILING_STRATEGY`) et la comparaison avec un modèle commercial sont décrites aux sections 4 à 7 du README de l'équipe. Les clés des API commerciales se donnent par variables d'environnement, jamais dans le code.

## 4. Ce que l'évaluation de l'équipe a montré

L'équipe a évalué le prototype sur trois pages : une page de test avec treize défauts injectés, une page publique conforme (pour mesurer les faux positifs) et la démonstration « Before and After » du W3C, chacune exécutée plusieurs dizaines de fois avec le modèle local et avec un modèle commercial.

- Les flux déterministes forment une base fiable : le flux code détecte les défauts de balisage de façon reproductible, et le flux clavier révèle des défauts qu'aucun autre flux ne voit, comme le piège clavier.
- Le modèle local était de trois à cinq fois plus lent que le modèle commercial.
- Il a signalé trois constats visuels sur la page conforme, où il n'y en avait aucun ; la stabilité de son compte reflétait la répétition du même verdict, pas sa justesse. Selon l'équipe, le petit modèle « récite des règles génériques » au lieu d'observer la capture.
- Une invite longue et restrictive a fait taire le modèle ; une invite courte et directive a débloqué la détection.
- Le même modèle, avec les mêmes poids, a donné des résultats différents sur une machine avec carte NVIDIA et sur un portable avec processeur graphique Intel : le couple modèle et matériel doit être traité comme une dépendance versionnée.

## 5. État du prototype et pistes d'amélioration

| # | Constat | Effet |
|---|---|---|
| 1 | Le projet n'a aucun test unitaire. | Les règles de validation, d'agrégation et de rattachement aux critères WCAG ne sont protégées contre aucune régression. |
| 2 | Les constats visuels ne sont pas vérifiés contre la structure de la page. | Un constat comme « texte dans une image » peut être retenu là où la page ne contient aucune image ; l'équipe recommande elle-même de rejeter automatiquement ces contradictions. |
| 3 | Le modèle local produit des faux positifs sur une page conforme. | Le flux visuel ne peut pas être utilisé seul ; ses constats doivent être revus par une personne. |
| 4 | Aucune règle de décision ne résume l'audit. | Le rapport liste des constats, mais ne dit pas si la page doit être corrigée ou revue par une personne ; il ne doit jamais affirmer une conformité. |
| 5 | Le flux visuel ne propose pas de textes alternatifs, et rien n'encadre une telle proposition. | Un texte alternatif fluide mais faux est pire qu'un texte absent : il ne déclenche plus aucune règle. |
| 6 | Le lanceur fourni (`start-ollama.bat`) et une partie des instructions visent Windows. | L'installation sur macOS et Linux est moins documentée. |
| 7 | Le nom du modèle commercial de comparaison est réglé par défaut à `gemini-3.6-flash`, alors que le rapport de l'équipe mentionne Gemini 3.7 Flash. | La version exacte utilisée pour l'évaluation est à confirmer. |
| 8 | La licence nomme trois auteurs, alors que le rapport de l'équipe en nomme quatre (Gabriel Gefin n'y figure pas). | À confirmer avec l'équipe. |

## 6. Dépannage

| Symptôme | Cause et solution |
|---|---|
| `pip install` échoue sur `jsonschema` | Python est trop ancien : il faut Python 3.10 ou plus récent. |
| `Executable doesn't exist` au lancement de Playwright | Le navigateur n'est pas installé : `python -m playwright install chromium`. |
| Le flux visuel est sauté ou échoue | Ollama n'est pas démarré ou `qwen2.5vl:7b` n'est pas téléchargé (`ollama list`) ; le rapport des flux code et clavier est quand même produit. |
| Le flux visuel ne retourne aucun constat sur une page longue | Voir les options de découpage en tuiles dans le README de l'équipe (section 5) et `GUIDE_TEST_TUILAGE.md`. |
| `fg: no current job` | Vous avez copié l'invite `%` avec la commande ; copiez seulement la commande. |
