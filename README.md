# Mini-projet : Développer et déployer une API REST dans le Cloud

Cette API permet à une école d'ingénieurs de gérer les stages de ses étudiants :
création, consultation, modification et suppression. Les exemples utilisent
uniquement des données fictives. Swagger et Postman permettent de tester l'API.

Technologies : Python 3.12, FastAPI, Pydantic, SQLite, SQLAlchemy, Uvicorn,
Docker, GitHub et Render. Les tests utilisent pytest et le client de test FastAPI.

## Fichiers

```text
.
├── main.py           # Application, démarrage et cinq endpoints REST
├── database.py       # Connexion SQLite et sessions SQLAlchemy
├── models.py         # Table stages et ses six colonnes
├── schemas.py        # Validation Pydantic et schéma des réponses
├── requirements.txt  # Versions des dépendances directes
├── test_main.py      # Tests sur une base SQLite temporaire
├── api-stages.postman_collection.json # Requêtes et tests à importer dans Postman
├── Dockerfile        # Construction de l'image et démarrage Uvicorn
├── .dockerignore     # Fichiers exclus du contexte Docker
├── .gitignore        # Fichiers locaux exclus de Git
└── README.md         # Installation, utilisation et déploiement
```

`stages.db` et la table `stages` sont créés automatiquement au démarrage, à côté
de `database.py`. Cette base locale et l'environnement `.venv` sont exclus de Git
et de l'image Docker. Chaque conteneur crée sa propre base dans `/app/stages.db`.

## Installation et démarrage local

Prérequis : Python 3.12 avec le module `venv`. Exécuter les commandes depuis le
dossier contenant `main.py` :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger : <http://localhost:8000/docs>.
Liste JSON : <http://localhost:8000/stages>.
Spécification OpenAPI : <http://localhost:8000/openapi.json>.
Arrêter le serveur avec `Ctrl+C`.

## Endpoints

| Méthode | Chemin | Résultat |
| --- | --- | --- |
| GET | `/stages` | `200` : liste des stages, ou `[]` |
| GET | `/stages/{id}` | `200` : stage trouvé ; `404` : introuvable |
| POST | `/stages` | `201` : stage créé avec son identifiant |
| PUT | `/stages/{id}` | `200` : stage modifié ; `404` : introuvable |
| DELETE | `/stages/{id}` | `204` : suppression sans corps de réponse ; `404` : introuvable |

Les requêtes POST et PUT exigent les cinq champs ci-dessous. PUT remplace
l'ensemble des informations du stage en conservant son identifiant. Les chaînes
doivent être non vides ; les dates doivent être valides et respecter `YYYY-MM-DD`.
La date de fin doit être supérieure ou égale à la date de début. L'identifiant est
généré par SQLite : ne pas l'envoyer dans le corps des requêtes. Les champs
supplémentaires et les données invalides sont rejetés avec le code `422`.

Exemple de corps JSON pour POST ou PUT :

```json
{
  "nom_etudiant": "Étudiant Démo",
  "entreprise": "Entreprise Exemple",
  "intitule": "Développement API REST",
  "date_debut": "2026-04-01",
  "date_fin": "2026-06-30"
}
```

Une erreur `404` retourne `{"detail":"Stage introuvable."}`. Les erreurs `422`
retournent une liste d'erreurs de validation dans la propriété `detail`.

## Tests

Dans l'environnement virtuel activé :

```bash
python -m pytest -q
```

Chaque test utilise un fichier SQLite dans un répertoire temporaire de pytest.
Le démarrage et les sessions de l'API sont redirigés vers cette base ; les tests
ne créent ni ne modifient la base `stages.db` de l'application.

Les 42 cas couvrent le CRUD, la liste vide, les identifiants distincts, les erreurs
404, les champs obligatoires, les données invalides sur POST et PUT, l'égalité
des dates, Swagger et OpenAPI. Ils vérifient aussi qu'une requête rejetée ne
modifie pas les stages enregistrés.

Pour reproduire manuellement les tests dans Swagger, ouvrir une opération,
cliquer sur **Try it out**, renseigner les paramètres puis cliquer sur **Execute** :

