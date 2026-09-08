> **Note de mise en forme (à l'attention de la personne qui convertit ce document en `.docx`)**
> Le Markdown ne permet pas d'encoder une couleur ni une police de texte. Pour respecter la charte Yonnov'IA :
> - **Titres (Titre 1 / Titre 2 / Titre 3, correspondant à `#`, `##`, `###`)** → couleur bleu Yonnov'IA `#2596BE`, police serif grasse (ex. Georgia Bold ou Cambria Bold — à aligner sur la police exacte de la charte si elle diffère), conforme au rendu du titre « Format du résumé structuré » de la charte graphique.
> - **Corps de texte, tableaux, listes, code** → **noir (#000000)** exclusivement, police standard du gabarit (ex. Calibri/Arial), aucune autre couleur décorative.
> - Application recommandée : définir les styles Word "Titre 1/2/3" avec cette couleur et cette police (ou utiliser `pandoc Documentation_Phase_2.md --reference-doc=gabarit_yonnovia.docx -o Documentation_Phase_2.docx` avec un gabarit dont les styles de titre sont déjà configurés ainsi).
> - **Logo Yonnov'IA (`frontend/public/logo.jpg`) sur chaque page du document**, pas seulement la page de garde : l'insérer dans l'**en-tête de section Word** (Insertion → En-tête → Image), qui se répète automatiquement sur toutes les pages suivantes — c'est la méthode fiable, contrairement à une image insérée dans le corps du Markdown qui n'apparaîtrait qu'une fois. Le gabarit Pandoc (`gabarit_yonnovia.docx`) doit donc avoir ce logo déjà placé dans son en-tête.

---

# PAGE DE GARDE

![Logo Yonnov'IA](../frontend/public/logo.jpg)

# Yonnov'IA
## Documentation technique

# Phase 2 — Upload PDF, extraction texte et OCR
## Sprint 2 — Moteur d'import PDF et extraction

**Durée estimée :** Semaine 2
**Version du document :** 1.0
**Date :** 26/08/2026
**Auteur :** Équipe Yonnov'IA — Team07-E26

---

# TABLE DES MATIÈRES

*(à régénérer automatiquement comme champ TOC lors de la conversion Word, sur la base des niveaux de titre ci-dessous)*

1. Présentation de la phase
2. Positionnement dans le système
3. Architecture technique
4. Technologies utilisées
5. Architecture des modules
6. Flux de données
7. Documentation détaillée des tâches
   7.1 Développement de l'upload PDF
   7.2 Extraction du texte depuis PDF textuel
   7.3 Détection du besoin OCR
   7.4 Intégration OCR si nécessaire
   7.5 Création du jeu de données de test
8. Interaction entre les tâches
9. API de la phase
10. Modèles de données
11. Gestion globale des erreurs
12. Tests globaux de la phase
13. Sécurité
14. Performance et limites
15. MVP et évolutions futures
16. Décisions techniques
17. Points à clarifier
18. Livrables de la phase
19. Definition of Done globale
20. Matrice de traçabilité

---

# 1. Présentation de la phase

## 1.1 Objectif général

La Phase 2 construit le point d'entrée de tout le pipeline du projet, puisqu'elle transforme un fichier PDF déposé par un utilisateur en un contenu textuel structuré et exploitable par les phases de nettoyage (Phase 3) et de résumé (Phase 4). Elle constitue à ce titre la frontière entre le monde extérieur — un fichier arbitraire fourni par un utilisateur — et le pipeline interne, où les données sont validées, tracées et stockées ; sans elle, aucune donnée ne peut entrer dans le système.

## 1.2 Contexte

Le pipeline du projet traite des articles scientifiques au format PDF, dont la structure varie fortement selon leur origine : PDF texte natif généré par LaTeX ou Word, PDF scanné sans couche texte, PDF multi-colonnes, ou encore PDF contenant des tableaux. La Phase 2 doit absorber cette hétérogénéité et produire, dans tous les cas, soit du texte exploitable, soit un signalement explicite d'échec, sans jamais laisser le pipeline s'arrêter silencieusement.

## 1.3 Problématique technique

Trois problèmes techniques distincts doivent être résolus :

1. **Réception fiable du fichier** : accepter un upload HTTP multipart, le valider, le stocker sans collision de nom, et le rattacher à une entité traçable (document) en base de données.
2. **Extraction hétérogène** : un PDF « texte » et un PDF « scanné » ne peuvent pas être traités par le même algorithme, si bien que le système doit d'abord détecter dans quel cas il se trouve avant de choisir la stratégie d'extraction appropriée.
3. **Dégradation contrôlée** : lorsque l'extraction directe échoue ou se révèle insuffisante, le système doit basculer vers une méthode de secours (OCR) plutôt que d'échouer intégralement, tout en informant l'utilisateur du mode effectivement utilisé.

## 1.4 Résultat attendu

À l'issue de la Phase 2, pour un PDF donné, le système doit produire :

- Un enregistrement `Document` en base de données (identifiant, nom de fichier, statut).
- Un texte brut extrait, page par page, dans l'ordre du document.
- Un rapport d'extraction (méthode utilisée, nombre de pages, volume de caractères).
- Une évaluation — au moins partielle dans le cadre du MVP — de la nécessité d'un OCR et du résultat de cet OCR si déclenché.
- Un jeu de données PDF de test permettant de valider ces mécanismes de façon reproductible.

## 1.5 Périmètre

### Inclus

- Endpoint d'upload PDF avec validation de type et stockage.
- Extraction de texte pour PDF à couche texte native, via PyMuPDF.
- Détection basique du besoin d'OCR (heuristique sur le volume de caractères extraits).
- Point d'extension OCR (Docling) pour les PDF scannés.
- Constitution du dataset de test (8 PDF minimum, cf. Tâche 2.5).

### Non inclus

- Le nettoyage avancé du texte (suppression d'en-têtes répétés, reconstruction de paragraphes) → Phase 3.
- La segmentation en sections scientifiques (Abstract, Introduction, etc.) → Phase 3.
- La génération de résumé → Phase 4.
- L'interface web de suivi visuel de la progression → Phase 5 (Phase 2 expose uniquement l'API).
- **OCR pleinement fonctionnel en production** : au moment de la rédaction de ce document, le connecteur Docling (`app/services/extraction/docling_service.py`) est un **stub non implémenté** (`status: "not_implemented"`, retourne un Markdown vide). Voir section 17 « Points à clarifier ».

---

# 2. Positionnement dans le système

## Entrées

- Fichier binaire PDF transmis en `multipart/form-data` par le frontend (ou tout client HTTP).

## Sorties

- `document_id` (UUID) persistant, réutilisé par toutes les phases suivantes.
- Texte brut extrait (en mémoire, transmis à la Phase 3) et persisté sur disque (`outputs/{stem}/extraction/markdown.md`).
- Rapport d'extraction structuré (JSON), consommé par la Phase 3 (rapport de nettoyage) et par la Phase 5 (affichage qualité).

## Dépendances

- Base de données PostgreSQL (table `documents`, `pipeline_runs`, `extraction_results`) — préalable technique : migrations Alembic appliquées.
- Bibliothèque PyMuPDF (`fitz`) pour la lecture PDF.
- (Optionnel, MVP dégradé) Modèle vision Ollama (`qwen2.5vl`) pour l'évaluation qualité par juge LLM.

## Interactions avec les autres phases

```text
       Utilisateur / Frontend
              │
              ▼
┌─────────────────────────────────────┐
│   PHASE 2 — Upload & Extraction      │
│                                       │
│  2.1 Upload PDF                      │
│      │                               │
│      ▼                               │
│  2.2 Extraction texte natif          │
│      │                               │
│      ▼                               │
│  2.3 Détection besoin OCR ────┐      │
│      │                        │      │
│      ▼                        ▼      │
│  (texte OK)          2.4 OCR (fallback)
│      │                        │      │
│      └──────────┬─────────────┘      │
│                  ▼                    │
│         Pages + Rapport d'extraction  │
└─────────────────────────────────────┘
              │
              ▼
   Phase 3 — Nettoyage, segmentation,
      extraction de métadonnées
```

La Phase 2 ne consomme aucune sortie d'une phase antérieure (elle est le point d'entrée). Elle fournit à la Phase 3 : le texte brut par page, le rapport d'extraction, et le statut qualité (si le juge LLM est actif).

---

# 3. Architecture technique

```text
┌─────────────────────────┐
│ Frontend (React / Vite) │
└────────────┬────────────┘
             │  multipart/form-data
             ▼
┌─────────────────┐
│   API FastAPI   │
│   POST /upload  │
│ POST /summarize │
└────────┬────────┘
         │
         ▼
┌───────────────────────────┐
│    Service d'extraction   │
│ app/services/extraction/* │
│  (pymupdf_service,        │
│   docling_service,        │
│   quality_check)          │
└─────────────┬─────────────┘
              │
         ┌────┴────────────┬────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ Fichiers locaux │  │ Base PostgreSQL │  │  Juge qualité LLM    │
│ uploads/{uuid}/ │  │  (documents,    │  │  (Ollama, optionnel, │
└─────────────────┘  │  pipeline_runs, │  │  ENABLE_LLM_JUDGE)   │
                      │extraction_res.) │  └─────────────────────┘
                      └─────────────────┘
```

**Frontend** : formulaire d'upload React (`frontend/src/App.jsx`, fonction `handleFiles`), filtrage côté client par type MIME et taille (≤ 50 Mo), appel `uploadPdf()` (`frontend/src/api.js`).

**Backend / API** : routeur FastAPI `app/api/routes/upload.py` (`POST /upload`), dépendances partagées `app/api/dependencies.py` (validation, session DB).

**Services d'extraction** : module `app/services/extraction/` — orchestrateur `extractor.py`, implémentation PyMuPDF `pymupdf_service.py`, implémentation Docling `docling_service.py` (stub), évaluation qualité `quality_check.py`.

**Stockage** : système de fichiers local (`UPLOAD_DIR`, `OUTPUT_DIR`, configurables par variables d'environnement) — pas de stockage objet (S3, etc.) prévu au MVP.

**Base de données** : PostgreSQL via SQLAlchemy 2.0, migrations gérées par Alembic. Chaque upload crée une ligne `Document` ; chaque exécution du pipeline crée une ligne `PipelineRun` et une ligne `ExtractionResult` associée.

**Composant IA (optionnel)** : juge de qualité par modèle de vision (Ollama, `qwen2.5vl:7b`), activé uniquement si `ENABLE_LLM_JUDGE=true`. Ce composant n'est pas un OCR : il évalue la fidélité entre l'image d'une page et le texte extrait, sans produire de texte alternatif lui-même.

---

# 4. Technologies utilisées

| Technologie | Rôle | Justification | Alternative |
|---|---|---|---|
| **FastAPI** | Serveur API (upload, orchestration) | Typage Pydantic natif, validation automatique, performances asynchrones, déjà standard sur le reste du projet | Flask (moins de validation native), Django REST (surdimensionné) |
| **PyMuPDF (`fitz`)** | Extraction de texte PDF natif | Léger, rapide, ne nécessite pas de dépendances système lourdes, gère la lecture page par page nécessaire à l'ordre et à la journalisation par page | `pdfplumber` (plus lent sur gros volumes), `pypdf` (extraction texte moins fidèle sur mise en page complexe) |
| **PyMuPDF4LLM** *(annoncé, non branché à ce jour)* | Extraction Markdown structurée (titres, listes) | Prévu par le README du projet pour produire un Markdown fidèle à la mise en page ; **le code actuel (`pymupdf_service.py`) utilise `page.get_text()` brut, pas l'API `pymupdf4llm`** — écart à corriger, voir section 17 | Conserver `fitz.get_text()` si le Markdown structuré n'est pas requis avant la Phase 3 |
| **Docling** | Extraction de secours (PDF scannés / échec PyMuPDF) | Bibliothèque open-source capable de traiter mise en page complexe et, à terme, OCR | Tesseract + pdf2image (OCR plus bas niveau, à assembler manuellement) |
| **PostgreSQL + SQLAlchemy 2.0 + Alembic** | Persistance des documents et exécutions pipeline | Historisation exigée par la Phase 5 (Tâche 5.6), transactions ACID pour la traçabilité des statuts | SQLite (insuffisant en environnement multi-utilisateur), MongoDB (pas de besoin de schéma flexible ici) |
| **Ollama (modèle vision `qwen2.5vl`)** | Juge qualité d'extraction (optionnel) | Évaluation automatique image-vs-texte sans service cloud, cohérent avec le choix « LLM local » du projet | Désactivation complète (`ENABLE_LLM_JUDGE=false`) en environnement sans GPU suffisant |
| **React + Vite** | Interface d'upload | Déjà le socle frontend du projet, réactivité de l'upload multi-fichiers | — |

---

# 5. Architecture des modules

### Module `api/routes/upload.py`

**Responsabilité** : exposer `POST /upload`, valider le fichier reçu, créer l'entité `Document`, écrire le fichier sur disque de façon atomique.
**Entrées** : `UploadFile` (FastAPI/Starlette), session DB (`Depends(get_db)`).
**Sorties** : `UploadResponse` (`document_id`, `filename`, `path`, `status`, `message`).
**Dépendances** : `app/api/dependencies.py` (validation, session), `app/db/models.py` (`Document`).
**Erreurs possibles** : extension invalide (400), nom de fichier vide (400), échec d'écriture disque (500, avec rollback DB et nettoyage des fichiers partiels).

### Module `api/dependencies.py`

**Responsabilité** : fonctions partagées de validation (`sanitize_filename`, `validate_upload_file`) et fourniture de session DB (`get_db`).
**Entrées** : nom de fichier brut, objet `UploadFile`.
**Sorties** : nom de fichier sécurisé (basename, sans chemin), ou exception `HTTPException`.
**Dépendances** : aucune dépendance métier, module transverse.
**Erreurs possibles** : nom de fichier vide après nettoyage, extension différente de `.pdf`.

### Module `services/extraction/extractor.py`

**Responsabilité** : orchestrer l'extraction — validation d'extension/lisibilité, choix PyMuPDF vs Docling, appel du juge qualité optionnel.
**Entrées** : chemin du fichier PDF, chemin de sortie Markdown souhaité.
**Sorties** : `(pages, texte_markdown, rapport_extraction)`.
**Dépendances** : `pymupdf_service.py`, `docling_service.py`, `quality_check.py`, `evaluation/llm_judge.py`.
**Erreurs possibles** : fichier illisible (PDF corrompu), extraction PyMuPDF vide sans fallback Docling fonctionnel (voir section 17).

### Module `services/extraction/pymupdf_service.py`

**Responsabilité** : extraction texte brut page par page via PyMuPDF.
**Entrées** : chemin PDF.
**Sorties** : texte concaténé, rapport (`page_count`, `characters`, `status`).
**Dépendances** : `fitz`.
**Erreurs possibles** : document corrompu (exception PyMuPDF), document chiffré/protégé par mot de passe (non géré explicitement à ce jour).

### Module `services/extraction/docling_service.py`

**Responsabilité (cible)** : extraction OCR/mise en page complexe pour les PDF où PyMuPDF échoue.
**État actuel** : **stub** — retourne systématiquement `{"status": "not_implemented", "markdown": ""}`.
**Entrées (cible)** : chemin PDF.
**Sorties (cible)** : Markdown structuré.
**Dépendances (cible)** : bibliothèque `docling` (non installée dans `requirements.txt` à ce jour).
**Erreurs possibles** : timeout sur PDF volumineux, échec de conversion image, qualité OCR insuffisante.

### Module `services/extraction/quality_check.py`

**Responsabilité** : agréger les scores de qualité par page en une décision globale (`accept` / `fallback`).
**Entrées** : liste de résultats par page (`quality_score`).
**Sorties** : rapport global (`average_score`, `failed_pages`, `decision`).
**Dépendances** : aucune (fonction pure).
**Erreurs possibles** : liste vide → décision par défaut `fallback` avec score `0`.

### Module `services/evaluation/llm_judge.py`

**Responsabilité** : comparer image de page et texte extrait via un modèle vision, produire un score 0–100 et une décision `accept`/`fallback`.
**Entrées** : chemin PDF, résultats d'extraction par page.
**Sorties** : liste de scores par page (échantillonnés, `LLM_JUDGE_MAX_PAGES` pages maximum).
**Dépendances** : `ollama` (client Python), modèle `qwen2.5vl:7b` téléchargé localement.
**Erreurs possibles** : modèle non disponible, timeout d'inférence, réponse JSON malformée du modèle.

### Structure de fichiers (réelle, backend)

```text
backend/
├── app/
│   ├── api/
│   │   ├── dependencies.py          # validation, session DB
│   │   └── routes/
│   │       ├── upload.py            # POST /upload, DELETE /documents/{id}
│   │       └── documents.py         # GET /documents, GET /documents/{id}/pipeline-runs
│   ├── db/
│   │   ├── database.py              # engine, SessionLocal, Base
│   │   └── models.py                # Document, PipelineRun, ExtractionResult, ...
│   ├── models/
│   │   ├── request_models.py
│   │   └── response_models.py       # UploadResponse, ExtractionResultResponse, ...
│   ├── services/
│   │   ├── extraction/
│   │   │   ├── extractor.py         # orchestrateur
│   │   │   ├── pymupdf_service.py
│   │   │   ├── docling_service.py   # stub OCR
│   │   │   └── quality_check.py
│   │   ├── evaluation/
│   │   │   └── llm_judge.py         # juge qualité vision (optionnel)
│   │   └── pipeline/
│   │       └── document_pipeline.py # orchestrateur global (toutes phases)
│   └── core/
│       ├── config.py                # UPLOAD_DIR, ENABLE_LLM_JUDGE, ...
│       └── constants.py             # STATUS_COMPLETED, STATUS_FAILED, STATUS_RUNNING
├── alembic/                          # migrations DB
└── tests/
```

---

# 6. Flux de données

```text
Input : fichier PDF (multipart/form-data)
 ↓
Validation (dependencies.validate_upload_file)
   - extension .pdf obligatoire
   - nom de fichier non vide
   - [MANQUANT] taille maximale non vérifiée côté serveur (voir §17)
 ↓
Stockage (routes/upload.py)
   - document_id = uuid4()
   - écriture atomique via fichier temporaire + rename
   - chemin final : uploads/{document_id}/{filename}
 ↓
Persistance (DB)
   - INSERT Document(status="UPLOADING" → "completed")
 ↓
Traitement (extractor.extract_pdf_content, déclenché par POST /summarize)
   - validate_pdf_extension / validate_pdf_readable
   - extraction PyMuPDF (pymupdf_service)
   - si pages vides → tentative Docling (stub actuellement)
 ↓
Évaluation qualité (optionnelle, si ENABLE_LLM_JUDGE=true)
   - échantillonnage de pages
   - scoring vision LLM
   - décision accept/fallback
 ↓
Transformation
   - assemblage du texte en Markdown
   - rapport d'extraction structuré (JSON)
 ↓
Stockage des résultats
   - fichier : outputs/{stem}/extraction/markdown.md
   - fichier : outputs/{stem}/extraction/extraction_report.json
   - DB : ExtractionResult (méthode, score, décision, page_count)
 ↓
Output : (pages[], texte_markdown, rapport_extraction) → Phase 3
```

**Erreurs possibles à chaque étape** : voir section 11 (gestion globale des erreurs) et les sous-sections 7.X.10 par tâche.

---

# 7. Documentation détaillée des tâches

## 7.1 Développement de l'upload PDF

### 7.1.1 Objectif

Permettre à un utilisateur de transmettre un fichier PDF au système via une API HTTP, avec validation et stockage traçable.

### 7.1.2 Description technique

Un endpoint `POST /upload` reçoit un `UploadFile` FastAPI. Le nom de fichier est nettoyé (basename uniquement, suppression de tout chemin), l'extension est vérifiée, un identifiant unique `document_id` (UUID v4) est généré, et le fichier est écrit sur disque sous `uploads/{document_id}/{filename}` via un fichier temporaire renommé de façon atomique (`Path.replace`). Une ligne `Document` est créée en base avec le statut `UPLOADING`, puis mise à jour à `completed` une fois l'écriture terminée.

### 7.1.3 Fonctionnement détaillé

1. Réception du fichier (`file: UploadFile = File(...)`).
2. `validate_upload_file(file)` → nom nettoyé, vérifie extension `.pdf` (insensible à la casse).
3. Génération `document_id = uuid4()`.
4. Création du répertoire `uploads/{document_id}/`.
5. Insertion `Document` en base (`status="UPLOADING"`), `db.add()` sans commit immédiat.
6. Écriture du contenu binaire dans un fichier temporaire `.{nom}.{uuid_temp}.tmp`.
7. `Path.replace()` du fichier temporaire vers la destination finale (opération atomique au niveau du système de fichiers).
8. Mise à jour `document.status = "completed"`, `db.commit()`, `db.refresh(document)`.
9. En cas d'exception à n'importe quelle étape 5–8 : `db.rollback()`, suppression des fichiers/répertoires partiels créés.

### 7.1.4 Inputs

- `file` : `UploadFile` (champ `file` du formulaire multipart), contenant `filename` et le flux binaire.

### 7.1.5 Outputs

- `UploadResponse` JSON : `document_id` (UUID), `filename` (str, nettoyé), `path` (str, chemin serveur absolu), `status` (str), `message` (str).

### 7.1.6 Algorithme

```text
FONCTION upload_pdf(file, db):
    SI file.filename est vide:
        LEVER erreur 400 "Filename is required"

    nom_sûr ← nettoyer_nom(file.filename)   # basename, strip
    SI extension(nom_sûr) != ".pdf":
        LEVER erreur 400 "Only PDF files are supported"

    document_id ← uuid4()
    répertoire ← UPLOAD_DIR / document_id
    créer répertoire

    document ← Document(id=document_id, filename=nom_sûr,
                         original_filename=file.filename,
                         file_path=répertoire/nom_sûr,
                         status="UPLOADING")
    db.add(document)

    TENTER:
        écrire contenu dans fichier temporaire
        renommer fichier temporaire → destination finale
        document.status ← "completed"
        db.commit()
    SAUF Exception:
        db.rollback()
        supprimer fichiers/répertoires partiels
        RELANCER

    RETOURNER UploadResponse(document.id, document.filename,
                              document.file_path, document.status,
                              "File uploaded successfully")
```

### 7.1.7 Technologies et bibliothèques

FastAPI (`UploadFile`, `File`), `pathlib.Path`, `uuid.uuid4`, SQLAlchemy ORM (`Session`).

### 7.1.8 Structures de données

```python
class UploadResponse(BaseModel):
    document_id: UUID
    filename: str
    path: str
    status: str
    message: str
```

```python
class Document(Base):
    __tablename__ = "documents"
    id: UUID (PK, default=uuid4)
    filename: str(255)
    original_filename: str(255)
    file_path: str(1000)
    status: str(50), default="UPLOADED"
    created_at: datetime (UTC)
    updated_at: datetime (UTC, auto)
```

### 7.1.9 API

```text
POST /upload
Content-Type: multipart/form-data

Paramètres (form-data) :
  file   binary   requis   Fichier PDF à uploader

Réponse 200 OK :
{
  "document_id": "e73a4acf-6543-4e8b-b3b8-e17c1e38ce60",
  "filename": "article.pdf",
  "path": "C:\\...\\uploads\\e73a4acf-.../article.pdf",
  "status": "completed",
  "message": "File uploaded successfully"
}

Réponse 400 Bad Request :
{ "detail": "Only PDF files are supported" }

Réponse 500 Internal Server Error :
{ "detail": "<message d'erreur serveur>" }
```

```text
DELETE /documents/{document_id}
Supprime le document, ses pipeline_runs et résultats associés, ainsi que
les fichiers uploadés et générés (si aucun autre document ne partage le
même nom de fichier).

Réponse 200 OK :
{ "document_id": "...", "status": "deleted", "message": "..." }

Réponse 404 Not Found :
{ "detail": "Document not found" }
```

### 7.1.10 Gestion des erreurs

| Erreur | Cause | Détection | Traitement | Message utilisateur |
|---|---|---|---|---|
| Extension invalide | Fichier sans extension `.pdf` | `validate_upload_file` | HTTP 400, aucune écriture disque | « Only PDF files are supported » |
| Nom de fichier vide | `file.filename` absent/vide | `sanitize_filename` | HTTP 400 | « Filename is required » |
| Fichier trop volumineux | Aucun contrôle serveur actuellement | — | — | **Non géré côté serveur — cf. §17** |
| Échec d'écriture disque (disque plein, permissions) | Exception `OSError` pendant l'écriture | `try/except` dans la route | Rollback DB, suppression fichiers partiels, HTTP 500 | « Erreur serveur lors de l'upload » (générique) |
| Nom de fichier avec espace/point en fin de segment (`"nom .pdf"`) | Windows tronque silencieusement l'espace/point final d'un composant de chemin lors de sa création | Constat empirique (`WinError 3`) lors de la Phase suivante (répertoire de sortie basé sur le nom) | **Corrigé sur la branche `karim`** (`sanitize_filename` retire les espaces/points en fin de radical) ; **non encore reporté sur `main`** — cf. §17 | — |

### 7.1.11 Logging

- Journaliser : réception de l'upload (nom de fichier, taille reçue), succès (`document_id`), échec (exception complète via `logger.exception`).
- Niveau recommandé : `INFO` pour succès, `ERROR` pour échec d'écriture, `WARNING` pour rejets de validation (400).

### 7.1.12 Sécurité

- **Traversée de chemin** : `sanitize_filename` réduit le nom au `basename` (`Path(...).name`), empêchant l'injection de segments `../`.
- **Type MIME non vérifié côté serveur** : seule l'extension est contrôlée ; un fichier renommé `.pdf` mais non conforme au format PDF passera la validation d'upload (il sera rejeté plus tard par `validate_pdf_readable` lors de l'extraction, mais restera stocké sur disque entre-temps).
- **Absence de limite de taille serveur** : un client malveillant peut envoyer un fichier arbitrairement volumineux (déni de service par épuisement disque). Le filtrage à 50 Mo existe uniquement côté frontend (`App.jsx`, contournable).
- **Isolation par document_id** : chaque upload est stocké dans un répertoire dédié (`uploads/{uuid}/`), évitant les collisions de noms entre utilisateurs.

### 7.1.13 Performance

- Écriture synchrone du flux complet en mémoire (`await file.read()`) avant écriture disque : pour de très gros fichiers, cela charge l'intégralité du fichier en RAM. Acceptable pour des articles scientifiques (quelques Mo), à surveiller si des PDF volumineux (rapports techniques longs, > 50 Mo) sont autorisés.
- Aucune limite de débit (rate limiting) sur l'endpoint.

### 7.1.14 Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T2.1-01 | Upload PDF valide | fichier `.pdf` valide, < 1 Mo | 200, `document_id` présent, fichier sur disque | Haute |
| T2.1-02 | Upload fichier non PDF | fichier `.txt` renommé `.pdf` | 200 à l'upload (extension seule vérifiée) puis échec à l'extraction | Haute |
| T2.1-03 | Upload sans extension `.pdf` | fichier `.docx` | 400 « Only PDF files are supported » | Haute |
| T2.1-04 | Upload nom de fichier vide | `filename=""` | 400 « Filename is required » | Moyenne |
| T2.1-05 | Upload avec chemin dans le nom | `filename="../../etc/passwd.pdf"` | Nom réduit au basename, pas de traversée de chemin | Haute |
| T2.1-06 | Upload fichier volumineux (> 50 Mo) | fichier de 200 Mo | **Non bloqué côté serveur actuellement** — à corriger | Haute |
| T2.1-07 | Deux uploads du même fichier | même PDF uploadé deux fois | Deux `document_id` distincts, deux répertoires distincts | Moyenne |
| T2.1-08 | Suppression d'un document | `DELETE /documents/{id}` sur document existant | 200, fichiers et lignes DB associées supprimés | Moyenne |
| T2.1-09 | Suppression d'un document inexistant | `DELETE /documents/{uuid-aléatoire}` | 404 « Document not found » | Basse |

### 7.1.15 Critères d'acceptation techniques

- [ ] `POST /upload` avec un PDF valide retourne HTTP 200 et un `document_id` UUID valide.
- [ ] `POST /upload` avec un fichier `.docx`, `.txt` ou sans extension retourne HTTP 400.
- [ ] Le fichier est physiquement présent sur disque à l'emplacement `path` retourné.
- [ ] Une ligne `Document` existe en base avec `status="completed"` après un upload réussi.
- [ ] Un nom de fichier contenant `../` ne provoque aucune écriture en dehors de `UPLOAD_DIR`.
- [ ] *(Non satisfait à ce jour)* Un fichier dépassant une taille maximale configurée est rejeté avec un message explicite avant tout traitement.

### 7.1.16 Livrables

- Endpoint `POST /upload` (`app/api/routes/upload.py`).
- Endpoint `DELETE /documents/{document_id}`.
- Fonctions de validation (`app/api/dependencies.py`).
- Modèle `Document` et migration Alembic associée.
- Composant frontend de dépôt de fichier (`frontend/src/App.jsx`, zone d'upload).

### 7.1.17 Dépendances

- Base de données PostgreSQL disponible et migrée (`alembic upgrade head`).
- Répertoire `UPLOAD_DIR` accessible en écriture par le process backend.

### 7.1.18 Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Absence de limite de taille serveur | Saturation disque, déni de service | Moyenne | Ajouter une vérification `Content-Length` / lecture par chunks avec seuil, avant écriture complète |
| Écriture disque hors transaction DB (fichier écrit mais DB en échec, ou inverse) | Incohérence fichier/DB | Faible (rollback prévu) | Le code actuel supprime déjà les fichiers partiels en cas d'échec ; ajouter un test automatisé dédié |

### 7.1.19 Definition of Done

```text
☐ Endpoint d'upload développé et fonctionnel
☐ Validation extension implémentée
☐ Génération document_id et stockage isolé par document
☐ Persistance DB (Document) avec statut cohérent
☐ Gestion des erreurs (400/500) avec rollback
☐ Logging des succès/échecs
☐ Tests unitaires (validation) et d'intégration (upload réel)
☐ Documentation API à jour
☐ Limite de taille serveur implémentée (actuellement manquante)
```

---

## 7.2 Extraction du texte depuis PDF textuel

### 7.2.1 Objectif

Extraire le texte brut d'un PDF disposant déjà d'une couche texte (non scanné), page par page, en conservant l'ordre du document.

### 7.2.2 Description technique

Le module `pymupdf_service.extract_with_pymupdf` ouvre le PDF via PyMuPDF (`fitz.open`), itère sur chaque page (`document`, itérable PyMuPDF), appelle `page.get_text()` pour chaque page, et concatène les fragments non vides séparés par une double nouvelle ligne. Un rapport (`page_count`, `characters`, `status`) accompagne le texte.

### 7.2.3 Fonctionnement détaillé

1. Ouverture du document via `fitz.open(pdf_path)`.
2. Itération séquentielle sur les pages (ordre garanti par l'API PyMuPDF, correspondant à l'ordre physique du PDF).
3. Extraction du texte de chaque page (`page.get_text()`, mode texte simple — pas de mode `"markdown"` de `pymupdf4llm` à ce jour, cf. section 4).
4. Filtrage des fragments vides ou uniquement composés d'espaces.
5. Concaténation avec séparateur `"\n\n"`.
6. Fermeture du document (`document.close()`).
7. Construction du rapport d'extraction (nombre de pages, nombre de caractères).

### 7.2.4 Inputs

- Chemin du fichier PDF (`str | Path`).

### 7.2.5 Outputs

- `texte_extrait: str` — texte concaténé de toutes les pages non vides.
- `rapport: dict` — `{"source": "PyMuPDF4LLM", "page_count": int, "characters": int, "status": "success"}`.

*(Remarque : le champ `"source": "PyMuPDF4LLM"` du rapport est actuellement trompeur — l'implémentation utilise l'API texte brut de PyMuPDF, pas la bibliothèque `pymupdf4llm`. Voir section 17.)*

### 7.2.6 Algorithme

```text
FONCTION extract_with_pymupdf(pdf_path):
    document ← ouvrir(pdf_path)
    fragments ← []
    POUR CHAQUE page DANS document:
        fragments.ajouter(page.texte())
    document.fermer()

    texte ← joindre("\n\n", [f.strip() POUR f DANS fragments SI f.strip() non vide])

    rapport ← {
        source: "PyMuPDF4LLM",
        page_count: longueur(fragments),
        characters: longueur(texte),
        status: "success"
    }
    RETOURNER (texte, rapport)
```

### 7.2.7 Technologies et bibliothèques

PyMuPDF (`fitz`), Python standard (`pathlib`).

### 7.2.8 Structures de données

```json
{
  "source": "PyMuPDF4LLM",
  "page_count": 12,
  "characters": 34521,
  "status": "success"
}
```

### 7.2.9 API

Fonction interne, non exposée directement en HTTP. Consommée par `extractor.extract_pdf_content`, elle-même appelée par le pipeline via `POST /summarize` (cf. section 9 pour l'API globale de la phase).

### 7.2.10 Gestion des erreurs

| Erreur | Cause | Détection | Traitement | Message utilisateur |
|---|---|---|---|---|
| PDF corrompu | Fichier invalide, en-tête PDF absent | Exception PyMuPDF à l'ouverture | Propagée à `extract_pdf_content`, capturée par le pipeline global (`document_pipeline.run`), statut `failed`, `failure_stage="extraction"` | « extraction failed: <détail> » |
| PDF protégé par mot de passe | Chiffrement PDF | Exception PyMuPDF à l'ouverture ou à la lecture de page | Non différencié d'un PDF corrompu actuellement | Message générique d'échec d'extraction |
| Document sans aucun texte natif (scanné) | Toutes les pages retournent une chaîne vide | `pages` résultant est vide | Bascule vers Docling (`use_docling = True`) — actuellement stub, retourne un texte vide également | Le pipeline continue avec un texte vide, sans erreur explicite dédiée (cf. §17) |

### 7.2.11 Logging

- Journaliser la durée de l'étape (`logger.info("Timing | Extraction | %.3f seconds", ...)`, déjà en place dans `document_pipeline.py`).
- Recommandation : ajouter un log par page vide détectée (actuellement absent), utile pour diagnostiquer les PDF partiellement scannés.

### 7.2.12 Sécurité

- Aucun risque d'exécution de code : PyMuPDF interprète le PDF de façon isolée (pas d'exécution de JavaScript embarqué par cette API).
- Risque de déni de service sur PDF « bombe » (PDF valide mais avec un nombre de pages ou d'objets extrêmement élevé) : non mitigé à ce jour (pas de timeout d'extraction).

### 7.2.13 Performance

- Extraction mesurée en pratique < 0,2 seconde pour un PDF de 12 pages sur la machine de développement (log réel : `Timing | Extraction | 0.094 seconds`).
- Complexité linéaire au nombre de pages ; aucun cache ni parallélisation à ce stade (MVP).
- Aucune limite de nombre de pages actuellement appliquée.

### 7.2.14 Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T2.2-01 | PDF textuel simple, 1 page | PDF avec un paragraphe | Texte extrait non vide, `page_count=1` | Haute |
| T2.2-02 | PDF textuel multi-pages | PDF de 12 pages (dataset `1007.3049v1.pdf`) | `page_count=12`, ordre des pages respecté | Haute |
| T2.2-03 | PDF avec pages vides intercalées | PDF avec 1 page blanche au milieu | Page vide exclue du texte concaténé, mais comptée dans `page_count` | Moyenne |
| T2.2-04 | PDF corrompu | Fichier tronqué / en-tête invalide | Exception propagée, statut pipeline `failed`, `failure_stage="extraction"` | Haute |
| T2.2-05 | PDF entièrement scanné (aucun texte) | PDF image pure | `pages` vide, bascule vers Docling déclenchée | Haute |
| T2.2-06 | PDF multi-colonnes | PDF scientifique 2 colonnes | Texte extrait (ordre de lecture non garanti colonne par colonne — limite connue de `get_text()` simple) | Moyenne |

### 7.2.15 Critères d'acceptation techniques

- [ ] Le texte d'un PDF textuel standard est extrait intégralement (caractères ≈ au contenu visible).
- [ ] Les pages sont concaténées dans l'ordre physique du document.
- [ ] Un PDF sans texte natif produit une liste de pages vide, déclenchant la bascule OCR.
- [ ] Le rapport d'extraction (`page_count`, `characters`, `status`) est produit systématiquement en cas de succès.
- [ ] Une exception d'ouverture PDF est capturée et remontée avec `failure_stage="extraction"`, sans crash du serveur.

### 7.2.16 Livrables

- Fonction `extract_with_pymupdf` (`app/services/extraction/pymupdf_service.py`).
- Fonction d'orchestration `extract_pdf_content` (`app/services/extraction/extractor.py`).
- Fichiers de sortie : `outputs/{stem}/extraction/markdown.md`, `extraction_report.json`.
- Tests d'intégration sur le dataset de la Tâche 2.5.

### 7.2.17 Dépendances

- Tâche 2.1 (fichier disponible sur disque, `document_id` connu).
- PyMuPDF installé (`requirements.txt`, `pymupdf>=1.24.0`).

### 7.2.18 Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Étiquetage trompeur « PyMuPDF4LLM » sans utiliser réellement cette bibliothèque | Sortie non structurée en Markdown, alors que les phases suivantes ou la documentation pourraient le supposer | Confirmée (constat de code) | Soit intégrer réellement `pymupdf4llm.to_markdown()`, soit renommer le champ `source` en `"PyMuPDF (texte brut)"` |
| Ordre de lecture incorrect sur PDF multi-colonnes | Texte extrait mélangeant les colonnes | Moyenne (limite connue de l'extraction texte simple) | Évaluer `pymupdf4llm` ou une extraction par blocs (`page.get_text("blocks")`) triés par position |

### 7.2.19 Definition of Done

```text
☐ Extraction fonctionnelle sur PDF textuel simple et multi-pages
☐ Ordre des pages respecté
☐ Rapport d'extraction généré
☐ Pages vides détectées (comptage) — journalisation détaillée à ajouter
☐ Tests sur le dataset de la Tâche 2.5
☐ Gestion des erreurs d'ouverture PDF
☐ Écart « PyMuPDF4LLM » vs implémentation réelle documenté et arbitré
```

---

## 7.3 Détection du besoin OCR

### 7.3.1 Objectif

Déterminer automatiquement si un PDF nécessite un traitement OCR plutôt qu'une extraction directe, et rendre cette décision explicable.

### 7.3.2 Description technique

Deux mécanismes coexistent dans le code actuel, à des niveaux de maturité différents :

1. **Déclencheur effectif** (`extractor.extract_pdf_content`) : si l'extraction PyMuPDF ne produit **aucune page** (`pages` vide), le système bascule sur Docling. C'est une condition binaire et grossière (tout ou rien), sans seuil configurable.
2. **Fonction de détection dédiée** (`extractor.needs_ocr`) : implémente la règle prévue par le cahier des charges — compte le total de caractères extraits sur l'ensemble des pages et compare à un seuil (`min_chars=20` par défaut). **Cette fonction existe mais n'est appelée nulle part dans le pipeline actuel** (code mort) — voir section 17.
3. **Juge qualité LLM** (`evaluation/llm_judge.py`, optionnel) : évalue, page par page échantillonnée, la fidélité entre l'image de la page et le texte extrait, et produit une décision `accept`/`fallback`. Ce mécanisme est plus proche d'un contrôle qualité que d'une détection de besoin OCR au sens strict, et **n'est pas non plus branché sur le déclenchement réel de l'OCR** — il alimente uniquement un rapport de qualité stocké en base.

### 7.3.3 Fonctionnement détaillé

**Mécanisme 1 (actif) :**
1. `extract_with_pymupdf` retourne une liste `pages`.
2. `if not pages: use_docling = True`.

**Mécanisme 2 (`needs_ocr`, code mort, non appelé) :**
1. Ouverture du PDF.
2. Somme des longueurs de texte (après `strip()`) sur toutes les pages.
3. Retourne `True` si le total est strictement inférieur à `min_chars`.

**Mécanisme 3 (juge LLM, optionnel, informatif) :**
1. Activé uniquement si `ENABLE_LLM_JUDGE=true`.
2. Échantillonne jusqu'à `LLM_JUDGE_MAX_PAGES` pages (3 par défaut).
3. Pour chaque page échantillonnée : rendu en image, appel au modèle vision avec un prompt structuré, récupération d'un `quality_score` (0–100) et d'une `decision` (`accept`/`fallback`, seuil 75).
4. Agrégation (`quality_check.build_quality_report`) : score moyen, nombre de pages en échec, décision globale.

### 7.3.4 Inputs

- Chemin du PDF (mécanismes 1 et 2).
- Chemin du PDF + résultats d'extraction par page (mécanisme 3).

### 7.3.5 Outputs

- Mécanisme 1 : booléen implicite (`use_docling`), non exposé en tant que tel dans le rapport final.
- Mécanisme 2 (non branché) : booléen `True`/`False`.
- Mécanisme 3 : rapport structuré (`average_score`, `decision`, `pages[]` avec score et résumé par page), persisté en base (`ExtractionResult.quality_score`, `.decision`).

### 7.3.6 Algorithme

```text
# Mécanisme 2 — needs_ocr (existant, non branché)
FONCTION needs_ocr(pdf_path, min_chars=20):
    document ← ouvrir(pdf_path)
    total_caractères ← 0
    POUR CHAQUE page DANS document:
        total_caractères += longueur(strip(page.texte()))
    document.fermer()
    RETOURNER total_caractères < min_chars

# Mécanisme 3 — juge LLM (existant, optionnel)
FONCTION evaluate_extraction_quality(pdf_path, résultats):
    SI NON ENABLE_LLM_JUDGE:
        RETOURNER { status: "skipped", decision: "skipped" }

    pages_évaluées ← evaluate_document_pages(pdf_path, résultats)  # échantillon ≤ LLM_JUDGE_MAX_PAGES
    RETOURNER build_quality_report(pages_évaluées)
```

### 7.3.7 Technologies et bibliothèques

PyMuPDF (mécanismes 1 et 2), client `ollama` + modèle vision `qwen2.5vl:7b` (mécanisme 3).

### 7.3.8 Structures de données

```json
{
  "status": "skipped | ok",
  "message": "LLM Judge disabled by configuration.",
  "decision": "accept | fallback | skipped",
  "average_score": 82.5,
  "pages": [
    { "page": 1, "quality_score": 90, "decision": "accept", "summary": "..." }
  ]
}
```

### 7.3.9 API

Non exposé directement ; intégré au traitement déclenché par `POST /summarize`. Le résultat est consultable a posteriori via `GET /documents/{document_id}/pipeline-runs` → `extraction.quality_score`, `extraction.decision`.

### 7.3.10 Gestion des erreurs

| Erreur | Cause | Détection | Traitement | Message utilisateur |
|---|---|---|---|---|
| Modèle vision indisponible (Ollama arrêté / modèle non téléchargé) | Service Ollama non démarré ou modèle manquant | Exception lors de l'appel `ollama.chat` | Non capturée spécifiquement dans `evaluate_document_pages` à ce jour — remonte comme échec générique du pipeline | Message d'échec générique, à préciser |
| Réponse JSON malformée du modèle | Le modèle ne respecte pas le schéma demandé | Échec de parsing JSON | Non géré explicitement — risque d'exception non capturée | À corriger : capturer et affecter un score par défaut (ex. 0, decision "fallback") |
| `needs_ocr` jamais invoquée | Fonction non appelée par le pipeline | Revue de code | Fonction conservée mais inerte | — |

### 7.3.11 Logging

- Le mécanisme 1 ne journalise pas explicitement la bascule Docling (absence de `logger.info("Bascule OCR déclenchée")`) — à ajouter pour la traçabilité.
- Le mécanisme 3 devrait journaliser chaque score de page évalué et la décision finale (actuellement seul le résultat agrégé est retourné, pas de log dédié).

### 7.3.12 Sécurité

- Aucun risque de sécurité direct. Risque opérationnel : si le juge LLM est activé sans limite de pages cohérente sur un document très volumineux, le temps de traitement peut devenir prohibitif (mitigé par `LLM_JUDGE_MAX_PAGES`).

### 7.3.13 Performance

- Le mécanisme 1 est instantané (test sur une liste déjà en mémoire).
- Le mécanisme 3, lorsqu'actif, ajoute un coût significatif : chaque page échantillonnée nécessite une inférence vision complète. Sur la machine de test (GPU 4 Go partiellement disponible), une évaluation à 12 pages avec `ENABLE_LLM_JUDGE=true` a provoqué un temps de traitement de plusieurs minutes — c'est pourquoi le MVP recommande `ENABLE_LLM_JUDGE=false` par défaut en environnement de développement contraint.

### 7.3.14 Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T2.3-01 | PDF textuel normal | PDF avec texte substantiel sur toutes les pages | `needs_ocr` (si branché) retourne `False` | Haute |
| T2.3-02 | PDF scanné pur | PDF sans aucun texte natif | `pages` vide → bascule Docling déclenchée (mécanisme 1) | Haute |
| T2.3-03 | PDF avec 1 page vide sur 12 | 11 pages de texte + 1 page blanche | `needs_ocr` (si branché) retourne `False` (seuil global, pas par page) | Moyenne |
| T2.3-04 | Juge LLM désactivé | `ENABLE_LLM_JUDGE=false` | `evaluate_extraction_quality` retourne `status="skipped"` immédiatement | Haute |
| T2.3-05 | Juge LLM activé, modèle indisponible | `ENABLE_LLM_JUDGE=true`, Ollama arrêté | Erreur gérée proprement, pipeline ne plante pas silencieusement | Haute |

### 7.3.15 Critères d'acceptation techniques

- [ ] Un PDF sans texte natif déclenche systématiquement la tentative d'extraction alternative.
- [ ] *(Non satisfait)* La décision de bascule OCR repose sur un seuil configurable et documenté (actuellement condition binaire « pages vides »).
- [ ] *(Non satisfait)* `needs_ocr` est effectivement appelée dans le flux de décision.
- [ ] Si le juge qualité est actif, la décision (`accept`/`fallback`) et le score sont persistés et consultables.
- [ ] L'utilisateur est informé (dans le rapport d'extraction) de la méthode réellement utilisée (`pymupdf4llm` vs `docling`).

### 7.3.16 Livrables

- Fonction `needs_ocr` (`app/services/extraction/extractor.py`) — à intégrer réellement au flux de décision.
- Fonction `evaluate_extraction_quality` + `evaluate_document_pages` (juge LLM).
- Rapport de décision persisté (`ExtractionResult.decision`, `.quality_score`).

### 7.3.17 Dépendances

- Tâche 2.2 (résultat d'extraction PyMuPDF disponible).
- Modèle Ollama vision installé si `ENABLE_LLM_JUDGE=true`.

### 7.3.18 Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Décision OCR binaire et grossière (pages vides uniquement) | Un PDF partiellement scanné (ex. 2 pages sur 12 sans texte) n'est jamais détecté comme nécessitant OCR | Élevée (confirmée par le code) | Brancher `needs_ocr` avec un seuil par document, ou une règle par page (ratio de pages sous le seuil) |
| Coût de calcul du juge LLM sur environnement GPU limité | Temps de traitement prohibitif, expérience utilisateur dégradée | Élevée (observée en session de test réelle) | Garder `ENABLE_LLM_JUDGE=false` par défaut ; documenter clairement le compromis coût/qualité |

### 7.3.19 Definition of Done

```text
☐ Mécanisme de détection basé sur un seuil de caractères, réellement branché
☐ Seuils documentés (valeur, unité, justification)
☐ Décision journalisée et explicable a posteriori
☐ Juge LLM optionnel fonctionnel et dégradable proprement (erreurs capturées)
☐ Tests couvrant PDF textuel, scanné, et partiellement scanné
☐ Message utilisateur clair indiquant si un OCR a été nécessaire
```

---

## 7.4 Intégration OCR si nécessaire

### 7.4.1 Objectif

Permettre l'extraction de texte pour les PDF scannés (sans couche texte), via un pipeline OCR de secours.

### 7.4.2 Description technique

**État actuel : non implémenté.** Le point d'intégration existe (`docling_service.extract_with_docling`), il est correctement appelé par l'orchestrateur (`extractor.extract_pdf_content`) lorsque l'extraction PyMuPDF ne produit aucune page, mais la fonction retourne systématiquement une charge utile vide :

```python
def extract_with_docling(pdf_path):
    return {
        "source": "Docling",
        "pdf_path": str(pdf_path),
        "status": "not_implemented",
        "markdown": "",
    }
```

Par conséquent, à ce jour, **un PDF scanné produit un texte vide en sortie de Phase 2**, sans exception explicite — le pipeline continue silencieusement avec un contenu vide jusqu'aux phases suivantes, où il échouera probablement de façon moins compréhensible (ex. section « Abstract introuvable » en Phase 3).

### 7.4.3 Fonctionnement détaillé (cible, à implémenter)

1. Détection du besoin OCR (Tâche 2.3, effectivement branchée).
2. Conversion de chaque page PDF en image (rendu raster, ex. via PyMuPDF `page.get_pixmap()` ou Docling natif).
3. Passage de chaque image au moteur OCR (Docling, ou modèle vision Ollama déjà présent dans le projet pour le juge qualité — réutilisable comme extracteur).
4. Assemblage du texte extrait par page, dans l'ordre.
5. Calcul d'un indicateur de qualité OCR (ex. taux de caractères reconnus avec confiance, ou réutilisation du juge qualité existant).
6. Limitation du volume traité (nombre de pages maximum, ou timeout global) pour éviter un traitement excessivement long.

### 7.4.4 Inputs (cible)

- Chemin du PDF détecté comme nécessitant un OCR.

### 7.4.5 Outputs (cible)

- Texte OCR assemblé, page par page.
- Rapport de qualité OCR (confiance, pages en échec).

### 7.4.6 Algorithme (cible, non implémenté)

```text
FONCTION extract_with_docling(pdf_path, max_pages=50):
    images ← convertir_pages_en_images(pdf_path, limite=max_pages)
    textes_par_page ← []
    POUR CHAQUE image DANS images:
        TENTER:
            texte ← moteur_ocr(image)
            textes_par_page.ajouter(texte)
        SAUF Exception AS e:
            textes_par_page.ajouter("")
            journaliser_erreur_page(e)

    markdown ← assembler(textes_par_page)
    qualité ← évaluer_qualité(textes_par_page)

    RETOURNER { source: "Docling", markdown: markdown,
                status: "success", quality: qualité }
```

### 7.4.7 Technologies et bibliothèques (cible)

Docling (à ajouter à `requirements.txt`, absente actuellement), ou réutilisation du modèle vision Ollama déjà en place pour le juge qualité (`qwen2.5vl`), capable en principe de transcrire une image de page.

### 7.4.8 Structures de données (cible)

```json
{
  "source": "Docling",
  "status": "success",
  "markdown": "...",
  "quality": { "average_confidence": 0.0, "failed_pages": [] }
}
```

### 7.4.9 API

Aucune API dédiée ; intégré au flux `POST /summarize` comme méthode d'extraction alternative.

### 7.4.10 Gestion des erreurs (cible)

| Erreur | Cause | Détection | Traitement | Message utilisateur |
|---|---|---|---|---|
| Bibliothèque OCR non implémentée | État actuel du projet | `status == "not_implemented"` | À faire : lever une exception explicite ou renvoyer un statut « OCR indisponible » clairement propagé jusqu'à l'utilisateur | « OCR non disponible pour ce document » |
| Échec de conversion image | Page corrompue | Exception à la conversion | Page ignorée, comptée en échec, traitement des autres pages poursuivi | « Certaines pages n'ont pas pu être traitées » |
| Temps de traitement excessif | Document très volumineux | Timeout / compteur de pages | Interruption après la limite configurée, retour partiel | « Document trop volumineux pour un traitement OCR complet » |

### 7.4.11 Logging (cible)

Journaliser par page : succès/échec OCR, score de confiance si disponible, durée totale du traitement OCR.

### 7.4.12 Sécurité

Aucun risque spécifique au-delà de ceux déjà couverts (validation d'entrée en amont, Tâche 2.1). Point d'attention : un moteur OCR basé sur un modèle vision local partage l'exposition déjà documentée pour le juge qualité (section 13).

### 7.4.13 Performance (cible)

Non mesurable à ce jour (fonctionnalité non implémentée). À déterminer expérimentalement sur le dataset de test une fois l'implémentation réalisée — cf. section 14.

### 7.4.14 Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T2.4-01 | PDF scanné simple (1 page) | PDF image pure, texte imprimé net | Texte extrait non vide | Haute *(bloqué : fonctionnalité non implémentée)* |
| T2.4-02 | PDF scanné de mauvaise qualité | Scan bruité/incliné | Texte partiel, qualité signalée basse | Moyenne *(bloqué)* |
| T2.4-03 | Échec total de l'OCR | Bibliothèque indisponible | Message d'erreur explicite, pipeline ne plante pas silencieusement | Haute — **applicable dès maintenant à l'état stub** |

### 7.4.15 Critères d'acceptation techniques

- [ ] *(Non satisfait)* Un PDF scanné simple produit du texte exploitable.
- [ ] *(Non satisfait)* Les erreurs OCR sont capturées et n'interrompent pas le pipeline.
- [ ] **Applicable immédiatement** : l'état « OCR non implémenté » doit produire un message explicite plutôt qu'un texte vide silencieux.
- [ ] Les limites de volume/temps sont documentées, même si la valeur exacte reste « à déterminer expérimentalement ».

### 7.4.16 Livrables

- Implémentation réelle de `extract_with_docling` (ou solution alternative), remplaçant le stub actuel.
- Dépendance ajoutée à `requirements.txt`.
- Rapport de qualité OCR.

### 7.4.17 Dépendances

- Tâche 2.3 (détection du besoin OCR réellement branchée).
- Choix technique arbitré entre Docling et réutilisation du modèle vision Ollama existant (cf. section 16, Décisions techniques).

### 7.4.18 Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| OCR non implémenté au moment du MVP | Tout PDF scanné produit un résultat vide et silencieux, perçu comme un bug plutôt qu'une limite connue | Certaine (état actuel) | Prioriser a minima un message d'erreur explicite avant l'implémentation complète ; documenter la limite dans l'interface (Phase 5) |
| Temps de traitement OCR imprévisible | Expérience utilisateur dégradée sur documents volumineux | Moyenne | Limiter le nombre de pages traitées par OCR au MVP, documenter la limite |

### 7.4.19 Definition of Done

```text
☐ Décision technique actée : Docling vs modèle vision Ollama (§16)
☐ Bibliothèque choisie intégrée et déclarée dans requirements.txt
☐ Conversion page → image fonctionnelle
☐ OCR page par page fonctionnel
☐ Assemblage du texte et rapport de qualité
☐ Erreurs OCR gérées individuellement par page
☐ Limite de volume/temps appliquée et documentée
☐ [Court terme, avant implémentation complète] Message d'erreur explicite remplaçant le texte vide silencieux actuel
```

---

## 7.5 Création du jeu de données de test

### 7.5.1 Objectif

Constituer un ensemble de PDF représentatifs des cas d'usage prioritaires, permettant de valider de façon reproductible l'upload, l'extraction, l'OCR et, en aval, le résumé.

### 7.5.2 Description technique

Le dataset est un ensemble de fichiers statiques versionnés (ou documentés) accompagné d'une description de chaque fichier et des scénarios de validation associés. Il sert de socle commun de test pour les Phases 2 à 5.

### 7.5.3 Fonctionnement détaillé

1. Sélection de PDF couvrant les cas suivants : 3 PDF textuels simples, 2 PDF multi-colonnes, 1 PDF scanné, 1 PDF avec tableaux, 1 PDF avec longues références — en anglais et français si possible.
2. Vérification de la licéité d'usage de chaque document (licence ouverte, arXiv, ou document produit en interne).
3. Dépôt des fichiers dans un répertoire dédié du dépôt (ex. `backend/tests/fixtures/pdf/` ou `docs/dataset/`).
4. Rédaction d'une fiche descriptive par fichier (origine, langue, nombre de pages, particularité testée).
5. Association de chaque fichier à un ou plusieurs scénarios de test (sections 7.1.14, 7.2.14, 7.3.14, 7.4.14).

### 7.5.4 Inputs

- Fichiers PDF sourcés (arXiv, documents internes, échantillons scannés).

### 7.5.5 Outputs

- Dossier de fichiers PDF.
- Fichier de description (Markdown ou JSON) répertoriant chaque PDF, ses caractéristiques et le scénario de test associé.

### 7.5.6 Algorithme

Non applicable (tâche de constitution de données, pas de traitement automatisé). Un script de vérification peut néanmoins être prévu :

```text
FONCTION valider_dataset(répertoire):
    POUR CHAQUE fichier DANS répertoire:
        VÉRIFIER extension == ".pdf"
        VÉRIFIER fichier lisible (validate_pdf_readable)
        VÉRIFIER présence d'une entrée de description associée
    RETOURNER rapport_de_couverture
```

### 7.5.7 Technologies et bibliothèques

Aucune dépendance technique nouvelle ; réutilisation de `validate_pdf_readable` pour un contrôle de non-régression du dataset lui-même.

### 7.5.8 Structures de données

```json
{
  "filename": "1007.3049v1.pdf",
  "category": "texte_simple",
  "language": "en",
  "pages": 12,
  "source": "arXiv (licence ouverte)",
  "purpose": "Validation extraction texte natif standard",
  "used_by_tests": ["T2.2-02"]
}
```

### 7.5.9 API

Non applicable — actif uniquement en environnement de test/développement.

### 7.5.10 Gestion des erreurs

| Erreur | Cause | Détection | Traitement | Message utilisateur |
|---|---|---|---|---|
| Fichier du dataset corrompu ou manquant | Erreur de dépôt/versionnement | Échec des tests automatisés au démarrage de la suite | Bloque l'exécution des tests concernés, à corriger avant merge | Message de test échoué (CI) |
| Fichier sans droits d'usage clairs | Oubli lors de la sélection | Revue manuelle | Retrait du fichier du dépôt | — |

### 7.5.11 Logging

Non applicable en production ; journalisation standard des tests (rapport pytest).

### 7.5.12 Sécurité

Vérifier qu'aucun PDF de test ne contient de données personnelles ou confidentielles réelles ; utiliser exclusivement des documents publics ou anonymisés.

### 7.5.13 Performance

Le dataset doit rester de taille raisonnable (quelques dizaines de Mo au total) pour ne pas alourdir le dépôt Git ni les temps de CI.

### 7.5.14 Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T2.5-01 | Couverture du dataset | Ensemble des fichiers déposés | Au moins un fichier par catégorie requise (texte simple ×3, multi-colonnes ×2, scanné ×1, tableaux ×1, références longues ×1) | Haute |
| T2.5-02 | Lisibilité de tous les fichiers | Chaque fichier du dataset | `validate_pdf_readable` retourne `True` pour chacun | Haute |
| T2.5-03 | Présence de la fiche descriptive | Chaque fichier | Entrée correspondante dans le fichier de description | Moyenne |

### 7.5.15 Critères d'acceptation techniques

- [ ] Le dataset couvre les catégories prioritaires listées dans le cahier des charges.
- [ ] Chaque fichier dispose d'une fiche descriptive (origine, langue, particularité).
- [ ] Les droits d'usage de chaque fichier sont vérifiés et documentés.
- [ ] Le dataset permet d'exécuter les scénarios de test des Tâches 2.1 à 2.4 sans dépendance externe.
- [ ] Le dataset est réutilisable pour la démonstration finale du projet.

### 7.5.16 Livrables

- Répertoire de fichiers PDF de test.
- Fichier de description structuré du dataset.
- Scénarios de validation associés (référencés dans les sections de test de chaque tâche).

### 7.5.17 Dépendances

- Aucune dépendance technique amont ; peut être constitué en parallèle des Tâches 2.1 à 2.4, mais doit être disponible avant leur phase de test.

### 7.5.18 Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Dataset non représentatif (trop homogène) | Bugs non détectés sur des cas réels (multi-colonnes, scans) | Moyenne | Suivre strictement la répartition par catégorie du cahier des charges |
| Problème de droits d'usage | Risque légal/retrait de contenu | Faible | Privilégier arXiv (licence ouverte) et documents produits en interne |

### 7.5.19 Definition of Done

```text
☐ Au moins 8 PDF réunis couvrant toutes les catégories requises
☐ Fiche descriptive par fichier
☐ Droits d'usage vérifiés
☐ Dataset intégré aux tests automatisés (pytest fixtures)
☐ Dataset validé comme support de démonstration finale
```

---

# 8. Interaction entre les tâches

```text
Tâche 2.5 (Dataset de test)
    │  (peut être menée en parallèle, doit être prête avant la phase de test)
    │
Tâche 2.1 (Upload PDF)
    │  dépendance forte : le fichier doit être stocké avant extraction
    ▼
Tâche 2.2 (Extraction texte natif)
    │  dépendance forte : résultat (pages vides ou non) conditionne 2.3
    ▼
Tâche 2.3 (Détection besoin OCR)
    │  dépendance conditionnelle
    ├── texte suffisant ──────────────► sortie directe vers Phase 3
    │
    ▼ (texte insuffisant)
Tâche 2.4 (OCR si nécessaire)
    │  dépendance forte sur 2.3, dépendance faible sur le choix technique (§16)
    ▼
Sortie vers Phase 3
```

- **Séquentielles** : 2.1 → 2.2 → 2.3 → 2.4.
- **Parallélisable** : 2.5 (dataset) peut être constituée indépendamment, en parallèle de 2.1–2.4, à condition d'être disponible avant l'écriture des tests.
- **Dépendance forte** : 2.2 dépend strictement du fichier stocké par 2.1 ; 2.4 dépend strictement de la décision de 2.3.
- **Dépendance faible** : 2.4 dépend d'un choix technique encore ouvert (Docling vs modèle vision Ollama), qui n'empêche pas l'avancement des autres tâches.

---

# 9. API de la phase

| Méthode | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| POST | `/upload` | Upload d'un PDF | `multipart/form-data` (`file`) | `UploadResponse` |
| DELETE | `/documents/{document_id}` | Suppression d'un document et de ses données associées | `document_id` (path) | `{document_id, status, message}` |
| GET | `/documents` | Liste des documents uploadés | — | `list[DocumentListItemResponse]` |
| GET | `/documents/{document_id}/pipeline-runs` | Historique des exécutions (dont extraction) pour un document | `document_id` (path) | `list[PipelineRunListItemResponse]` |
| POST | `/summarize` | Déclenche le pipeline complet (extraction incluse) pour un document uploadé | `{document_id, model?}` (JSON) | `SummarizeResponse` |

### `POST /upload` — détails

Voir section 7.1.9.

### `POST /summarize` — pertinence pour la Phase 2

Bien que cet endpoint orchestre l'ensemble du pipeline (Phases 2 à 4), c'est le point d'entrée qui déclenche effectivement l'extraction (Tâches 2.2–2.4). La Phase 2, prise isolément, ne s'exécute pas via un endpoint dédié : l'upload (2.1) est séparé, et l'extraction (2.2–2.4) est intégrée à l'appel global `/summarize`, orchestré par `DocumentPipeline.run`.

> **Point à clarifier** : le cahier des charges suggère une phase d'extraction autonome, potentiellement déclenchable indépendamment du résumé (par exemple pour afficher le texte extrait avant de lancer la génération IA, cf. Phase 5, Tâche 5.3). L'architecture actuelle couple extraction et résumé dans un seul appel synchrone. Voir section 17.

---

# 10. Modèles de données

### `Document` (table `documents`)

```json
{
  "id": "uuid",
  "filename": "article.pdf",
  "original_filename": "Article Original (1).pdf",
  "file_path": "C:\\...\\uploads\\{uuid}\\article.pdf",
  "status": "UPLOADING | completed | failed",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:03Z"
}
```

- `id` : identifiant unique, généré côté serveur, utilisé par toutes les phases suivantes.
- `filename` : nom nettoyé (basename, extension `.pdf` garantie).
- `original_filename` : nom tel que fourni par le client, conservé pour affichage/traçabilité.
- `file_path` : chemin absolu du fichier sur le système de fichiers serveur.
- `status` : cycle de vie de l'upload (transitoire `UPLOADING`, terminal `completed` ou `failed`).

### `ExtractionResult` (table liée à `pipeline_runs`)

```json
{
  "pipeline_run_id": "uuid",
  "extraction_method": "pymupdf4llm | docling | unknown",
  "quality_score": 82.5,
  "decision": "accept | fallback | skipped",
  "page_count": 12,
  "extraction_report": {
    "extraction": { "...": "rapport pymupdf_service" },
    "quality": { "...": "rapport quality_check" }
  }
}
```

- `extraction_method` : méthode réellement utilisée (reflète l'étiquetage actuel — voir réserve section 7.2.5 sur la dénomination).
- `quality_score` / `decision` : renseignés uniquement si `ENABLE_LLM_JUDGE=true` ; `null`/`"skipped"` sinon.

### Rapport d'extraction (fichier JSON, `extraction_report.json`)

```json
{
  "Filename": "article.pdf",
  "Input PDF": "C:\\...\\uploads\\{uuid}\\article.pdf",
  "Output Markdown": "C:\\...\\outputs\\article\\extraction\\markdown.md",
  "Pages": 12,
  "Markdown Size (characters)": 34521,
  "Extraction Status": "Success",
  "Extraction Method": "pymupdf4llm"
}
```

---

# 11. Gestion globale des erreurs

| Catégorie | Exemples (Phase 2) | Stratégie |
|---|---|---|
| **Erreurs utilisateur** | Fichier non-PDF, nom de fichier vide, fichier trop volumineux (non géré à ce jour) | HTTP 4xx, message explicite, aucune écriture persistante |
| **Erreurs système** | Disque plein, permissions insuffisantes | HTTP 500, rollback DB, nettoyage des fichiers partiels, log `logger.exception` |
| **Erreurs externes** | Service Ollama indisponible (juge qualité) | Dégradation : traitement continue sans évaluation qualité si possible, sinon échec du pipeline avec `failure_stage` explicite |
| **Erreurs de traitement** | PDF corrompu, extraction vide sans fallback fonctionnel | Statut `failed`, `failure_stage` renseigné (`"extraction"`), message contenant la cause (`{stage} failed: {exc}`) |
| **Logging** | Toute exception de haut niveau | `logger.exception` dans le bloc `except` global de `DocumentPipeline.run`, avec persistance du statut d'échec en base (`PipelineRun.status="failed"`, `.error_message`) |
| **Récupération** | Échec DB pendant la persistance de l'échec lui-même | `try/except` imbriqué avec `db.rollback()` dédié (déjà en place dans `document_pipeline.py`) |
| **Message utilisateur** | Toute erreur | Retournée via `SummarizeResponse.message`, code HTTP différencié (400 si `failure_stage=="validation"`, 500 sinon) |

**Point de vigilance identifié** (voir section 17 pour le détail) : la gestion d'erreurs de la Phase 2 dépend d'un mécanisme partagé avec l'ensemble du pipeline (`DocumentPipeline.run`), dont deux bugs de portée de variable ont été corrigés en base de code au cours du développement (variable d'exception hors de portée, écriture DB non protégée par sa condition). Ces corrections doivent être vérifiées comme présentes sur toutes les branches actives avant mise en production.

---

# 12. Tests globaux de la phase

| ID | Tâche | Scénario | Résultat attendu | Priorité |
|---|---|---|---|---|
| G2-01 | 2.1→2.2 | Parcours complet : upload PDF textuel valide → extraction | `document_id` créé, texte extrait non vide, `ExtractionResult` persisté | Haute |
| G2-02 | 2.1 | Upload fichier invalide | Rejet 400, aucune donnée persistée | Haute |
| G2-03 | 2.2→2.3 | PDF scanné pur | Extraction vide détectée, bascule OCR tentée | Haute |
| G2-04 | 2.4 | PDF scanné, OCR non implémenté | Comportement actuel : texte vide silencieux — **à corriger en message explicite** | Haute |
| G2-05 | 2.5 | Exécution de la suite de tests sur l'ensemble du dataset | Tous les fichiers du dataset traités sans crash serveur (succès ou échec explicite) | Haute |
| G2-06 | 2.1 | Upload concurrent de plusieurs fichiers | Chaque fichier reçoit un `document_id` distinct, pas de collision de répertoire | Moyenne |
| G2-07 | Intégration | Suppression d'un document après extraction | Fichiers uploadés et générés supprimés, lignes DB associées supprimées en cascade applicative | Moyenne |
| G2-08 | Performance | PDF de 12 pages, juge LLM désactivé | Extraction complète en moins d'1 seconde (référence mesurée : 0,094 s) | Basse |

---

# 13. Sécurité

| Risque | Impact | Protection |
|---|---|---|
| Traversée de chemin via nom de fichier malveillant | Écriture de fichier en dehors du répertoire prévu | `sanitize_filename` réduit au basename ; stockage isolé par `document_id` |
| Absence de limite de taille serveur | Déni de service par saturation disque | **Non protégé actuellement** — à implémenter en priorité (vérification `Content-Length` ou lecture par chunks avec seuil) |
| Upload de fichier non-PDF renommé `.pdf` | Traitement d'un contenu arbitraire par les bibliothèques d'extraction | Partiellement protégé : `validate_pdf_readable` rejette les fichiers illisibles par PyMuPDF avant tout traitement de contenu |
| PDF « bombe » (grand nombre de pages/objets) | Consommation CPU/mémoire excessive | **Non protégé actuellement** — aucun timeout ni limite de pages en extraction |
| Exposition du modèle vision local (juge qualité) | Consommation de ressources GPU/CPU partagées de la machine hôte | Contrôlée par la variable `ENABLE_LLM_JUDGE` (désactivable) et `LLM_JUDGE_MAX_PAGES` |
| Fuite d'information via messages d'erreur détaillés | Exposition de chemins serveur internes dans les réponses d'erreur | À vérifier : certains messages d'échec (`f"{stage} failed: {exc}"`) peuvent inclure des chemins de fichiers serveur — à filtrer avant exposition publique |

---

# 14. Performance et limites

- **Extraction PyMuPDF** : mesurée à ≈ 0,1 seconde pour un PDF de 12 pages (environnement de développement, sans juge LLM). Complexité linéaire au nombre de pages.
- **Juge qualité LLM (optionnel)** : coût significatif, dépendant du matériel GPU disponible ; sur un GPU à VRAM limitée, une évaluation multi-pages peut prendre plusieurs minutes. *Valeur précise à déterminer expérimentalement sur le dataset de test, matériel de référence à définir.*
- **OCR (Docling)** : non mesurable, fonctionnalité non implémentée à ce jour.
- **Limite de taille de fichier** : non appliquée côté serveur (recommandation : aligner sur la limite déjà présente côté frontend, 50 Mo, en la dupliquant côté serveur — ne jamais faire confiance uniquement à une validation client).
- **Limite de nombre de pages** : aucune limite actuelle sur l'extraction PyMuPDF ; à définir pour l'OCR (cahier des charges : « limitation de volume pour éviter un traitement trop long »), valeur à déterminer expérimentalement.
- **Concurrence** : aucun mécanisme de file d'attente ; les traitements sont synchrones par requête (`run_in_threadpool` côté FastAPI), ce qui limite le nombre de traitements simultanés à la taille du pool de threads par défaut.

---

# 15. MVP et évolutions futures

## 15.1 MVP

- Upload PDF avec validation d'extension et stockage isolé par document (fait).
- Extraction de texte natif via PyMuPDF pour les PDF textuels (fait).
- Détection binaire (pages vides / non vides) du besoin de fallback (fait, mais grossière).
- Dataset de test couvrant les cas prioritaires (à finaliser, Tâche 2.5).
- Message d'erreur explicite en cas d'échec OCR/extraction plutôt qu'un résultat vide silencieux (à corriger en priorité).
- Limite de taille de fichier appliquée côté serveur (à ajouter).

## 15.2 Évolutions futures

- Implémentation réelle de l'OCR (Docling ou modèle vision local) — actuellement hors MVP fonctionnel malgré la présence du point d'intégration.
- Détection du besoin OCR par seuil configurable et documenté (bascule de `needs_ocr` de code mort à mécanisme actif), éventuellement combinée à une analyse par page plutôt que globale.
- Utilisation réelle de `pymupdf4llm` pour une extraction Markdown structurée (titres, listes), au lieu du texte brut actuel.
- Extraction consciente de la mise en page multi-colonnes (tri des blocs de texte par position).
- Limite de débit (rate limiting) et file d'attente pour les uploads/traitements concurrents.
- Endpoint d'extraction autonome, découplé du déclenchement du résumé complet, pour permettre l'affichage du texte extrait avant génération IA (cf. Phase 5, Tâche 5.3).

Ces évolutions ne sont pas nécessaires à la validation du MVP de la Phase 2 mais doivent être tracées pour ne pas être oubliées.

---

# 16. Décisions techniques

| Décision | Choix | Justification | Alternative |
|---|---|---|---|
| Bibliothèque d'extraction texte natif | PyMuPDF (`fitz`), API texte brut | Déjà en place, rapide, dépendance légère | `pymupdf4llm` (Markdown structuré) — **recommandé pour une prochaine itération**, non retenu au MVP initial faute de branchement effectif |
| Identification des documents | UUID v4 généré serveur (`document_id`) | Évite les collisions de noms, indépendant du nom de fichier utilisateur | Nom de fichier + horodatage (rejeté : risque de collision et de traversée de chemin) |
| Stockage des fichiers uploadés | Système de fichiers local, un répertoire par `document_id` | Simplicité pour un MVP mono-serveur, cohérent avec `UPLOAD_DIR`/`OUTPUT_DIR` déjà configurés | Stockage objet (S3/MinIO) — pertinent si passage en environnement multi-instance |
| Déclenchement OCR | *(à trancher)* Docling vs réutilisation du modèle vision Ollama déjà intégré comme juge qualité | Le modèle vision est déjà opérationnel dans le projet (utilisé pour le score qualité) et pourrait transcrire une page directement, évitant une dépendance supplémentaire (Docling) | Docling — mise en page plus fidèle en théorie, mais bibliothèque non encore intégrée (absente de `requirements.txt`) |
| Persistance de l'historique d'extraction | Table `ExtractionResult` liée à `PipelineRun` | Répond à l'exigence d'historique de la Phase 5 (Tâche 5.6) dès la Phase 2 | Journalisation fichier seule (rejetée : pas interrogeable pour l'interface historique) |

---

# 17. Points à clarifier

### Point à clarifier — Docling non implémenté

**Problème :** le connecteur Docling, seul mécanisme d'OCR prévu, est un stub retournant systématiquement un texte vide (`status: "not_implemented"`).
**Interprétations :** (a) l'OCR est explicitement hors périmètre du MVP de la Semaine 2 et sera traité ultérieurement ; (b) l'OCR devait être fonctionnel dès cette phase selon le cahier des charges (« si faisable dans le MVP »).
**Recommandation :** traiter l'OCR complet comme une évolution post-MVP (cohérent avec la formulation conditionnelle du cahier des charges « si faisable dans le MVP »), mais livrer immédiatement un signalement explicite (message d'erreur ou statut dédié) à la place du texte vide silencieux actuel, afin de ne pas masquer un échec comme un succès.

### Point à clarifier — Étiquetage « PyMuPDF4LLM »

**Problème :** le rapport d'extraction annonce la source `"PyMuPDF4LLM"` alors que le code utilise l'API texte brut de PyMuPDF (`page.get_text()`), sans dépendance à la bibliothèque `pymupdf4llm`.
**Interprétations :** (a) simple erreur de nommage à corriger ; (b) intention d'intégrer réellement `pymupdf4llm` prochainement, le nom anticipant ce changement.
**Recommandation :** corriger le nom immédiatement (`"PyMuPDF (texte brut)"`) pour refléter l'état réel, et ouvrir un chantier séparé pour l'intégration effective de `pymupdf4llm` si un Markdown structuré est requis par la Phase 3.

### Point à clarifier — Détection OCR non branchée

**Problème :** `needs_ocr` (seuil de caractères configurable) existe mais n'est jamais appelée ; seule la condition « zéro page extraite » déclenche le fallback.
**Interprétations :** (a) simplification volontaire pour le MVP ; (b) oubli d'intégration lors du développement.
**Recommandation :** brancher `needs_ocr` (ou une variante par ratio de pages) dans `extract_pdf_content`, avec un seuil documenté et potentiellement configurable par variable d'environnement, cohérent avec l'esprit de la Tâche 2.3 du cahier des charges.

### Point à clarifier — Couplage extraction / résumé

**Problème :** l'extraction (Phase 2) n'est pas déclenchable indépendamment du résumé complet (Phase 4) : les deux sont exécutés dans le même appel `POST /summarize`.
**Interprétations :** (a) acceptable pour le MVP, l'utilisateur consulte le texte extrait après coup via les endpoints de lecture ; (b) la Phase 5 (Tâche 5.3, affichage du texte extrait avant résumé) suppose un découplage.
**Recommandation :** conserver le couplage actuel pour le MVP (simplicité), mais le signaler explicitement comme contrainte connue à la Phase 5.

### Point à clarifier — Absence de limite de taille serveur

**Problème :** aucune vérification de taille n'existe côté API, alors que le cahier des charges l'exige explicitement (Tâche 2.1).
**Interprétations :** aucune ambiguïté d'interprétation — c'est un écart direct à corriger.
**Recommandation :** implémenter une vérification de taille côté serveur avant écriture complète en mémoire, alignée sur la limite déjà en place côté frontend (50 Mo), configurable par variable d'environnement.

---

# 18. Livrables de la phase

- Code : endpoints `POST /upload`, `DELETE /documents/{id}`, `GET /documents`, `GET /documents/{id}/pipeline-runs`.
- Modules : `extraction/extractor.py`, `pymupdf_service.py`, `docling_service.py` (stub), `quality_check.py`, `evaluation/llm_judge.py`.
- Modèles : `Document`, `ExtractionResult` (SQLAlchemy + migrations Alembic).
- Interface : composant d'upload frontend (`App.jsx`).
- Dataset : ensemble de PDF de test avec fiche descriptive (Tâche 2.5).
- Rapports : `extraction_report.json` par document traité.
- Documentation : le présent document.

---

# 19. Definition of Done globale

```text
☐ Upload PDF fonctionnel avec validation et stockage traçable
☐ Extraction de texte natif fonctionnelle sur PDF standards
☐ Détection du besoin OCR branchée sur un seuil documenté (pas seulement "pages vides")
☐ Comportement explicite (message clair) en cas d'OCR indisponible
☐ Dataset de test complet et versionné
☐ Historique des extractions persisté en base
☐ Limite de taille de fichier appliquée côté serveur
☐ Erreurs de chaque étape capturées, journalisées et remontées de façon compréhensible
☐ Tests unitaires et d'intégration couvrant les scénarios de la section 12
☐ Documentation technique à jour (ce document)
```

---

# 20. Matrice de traçabilité

| Exigence (cahier des charges) | Tâche | Module | Test | Critère d'acceptation |
|---|---|---|---|---|
| Upload fichier .pdf | 2.1 | `api/routes/upload.py` | T2.1-01 | §7.1.15 |
| Vérification du type de fichier | 2.1 | `api/dependencies.py` | T2.1-03 | §7.1.15 |
| Limite de taille | 2.1 | *(non implémenté)* | T2.1-06 | §7.1.15 (non satisfait) |
| Message d'erreur si fichier invalide | 2.1 | `api/routes/upload.py` | T2.1-03, T2.1-04 | §7.1.15 |
| Stockage temporaire | 2.1 | `api/routes/upload.py` | T2.1-01 | §7.1.15 |
| Extraction du texte brut | 2.2 | `extraction/pymupdf_service.py` | T2.2-01, T2.2-02 | §7.2.15 |
| Conservation de l'ordre des pages | 2.2 | `extraction/pymupdf_service.py` | T2.2-02 | §7.2.15 |
| Journalisation des pages vides | 2.2 | `extraction/pymupdf_service.py` | T2.2-03 | §7.2.15 (partiel — comptage oui, log dédié à ajouter) |
| Détection PDF probablement scanné | 2.3 | `extraction/extractor.py` (`needs_ocr`, non branché) | T2.3-01, T2.3-02 | §7.3.15 (partiel) |
| Décision OCR explicable | 2.3 | `evaluation/llm_judge.py`, `quality_check.py` | T2.3-04, T2.3-05 | §7.3.15 |
| Conversion pages en images + OCR | 2.4 | `extraction/docling_service.py` (stub) | T2.4-01, T2.4-02 | §7.4.15 (non satisfait) |
| Gestion des erreurs OCR | 2.4 | `extraction/docling_service.py` | T2.4-03 | §7.4.15 (applicable dès l'état stub) |
| Dataset PDF de test couvrant les cas prioritaires | 2.5 | Répertoire de test dédié | T2.5-01, T2.5-02, T2.5-03 | §7.5.15 |

---

*Fin du document — Phase 2. Le prochain document indépendant (Phase 3) suivra la même structure et la même charte graphique.*