1. Créer un stage avec POST ; vérifier `201` et noter l'identifiant retourné.
2. Exécuter GET `/stages`, puis GET `/stages/{id}` ; vérifier `200` et les données.
3. Modifier l'intitulé avec PUT en envoyant les cinq champs ; vérifier `200`,
   puis consulter à nouveau le stage pour confirmer la modification.
4. Envoyer une date de fin antérieure à la date de début, ou retirer un champ
   obligatoire ; vérifier `422` et l'absence de modification.
5. Supprimer le stage ; vérifier `204` et l'absence de corps de réponse.
6. Réessayer GET, PUT avec un corps valide, et DELETE sur cet identifiant ;
   vérifier `404`. GET `/stages` retourne `[]` si la base était initialement vide.

## Tester avec Postman

1. Démarrer l'API avec la commande Uvicorn indiquée plus haut et laisser le
   terminal ouvert.
2. Ouvrir l'application Postman sur le PC et importer le fichier
   `api-stages.postman_collection.json` avec **Import**, ou le glisser dans
   l'application. Voir le [guide d'import Postman](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data).
3. Ouvrir la collection **API Stages - Tests locaux**. La variable `base_url`
   vaut déjà `http://localhost:8000` ; aucun environnement n'est nécessaire.
4. Ouvrir chaque requête dans l'ordre de 01 à 09 et cliquer sur **Send**. Les
   méthodes, URL, en-têtes et corps JSON sont déjà renseignés. La première
   requête mémorise automatiquement l'identifiant pour les suivantes.
5. Consulter le corps de réponse, le statut HTTP et l'onglet **Test Results**.
   Les scripts vérifient les réponses après chaque envoi, comme décrit dans le
   [guide des tests Postman](https://learning.postman.com/docs/tests-and-scripts/write-scripts/test-scripts/).

| Requête | Résultat attendu |
| --- | --- |
| 01 - Créer un stage | `201` et un identifiant généré |
| 02 - Lister les stages | `200`, liste contenant le stage |
| 03 - Consulter le stage | `200`, données du stage |
| 04 - Modifier le stage | `200`, nouvel intitulé |
| 05 - Vérifier la modification | `200`, modification enregistrée |
| 06 - Rejeter des dates incohérentes | `422` |
| 07 - Rejeter un champ obligatoire absent | `422` |
| 08 - Supprimer le stage | `204`, réponse vide |
| 09 - Vérifier que le stage est introuvable | `404` |

Ce scénario crée un stage fictif dans la base de l'API, le modifie puis le
supprime. Il peut être relancé en repartant de la requête 01. Pour tester le
déploiement Render, remplacer la variable de collection `base_url` par l'URL
publique, sans slash final.

## Docker

Prérequis : Docker installé et son moteur démarré. Arrêter le serveur local s'il
occupe déjà le port 8000, puis exécuter :

```bash
docker build -t api-stages .
docker run --rm -d --name api-stages -p 8000:8000 api-stages
docker ps --filter name=api-stages
docker logs api-stages
curl -i http://localhost:8000/stages
```

Ouvrir <http://localhost:8000/docs> et reproduire les tests CRUD. Pour arrêter
le conteneur :

```bash
docker stop api-stages
```

Le Dockerfile utilise l'image officielle `python:3.12-slim`, installe
`requirements.txt` et lance Uvicorn sur `0.0.0.0`. Le port vaut `8000` par défaut
et suit la variable `PORT` lorsqu'elle est fournie. Pour vérifier ce cas :

```bash
docker run --rm -d --name api-stages-port -e PORT=10000 -p 8001:10000 api-stages
curl -i http://localhost:8001/stages
docker stop api-stages-port
```

Sans volume, les données du conteneur sont perdues lorsqu'il est supprimé.
L'option `--rm` le supprime automatiquement après son arrêt.

## Publication sur GitHub et déploiement sur Render

Le projet est préparé pour le déploiement ; aucun dépôt distant ni service Render
n'a été créé pendant sa réalisation. Les étapes ci-dessous sont à effectuer
avec vos comptes.

### 1. Envoyer les sources sur GitHub

Créer un dépôt GitHub vide nommé `mini-projet-cloud`, sans README initial.
Depuis le dossier du projet, remplacer `VOTRE_COMPTE` dans les commandes :

```bash
git init
git add main.py database.py models.py schemas.py requirements.txt test_main.py api-stages.postman_collection.json Dockerfile .dockerignore .gitignore README.md
git commit -m "Créer l'API de gestion des stages"
git branch -M main
git remote add origin https://github.com/VOTRE_COMPTE/mini-projet-cloud.git
git push -u origin main
```

Ne publier ni la base SQLite ni de données personnelles réelles.

### 2. Créer le Web Service

1. Se connecter à [Render](https://dashboard.render.com/), choisir **New → Web
   Service**, connecter GitHub et autoriser l'accès au dépôt.
2. Sélectionner le dépôt et renseigner les paramètres suivants :

| Paramètre | Valeur |
| --- | --- |
| Name | `api-stages` ou un nom disponible |
| Branch | `main` |
| Language / Runtime | `Docker` |
| Root Directory | Laisser vide : les fichiers sont à la racine du dépôt |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context | `.` si le champ est proposé |
| Docker Command | Laisser vide pour utiliser le `CMD` du Dockerfile |
| Instance Type | `Free` si disponible |
| Health Check Path | `/stages` |

3. Lancer **Deploy Web Service** et attendre le statut **Live**. Le Dockerfile
   fournit les étapes de construction et la commande de démarrage.
4. Copier l'URL HTTPS fournie par Render, ouvrir cette URL suivie de `/docs` et
   reproduire le cycle CRUD. Consulter aussi `/stages` depuis Internet.

Ces paramètres suivent le [guide Docker de Render](https://render.com/docs/docker)
et le [guide de premier déploiement](https://render.com/docs/your-first-deploy).

Aucune variable personnalisée n'est nécessaire. Render fournit `PORT` (par
défaut `10000`) et le Dockerfile l'utilise. Voir la
[documentation des ports Render](https://render.com/docs/web-services#port-binding).

**URL publique de l'API : À compléter après le déploiement.**

**URL publique Swagger : À compléter avec l'URL de l'API suivie de `/docs`.**

### Limites de SQLite sur Render

Le système de fichiers est temporaire : la base SQLite peut disparaître après
un redémarrage, un redéploiement ou une mise en veille. Le plan gratuit met le
service en veille après 15 minutes sans requête ; la première requête suivante
peut prendre environ une minute. Les disques persistants ne sont pas proposés
sur ce plan. Ces limites sont acceptées pour ce mini-projet pédagogique ; recréer
les données fictives avant une démonstration si nécessaire.
[Source : limites du plan gratuit Render](https://render.com/docs/free).

## Captures d'écran pour le rendu

Conserver les captures suivantes en faisant apparaître le chemin de l'endpoint,
le code HTTP et la réponse :

| Capture | Éléments à montrer |
| --- | --- |
| Swagger | `/docs` avec les cinq opérations visibles |
| Création | POST avec le JSON fictif, le code `201` et l'identifiant retourné |
| Consultation | GET `/stages` et GET `/stages/{id}`, code `200` et données |
| Modification | PUT, code `200` et intitulé modifié, puis GET de confirmation |
| Suppression | DELETE avec `204`, puis GET du même identifiant avec `404` |
| Erreurs | Stage introuvable `404` et données invalides `422` |
| Docker | Terminal avec `docker ps` montrant le conteneur actif et son port |
| Render | Service au statut Live et Swagger avec l'URL publique dans la barre d'adresse |

## Vérifications réalisées

- Tests automatisés : **42 réussis**. Starlette émet un avertissement de
  dépréciation concernant son client HTTPX ; il ne provoque aucun échec.
- Uvicorn local : cycle CRUD, erreurs `404`/`422`, Swagger et OpenAPI vérifiés par HTTP.
- Docker : image construite et mêmes vérifications HTTP réussies avec le port
  par défaut `8000`, puis avec `PORT=10000`.
- Publication GitHub et déploiement Render : **à effectuer avec vos comptes**.
