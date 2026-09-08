> **Note de mise en forme (conversion `.docx`)**
> Titres (`#`/`##`/`###`) → bleu Yonnov'IA `#2596BE`, police serif grasse (ex. Georgia Bold), conforme au rendu de la charte. Corps de texte, tableaux, code → noir uniquement. Logo Yonnov'IA (`frontend/public/logo.jpg`) en en-tête Word sur **chaque page**, pas seulement la page de garde. Procédure d'application détaillée en tête du document Phase 2.
>
> **Sommaire volontairement distinct des Phases 2, 3 et 4.** La Phase 5 n'ajoute ni infrastructure serveur nouvelle (Phase 2), ni heuristique de texte (Phase 3), ni comportement de modèle de langage (Phase 4) : elle assemble une **interface produit** au-dessus de ce qui existe déjà. La structure ci-dessous reflète cette nature (panorama des écrans, sources de données consommées) plutôt qu'un calque des trois documents précédents.

---

# PAGE DE GARDE

![Logo Yonnov'IA](../frontend/public/logo.jpg)

# Yonnov'IA
## Documentation technique

# Phase 5 — Interface web, visualisation et exports
## Sprint 5 — Application web et exports

**Durée estimée :** Semaines 5 et 6
**Version du document :** 1.0
**Date :** 26/08/2026
**Auteur :** Équipe Yonnov'IA — Team07-E26

---

# SOMMAIRE

*(champ TOC à régénérer automatiquement lors de la conversion Word)*

1. Vue d'ensemble de la phase
2. Position dans le produit
3. Deux sources de vérité : fichiers et base de données
4. Panorama de l'interface
5. Documentation détaillée des tâches
   5.1 Interface principale
   5.2 Page de consultation du résumé
   5.3 Affichage du texte extrait et des sections
   5.4 Export Markdown
   5.5 Export PDF
   5.6 Historique des documents traités
6. Dépendances entre les tâches
7. Contrats de données consommés par le frontend
8. Gestion des erreurs et des états
9. Plan de tests de la phase
10. Sécurité et confidentialité
11. Performance et limites
12. MVP et évolutions futures
13. Décisions techniques actées
14. Points ouverts et zones grises
15. Livrables de la phase
16. Definition of Done globale
17. Matrice de traçabilité

---

# 1. Vue d'ensemble de la phase

## 1.1 Objectif

La Phase 5 rend le pipeline (Phases 2 à 4) utilisable par une personne sans accès à l'API : une application web unique permettant d'importer un PDF, de suivre son traitement, de consulter le résumé structuré, les mots-clés, l'historique des traitements passés, et d'exporter les résultats.

## 1.2 Nature du travail de cette phase

Contrairement aux phases précédentes, la Phase 5 ne traite aucune donnée elle-même : elle **consomme** des API déjà construites (Phases 2 à 4) et les met en forme. La difficulté n'est donc pas algorithmique mais porte sur trois points : la cohérence entre ce que l'interface promet à l'utilisateur et ce que le backend fournit réellement, la gestion des états intermédiaires (chargement, erreur, absence de données), et l'articulation entre deux sources de données distinctes exposées par le backend (détaillées en section 3).

## 1.3 Résultat attendu en sortie de phase

- Une application React (Vite) à page unique, avec navigation par état interne (pas de routeur d'URL).
- Un flux complet : import → traitement → consultation du résumé et des mots-clés → export.
- Un historique consultable des documents et de leurs exécutions passées, avec suppression.
- Trois formats d'export du résumé final : Markdown, JSON, PDF.

## 1.4 Périmètre

**Inclus** : les 6 tâches du cahier des charges telles qu'implémentées dans `frontend/src/App.jsx`, `api.js`, `data.js`, et les routes backend qu'elles consomment (`summary.py`, `documents.py`, `pipeline_runs.py`, `upload.py`, `summarize.py` — ces deux dernières documentées en détail dans les Phases 2 et 4).

**Non inclus** : toute nouvelle logique de traitement PDF, NLP ou LLM (déjà couverte). L'authentification/autorisation des utilisateurs n'est pas mentionnée par le cahier des charges et n'existe pas dans le code — l'application est actuellement mono-utilisateur, sans notion de compte.

**Point de périmètre à noter d'emblée** : la page nommée « Texte extrait » (Tâche 5.3) n'affiche, dans l'implémentation actuelle, **ni le texte brut, ni le texte nettoyé, ni les sections réellement détectées par la Phase 3** — elle affiche le résumé final généré par la Phase 4, reformaté. Ce point est développé en détail en section 5.3 et constitue l'écart le plus significatif de cette phase par rapport au cahier des charges.

---

# 2. Position dans le produit

```text
Phases 2, 3, 4 (backend)
   POST /upload, POST /summarize
   GET /summary/{filename}[...], GET /documents, GET /pipeline-runs...
        │
        ▼
┌───────────────────────────────────────────────┐
│                  PHASE 5                          │
│                                                     │
│  5.1 Coquille applicative (AppShell, navigation)    │
│        │                                           │
│        ▼                                           │
│  Upload ──▶ Suivi ──▶ 5.2 Résumé ──▶ Mots-clés       │
│                  │                                  │
│                  ▼                                  │
│           5.3 "Texte extrait" (voir §3, §5.3)        │
│                                                     │
│  5.4 Export .md   5.5 Export .pdf   Export .json     │
│                                                     │
│  5.6 Historique (documents + exécutions persistées)  │
└───────────────────────────────────────────────┘
        │
        ▼
   Utilisateur final (navigateur)
```

La Phase 5 n'a pas de sortie vers une phase suivante : c'est la couche terminale du pipeline. Elle a en revanche **deux points d'entrée backend distincts et non unifiés**, ce qui structure toute la suite de ce document — voir section 3.

---

# 3. Deux sources de vérité : fichiers et base de données

C'est la particularité architecturale la plus importante à comprendre avant d'aborder les tâches une par une. Le backend expose, pour un même document traité, **deux chemins d'accès indépendants** :

| | Route filename-based (héritée) | Route document_id-based (persistance DB, Phase 2/4) |
|---|---|---|
| Identifiant utilisé | Nom de fichier (`filename`, chaîne libre) | `document_id` (UUID, clé primaire `documents.id`) |
| Source des données | Système de fichiers (`OUTPUT_DIR/{stem}/summary/summary.{md,json}`) | Base PostgreSQL (`documents`, `pipeline_runs`, `summaries`, ...) |
| Endpoints | `GET /summary/{filename}`, `/markdown`, `/json`, `/pdf` | `GET /documents`, `GET /documents/{id}/pipeline-runs`, `GET /pipeline-runs/{id}`, `DELETE /pipeline-runs/{id}`, `DELETE /documents/{id}` |
| Pages frontend consommatrices | `SummaryPage`, `ExtractionPage`, `KeywordsPage`, `ExportsPage` | `HistoryPage` |
| Fonction `api.js` | `getSummary(filename)`, `downloadArtifact`, `downloadPdf(filename)` | `getDocuments`, `getDocumentPipelineRuns`, `getPipelineRun`, `deleteDocument`, `deletePipelineRun` |

### Conséquences concrètes

- **`GET /summary/{filename}` ignore entièrement l'état de la base de données.** Si un document a été supprimé via `DELETE /documents/{document_id}` (Tâche 5.6) mais que son dossier `OUTPUT_DIR/{stem}/` existe encore pour une raison quelconque (autre document partageant le même nom de fichier, ou incohérence), les endpoints d'export continueraient de le servir sans qu'aucune trace de ce document n'existe plus en base.
- **Une collision de nom de fichier entre deux documents distincts** (deux uploads de `article.pdf` par deux utilisateurs différents, chacun avec son propre `document_id`) partagerait le **même** dossier de sortie sur le système de fichiers (`OUTPUT_DIR/article/`), puisque ce chemin est dérivé du nom de fichier, pas du `document_id` — voir Documentation Phase 2, §17, sur ce même sujet côté extraction.
- **Le flux normal de l'application** (upload → traitement → consultation immédiate du résumé) n'utilise jamais les routes `document_id`-based pour afficher le résumé lui-même : `App.jsx::startProcessing` appelle `summarizePdf(uploadedDocumentId)` (document_id) mais ensuite `getSummary(summarizeResponse.filename)` (filename) pour récupérer le contenu à afficher. Les deux identifiants coexistent donc dans le même parcours utilisateur.

Cette dualité n'est pas nécessairement un défaut bloquant pour le MVP (les deux chemins fonctionnent indépendamment), mais elle représente une dette d'architecture à connaître avant toute évolution (authentification multi-utilisateur, notamment, où la collision par nom de fichier deviendrait un vrai problème de confidentialité entre utilisateurs).

---

# 4. Panorama de l'interface

L'application est une **single-page application sans routeur d'URL** : `App.jsx` maintient un état `page` (chaîne parmi `home`, `upload`, `processing`, `extraction`, `summary`, `keywords`, `history`, `exports`) et bascule entre composants via un simple objet de correspondance (`pages[page]`). Conséquence directe : il n'existe pas d'URL propre à chaque écran (`/summary`, `/history`, ...) — un rafraîchissement du navigateur ramène toujours à l'écran d'accueil et perd l'état en mémoire (fichier importé, résumé affiché), puisque rien n'est persisté côté client (pas de `localStorage`, pas de requête de restauration au montage autre que celles de `HistoryPage`).

| Écran (`page`) | Composant | Tâche(s) associée(s) |
|---|---|---|
| `home` | `HomePage` | 5.1 (vitrine, présentation, équipe) |
| `upload` | `UploadPage` | 5.1 (import de fichiers) |
| `processing` | `ProcessingPage` | 5.1 (suivi — voir réserve en §5.1) |
| `extraction` | `ExtractionPage` | 5.3 (voir réserve importante en §5.3) |
| `summary` | `SummaryPage` | 5.2 |
| `keywords` | `KeywordsPage` | 5.2 (extension, non listée séparément dans le cahier des charges mais alignée avec « Mots-clés ») |
| `history` | `HistoryPage` | 5.6 |
| `exports` | `ExportsPage` | 5.4, 5.5 |

---

# 5. Documentation détaillée des tâches

## 5.1 Interface principale

### Objectif
Fournir la coquille applicative (navigation, mise en page, connexion au backend) et le parcours d'import/suivi de traitement.

### Composants réels

- **`AppShell`** : barre latérale de navigation (`navigation` défini dans `data.js`, 8 entrées), en-tête avec bouton « Nouveau document » (réinitialise tout l'état applicatif via `reset()`), zone de contenu.
- **`HomePage`** : page vitrine (statistiques calculées côté client à partir de `summaryDetail`, présentation du pipeline en 4 étapes marketing, section équipe).
- **`UploadPage`** : zone de dépôt (glisser-déposer ou sélection), liste des fichiers avec statut d'import, validation côté client (type MIME ou extension `.pdf`, taille ≤ 50 Mo).
- **`ProcessingPage`** : barre de progression et journal d'événements.

### Le parcours réel, étape par étape (`App.jsx`)

1. `handleFiles` filtre les fichiers déposés (PDF, ≤ 50 Mo) et appelle `uploadPdf` **séquentiellement** pour chaque fichier valide (boucle `for...of`, pas d'envoi parallèle). Chaque succès met à jour `uploadedDocumentId`/`uploadedFilename` avec le **premier** fichier importé avec succès seulement (`setUploadedFilename((current) => current || response.filename)`).
2. `startProcessing` : appelle `summarizePdf(uploadedDocumentId)` — c'est cet appel unique qui déclenche, côté backend, l'intégralité des Phases 2, 3 et 4 (extraction, prétraitement, inférence, fusion), de façon synchrone du point de vue du frontend.
3. Pendant cet appel, la barre de progression n'est **pas** alimentée par un flux d'événements réel du backend : `setProgress` est appelé à seulement trois moments fixes (25 % au lancement, 80 % après la résolution de `summarizePdf`, 100 % après la résolution de `getSummary`). Les 8 étapes visuellement détaillées de `pipelineSteps` (`data.js` : Validation, Extraction, Prétraitement, Mots-clés, Découpage, Préparation, Inférence, Synthèse finale) sont donc une **animation dérivée de ces 3 paliers**, pas un reflet de l'avancement réel du pipeline stage par stage.
4. À la résolution, `getSummary(summarizeResponse.filename)` récupère le contenu à afficher (bascule sur la route filename-based, §3) et navigue automatiquement vers l'écran `summary`.

### Ce que le cahier des charges attend et qui est satisfait

- L'utilisateur peut importer un ou plusieurs PDF.
- Le traitement peut être lancé depuis l'interface.
- Les résultats sont affichés (résumé, mots-clés).
- Les erreurs sont visibles (bandeaux d'alerte sur les écrans concernés, message d'erreur propagé depuis l'API via `apiRequest`).

### Ce qui s'écarte de l'esprit « suivi en direct »

Le nom de l'écran (« Suivi du traitement ») et son contenu visuel (8 étapes détaillées) suggèrent un suivi granulaire du pipeline, alors que le mécanisme réel n'a que trois paliers de progression déclenchés par deux promesses JavaScript. Ce n'est pas un défaut fonctionnel (le résultat final est correct), mais un écart entre la promesse visuelle et la réalité technique, à corriger si un mécanisme de suivi réel (WebSocket, Server-Sent Events, ou polling d'un statut persisté) est jugé prioritaire.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.1-01 | Import d'un PDF valide | Fichier `.pdf` ≤ 50 Mo | Fichier ajouté à la liste, statut `uploaded` après l'appel `POST /upload` | Haute |
| T5.1-02 | Import d'un fichier non-PDF | Fichier `.docx` | Rejeté côté client, message d'erreur affiché, aucun appel réseau | Haute |
| T5.1-03 | Import de plusieurs fichiers | 3 PDF valides | Les 3 sont importés séquentiellement ; seul le premier devient le document actif (`uploadedDocumentId`) | Moyenne |
| T5.1-04 | Échec de `POST /summarize` | Backend renvoie une erreur | `processingError` affiché, navigation reste sur l'écran de suivi, `progress` remis à 0 | Haute |
| T5.1-05 | Réinitialisation | Clic sur « Nouveau document » | Tous les états (fichiers, résumé, progression) réinitialisés, retour à l'écran d'import | Moyenne |
| T5.1-06 | Rafraîchissement du navigateur en cours de consultation | F5 sur l'écran résumé | Retour à l'écran d'accueil, perte de l'état en mémoire (comportement actuel, non testé automatiquement) | Basse (comportement connu, pas un bug à proprement parler) |

### Critères d'acceptation

- [x] L'utilisateur peut importer un PDF.
- [x] Le traitement peut être lancé.
- [x] Les résultats sont affichés après traitement.
- [x] Les erreurs sont visibles.
- [ ] *(Écart documenté, non bloquant)* Le suivi de progression reflète l'avancement réel du pipeline plutôt que 3 paliers fixes.

### Livrables
`AppShell`, `HomePage`, `UploadPage`, `ProcessingPage` (`App.jsx`), `navigation`/`pipelineSteps` (`data.js`).

---

## 5.2 Page de consultation du résumé

### Objectif
Afficher le résumé structuré de façon lisible, avec métadonnées, mots-clés et accès direct aux exports.

### Composant réel : `SummaryPage`

- Extrait la section « Résumé exécutif »/« Executive Summary » du Markdown via une regex (`parseSummarySections` + recherche `/executive summary|résumé synthétique/i`) pour la mettre en avant visuellement.
- Découpe l'intégralité du Markdown en sections par ses propres titres `##` (`parseSummarySections`, simple `split` sur `^##\s+`) pour la « Lecture structurée » — **reparsing côté client** d'un Markdown déjà produit par le backend (Phase 4, `parse_summary_to_json`), plutôt que consommation directe du JSON structuré déjà disponible (`summaryDetail` n'expose que le Markdown brut et les métadonnées/mots-clés, pas `summary_structured`/`summary.json` — voir §7).
- Panneau métadonnées (auteurs, source, année, pages) et panneau mots-clés (5 premiers), tous deux directement issus de `SummaryDetailResponse`.
- Actions : copier le Markdown dans le presse-papiers, naviguer vers les exports.

### Une redondance de traitement à noter

Le backend produit déjà une version JSON structurée du résumé (`parse_summary_to_json`, Documentation Phase 4 §6.3), mais celle-ci n'est **pas exposée** par `GET /summary/{filename}` (`SummaryDetailResponse` ne contient que `summary: str`, le Markdown). Le frontend est donc contraint de **reparser** ce Markdown avec sa propre logique (`parseSummarySections`), moins robuste que le parseur backend dédié (par exemple, il ne gère pas le mapping bilingue de titres de `heading_map` — il utilise directement le titre tel qu'il apparaît dans le Markdown, ce qui fonctionne mais duplique une logique déjà écrite côté serveur).

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.2-01 | Résumé complet disponible | `summaryDetail` renseigné | Toutes les sections affichées, résumé exécutif mis en avant | Haute |
| T5.2-02 | Aucun résumé disponible | `summaryDetail` null | Messages de repli (« Lancez un traitement... »), aucune erreur JavaScript | Haute |
| T5.2-03 | Résumé en français | Sections en français (« Résumé synthétique ») | Section exécutive correctement identifiée par la regex bilingue | Haute |
| T5.2-04 | Copie du Markdown | Clic sur « Copier » | Contenu copié dans le presse-papiers, notification affichée | Basse |

### Critères d'acceptation

- [x] Le résumé est lisible, sections visuellement séparées.
- [x] Les mots-clés sont visibles.
- [x] Les exports sont accessibles depuis cette page.
- [ ] *(Amélioration possible)* Le JSON structuré déjà produit par le backend est réutilisé tel quel plutôt que reparsé côté client.

### Livrables
`SummaryPage` (`App.jsx`), route consommée : `GET /summary/{filename}`.

---

## 5.3 Affichage du texte extrait et des sections

### Objectif (cahier des charges)
Permettre à l'utilisateur de consulter le texte brut extrait, le texte nettoyé, et la segmentation par section produits par les Phases 2 et 3, avec recherche interne.

### Constat : cette tâche n'affiche pas les données qu'elle est censée afficher

C'est le point le plus important de ce document. Le composant `ExtractionPage` (écran « Texte extrait », `page: 'extraction'`) est câblé sur `summaryDetail`, exactement comme `SummaryPage` :

```js
const source = summaryDetail?.summary || 'Aucun résultat disponible...';
const sections = parseSummarySections(summaryDetail?.summary)...
```

`summaryDetail.summary` est le **résumé final généré par la Phase 4** (contenu de `summary.md`), pas le texte extrait par la Phase 2 (`extraction/markdown.md`) ni le texte nettoyé par la Phase 3 (`preprocessing/cleaned_text.txt`). De même, les « sections » affichées par les onglets « Par section » proviennent du même découpage naïf par titres `##` que `SummaryPage` (§5.2) — ce sont les 12 sections du résumé structuré (Sujet principal, Méthodologie, ...), **pas** les sections scientifiques réellement détectées par `preprocessing/sections.py` (Documentation Phase 3, §7.2), qui ne sont jamais transmises au frontend.

### Pourquoi cet écart existe (cause racine côté backend)

Aucune route API n'expose, à ce jour, le texte brut, le texte nettoyé, ou la liste des sections détectées par la Phase 3 pour un document donné en dehors du contexte d'un `PipelineRun` complet (`GET /pipeline-runs/{id}` expose bien `preprocessing.sections`, `preprocessing.cleaning_report`, etc. — mais uniquement via la route **document_id-based** de l'historique, §3, jamais consommée par `ExtractionPage`, qui utilise exclusivement la route filename-based réservée au résumé). Techniquement, les données existent (persistées en base par la Phase 3, cf. Documentation Phase 3 §9) et sont même déjà exposées par une route existante (`GET /pipeline-runs/{id}`) — mais l'écran « Texte extrait » ne les consomme pas.

### Ce qui fonctionne malgré tout sur cet écran

- Recherche textuelle en direct dans le contenu affiché (recherche simple `String.split`, insensible à la casse).
- Bascule entre trois vues (« Synthèse Markdown » brute, « Résumé généré » rendu, « Par section »).
- Copie du texte affiché.
- Indicateurs (nombre de mots, nombre de « sections », statut).
- Ces fonctionnalités sont réelles et de bonne qualité — elles s'appliquent simplement à la mauvaise donnée source par rapport à l'intention du cahier des charges.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.3-01 | Recherche dans le contenu affiché | Terme présent plusieurs fois | Nombre d'occurrences affiché correctement | Moyenne |
| T5.3-02 | Bascule entre les 3 onglets | — | Contenu cohérent affiché dans chaque mode (brut, rendu, par section) | Moyenne |
| T5.3-03 *(à écrire après correction)* | Consultation du texte réellement extrait (Phase 2) | Document traité | Le texte affiché correspond à `extraction/markdown.md`, pas au résumé | Haute — bloquée tant que l'écart n'est pas corrigé |
| T5.3-04 *(à écrire après correction)* | Consultation des sections réellement détectées (Phase 3) | Document avec sections standards | Les sections affichées correspondent à `preprocessing.sections`, avec `missing_sections` visibles | Haute — idem |

### Critères d'acceptation

- [ ] *(Non satisfait)* L'utilisateur peut vérifier le texte source réellement extrait (avant résumé).
- [ ] *(Non satisfait)* Les sections détectées affichées sont celles produites par la Phase 3, y compris les sections manquantes.
- [x] Une fonctionnalité de recherche interne existe et fonctionne sur le contenu actuellement affiché.
- [x] Le résumé peut être comparé... au résumé lui-même (trivialement vrai, mais ne répond pas à l'intention du critère : comparer résumé et texte source).

### Livrables
`ExtractionPage` (`App.jsx`) — **fonctionnellement à reconnecter** à une route exposant le texte brut/nettoyé/sections d'un document (existe déjà via `GET /pipeline-runs/{id}`, réutilisable moyennant un changement d'identifiant consommé par cet écran : `document_id` au lieu de `filename`).

### Risque
| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Confusion utilisateur entre « texte extrait » et « résumé » sous deux noms d'écran différents mais un contenu identique | Perte de confiance dans l'outil (l'utilisateur ne peut pas vérifier ce que le résumé a réellement lu), fonctionnalité de contrôle qualité manuelle inexistante en pratique | Certaine (constat direct de code) | Reconnecter `ExtractionPage` à `GET /pipeline-runs/{id}` (ou créer une route filename-based équivalente pour rester cohérent avec le reste de l'écran), en utilisant `preprocessing.sections`/`missing_sections` et le contenu persisté de l'extraction |

---

## 5.4 Export Markdown

### Objectif
Permettre le téléchargement du résumé structuré au format `.md`.

### Fonctionnement réel

`ExportsPage` appelle `downloadArtifact(summaryDetail.downloads.markdown, 'summary.md')`, qui effectue un `fetch` vers `GET /summary/{filename}/markdown` (route filename-based, §3), récupère le corps de réponse en `Blob`, puis déclenche un téléchargement navigateur via un lien `<a download>` temporaire. Le nom de fichier proposé au téléchargement respecte l'en-tête `Content-Disposition` renvoyé par le serveur si présent, sinon retombe sur le nom par défaut fourni au client.

Côté serveur, `download_summary_markdown` (`summary.py`) sert directement le fichier `summary.md` déjà écrit sur disque par la Phase 4 (`document_pipeline.py::_write_text`) — aucune régénération, aucune transformation supplémentaire à l'export.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.4-01 | Export d'un résumé existant | Document traité avec succès | Fichier `.md` téléchargé, contenu identique à celui affiché dans `SummaryPage` | Haute |
| T5.4-02 | Export sans résumé disponible | Aucun traitement effectué | Bouton d'export non actionnable (`summaryDetail` requis pour afficher la grille d'export) | Moyenne |
| T5.4-03 | Fichier de résumé supprimé du disque entre génération et export | Suppression manuelle du fichier serveur | `404 Generated summary not found`, message d'erreur affiché côté client (`notify`) | Basse |

### Critères d'acceptation

- [x] Le fichier Markdown est généré et téléchargeable.
- [x] La structure (12 sections) est conservée telle que produite par la Phase 4.
- [x] Métadonnées et mots-clés sont inclus (ils font partie du Markdown final, `grounded` par la Phase 4).
- [x] Le fichier est un Markdown standard, lisible dans tout éditeur.

### Livrables
`ExportsPage` (bouton Markdown), `api.js::downloadArtifact`, route `GET /summary/{filename}/markdown`.

---

## 5.5 Export PDF du résumé

### Objectif
Permettre le téléchargement du résumé structuré sous une mise en page PDF soignée.

### Fonctionnement réel

`ExportsPage` appelle `downloadPdf(summaryDetail.filename)` → `GET /summary/{filename}/pdf`. Contrairement au Markdown et au JSON (servis tels quels), **le PDF est généré à la volée à chaque téléchargement** par `app/services/export/pdf_generator.py` :

1. `_load_persisted_summary` relit `summary.json` (priorité) ou `summary.md` (repli) depuis le disque — troisième lecture indépendante de la même donnée après celle faite pour `GET /summary/{filename}` et pour l'export Markdown.
2. `_markdown_story` convertit le Markdown en une séquence d'éléments ReportLab (titres, paragraphes, puces, séparateurs), avec un sous-ensemble volontairement restreint de syntaxe Markdown (gras, code inline, titres, puces, séparateurs horizontaux — pas de tableaux, pas d'images, pas de liens).
3. Mise en page avec en-tête/pied de page (`_draw_page` : logo textuel « YONNOVIA », numéro de page), police Unicode embarquée avec ReportLab (`Vera`/`Vera-Bold`) si disponible, repli sur Helvetica sinon.
4. Le PDF est écrit dans un fichier temporaire **au même emplacement que le résumé** (`summary_directory`), puis servi et supprimé automatiquement après l'envoi complet de la réponse (`BackgroundTask(_remove_temporary_file, ...)`), pour ne jamais laisser de fichier temporaire orphelin sur le serveur.

### Vérification réelle effectuée en session de développement

Un test bout-en-bout (upload → résumé → export PDF) a été exécuté sur l'environnement de développement du projet : le PDF produit fait 44 Ko, avec un en-tête de fichier `%PDF-1.4` valide, confirmant que la chaîne complète fonctionne de bout en bout sur le code actuel.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.5-01 | Export PDF d'un résumé complet | Document traité | PDF valide généré (en-tête `%PDF`), toutes les sections présentes | Haute — vérifié réellement en session de développement |
| T5.5-02 | Résumé absent sur le disque | `summary.json`/`summary.md` manquants | `404`, exception `SummarySourceNotFoundError` capturée proprement, aucun fichier temporaire laissé sur le disque | Moyenne |
| T5.5-03 | Résumé contenant des caractères Unicode étendus (accents, symboles) | Article en français avec accents | Rendu correct grâce à la police Unicode embarquée | Moyenne |
| T5.5-04 | Génération concurrente (deux exports simultanés du même document) | Deux requêtes PDF en parallèle | Deux fichiers temporaires distincts (nommage aléatoire via `NamedTemporaryFile`), pas de collision | Basse |

### Critères d'acceptation

- [x] Le PDF est généré (vérifié réellement, pas seulement en lecture de code).
- [x] Le résumé est lisible, mise en page sobre avec en-tête/pied de page.
- [x] Les sections sont structurées (titres, puces).
- [x] Les erreurs d'export sont gérées (404 explicite, nettoyage systématique des fichiers temporaires y compris en cas d'échec).

### Livrables
`export/pdf_generator.py`, route `GET /summary/{filename}/pdf`, bouton d'export (`ExportsPage`).

---

## 5.6 Historique des documents traités

### Objectif
Conserver et consulter l'historique des documents importés et de leurs exécutions de traitement.

### Ce qui est réellement conservé (au-delà de la liste demandée par le cahier des charges)

Le cahier des charges demande une liste relativement simple par document (nom, date, statut, méthode, pages, mots, résumé, exports). L'implémentation réelle va plus loin en modélisant explicitement la relation **un document → plusieurs exécutions de pipeline** (`PipelineRun`), chacune avec ses propres résultats détaillés par étape (extraction, prétraitement, inférence, résumé) — cf. Documentation Phase 2 §10 et Phase 4 §8 pour le détail des modèles. `HistoryPage` exploite cette richesse : sélection d'un document → liste de ses exécutions → détail complet d'une exécution (y compris le JSON persisté de chaque étape, via le composant générique `PersistedJson`, qui filtre les chemins de fichiers serveur avant affichage).

### Fonctionnement réel

1. Au montage, `GET /documents` charge la liste des documents.
2. Sélection d'un document → `GET /documents/{id}/pipeline-runs` charge ses exécutions.
3. Sélection d'une exécution → `GET /pipeline-runs/{id}` charge le détail complet (extraction, prétraitement, inférence, résumé).
4. Suppression : deux actions distinctes, chacune avec une modale de confirmation dédiée — supprimer une exécution seule (`DELETE /pipeline-runs/{id}`, conserve le document et le fichier PDF) ou supprimer un document entier (`DELETE /documents/{id}`, supprime aussi le fichier PDF et le dossier de sortie si aucun autre document ne partage le même nom de fichier — cf. §3 sur ce risque de partage).

### Un écart significatif : les documents non traités sont invisibles

`GET /documents` (`documents.py::list_documents`) est implémenté avec une **jointure interne** (`INNER JOIN`) entre `documents` et `pipeline_runs` :

```python
documents = (
    db.query(Document)
    .join(PipelineRun, PipelineRun.document_id == Document.id)
    .distinct()
    ...
)
```

Conséquence directe : un document **uploadé mais jamais soumis à `POST /summarize`** (upload seul, sans traitement lancé) n'apparaît **jamais** dans l'historique, alors même qu'il est bien persisté en base (`Document` existe dès l'upload, Documentation Phase 2 §7.1). Ce n'est pas nécessairement un défaut — on peut arguer qu'un document jamais traité n'a « rien à montrer » dans un historique de traitements — mais cela s'écarte du libellé du cahier des charges (« historique des **documents traités** » pourrait se lire comme incluant leur simple présence, avec un statut « non traité »).

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T5.6-01 | Liste des documents avec au moins une exécution | Base contenant 3 documents traités | Les 3 apparaissent, triés par date de création décroissante | Haute |
| T5.6-02 | Document uploadé sans traitement lancé | Upload seul, pas de `POST /summarize` | **Absent de la liste** (comportement actuel, cf. écart ci-dessus) | Haute — comportement à valider explicitement avec le porteur du cahier des charges |
| T5.6-03 | Consultation des exécutions d'un document | Document avec 2 exécutions (une échouée, une réussie) | Les deux apparaissent, badges de statut différenciés (`teal` si `completed`, `amber` sinon) | Haute |
| T5.6-04 | Suppression d'une exécution | Clic confirmé sur « Supprimer » (exécution) | Exécution retirée de la liste, document conservé, PDF conservé | Haute |
| T5.6-05 | Suppression d'un document | Clic confirmé sur « Supprimer » (document) | Document, toutes ses exécutions, PDF et dossier de sortie supprimés (sauf partage de nom de fichier, §3) | Haute |
| T5.6-06 | Annulation d'une suppression | Fermeture de la modale sans confirmer | Aucune suppression effectuée | Basse |

### Critères d'acceptation

- [x] Les traitements sont listés (pour les documents ayant au moins une exécution).
- [x] L'utilisateur peut consulter un ancien résumé (via le détail d'exécution, `selectedRun.summary`).
- [x] Les statuts sont visibles (par document et par exécution).
- [x] Les erreurs sont historisées (`failure_stage`, `error_message` affichés dans le détail d'exécution).
- [ ] *(Point à clarifier)* Un document uploadé mais jamais traité doit-il apparaître dans l'historique ? Non satisfait dans l'implémentation actuelle (`INNER JOIN`).

### Livrables
`HistoryPage`, `PersistedJson` (`App.jsx`) ; routes `documents.py`, `pipeline_runs.py` (list, detail, delete).

---

# 6. Dépendances entre les tâches

```text
5.1 Interface principale (coquille + import + suivi)
    │  (toutes les autres tâches s'affichent à l'intérieur de cette coquille)
    │
    ├──────────────► 5.2 Page résumé ──────────────► 5.4 Export Markdown
    │                     │                           5.5 Export PDF
    │                     │                           (Export JSON, non détaillé
    │                     │                            séparément par le cahier
    │                     │                            des charges mais présent)
    │                     │
    └──────────────► 5.3 "Texte extrait"
                          (actuellement alimentée par la même donnée que 5.2 —
                           dépendance de fait non voulue, cf. §5.3)

5.6 Historique — indépendante des tâches 5.2/5.3/5.4/5.5 dans son fonctionnement
    (consomme la route document_id-based, §3), mais dépend de 5.1 pour la navigation.
```

- **Séquentielle** : 5.1 doit exister avant toute autre tâche (coquille commune).
- **Dépendance de fait non voulue** : 5.3 dépend aujourd'hui de la même donnée que 5.2 au lieu de dépendre de la Phase 3 — c'est le point à corriger en priorité (§5.3).
- **Indépendante** : 5.6 peut être développée, testée et livrée sans dépendre de 5.2/5.3/5.4/5.5, puisqu'elle utilise un chemin de données entièrement séparé (§3).

---

# 7. Contrats de données consommés par le frontend

### `SummaryDetailResponse` (route filename-based)

```json
{
  "filename": "article.pdf",
  "metadata": { "...": "cf. Documentation Phase 3, §7.3" },
  "keywords": [{ "keyword": "...", "score": 0.9, "method": "tfidf" }],
  "summary": "# Résumé scientifique\n\n## Métadonnées\n...",
  "status": "completed",
  "generated_at": "2026-08-26T10:00:25Z",
  "downloads": {
    "markdown": "/summary/article.pdf/markdown",
    "json": "/summary/article.pdf/json",
    "pdf": "/summary/article.pdf/pdf"
  }
}
```

*(Absent de ce contrat : le JSON structuré par section — `summary_structured`, produit par la Phase 4 — et tout score de qualité, puisque le module de contrôle qualité n'est pas branché, Documentation Phase 4 §6.5.)*

### `DocumentListItemResponse` / `PipelineRunListItemResponse` / `PipelineRunDetailResponse` (route document_id-based)

Voir Documentation Phase 2 (§10) et Phase 4 (§8) pour le détail complet des modèles persistés dont ces réponses sont dérivées. `PipelineRunDetailResponse` est notable : c'est la **seule** route qui expose déjà `preprocessing.sections`, `preprocessing.missing_sections` et le texte nettoyé indirectement via `cleaning_report` — les données que la Tâche 5.3 devrait afficher (§5.3).

---

# 8. Gestion des erreurs et des états

| Situation | Comportement actuel |
|---|---|
| Erreur réseau/HTTP sur n'importe quel appel API | `apiRequest` (`api.js`) lève une `Error` avec le message `detail`/`message` renvoyé par le backend, ou un message générique `"Erreur HTTP {code}"` |
| Échec d'upload d'un fichier parmi plusieurs | Le fichier en échec est retiré de la liste, les autres continuent d'être traités, message d'erreur agrégé affiché | 
| Échec de `POST /summarize` | Message affiché sur l'écran de suivi, aucune navigation automatique vers le résumé |
| Absence de résultat pour un écran donné (`summaryDetail` null) | Messages de repli explicites (« Aucun résultat disponible. Lancez d'abord le traitement d'un document. ») plutôt qu'un écran vide ou une erreur JavaScript |
| Échec de chargement de l'historique | Bandeau d'erreur dédié (`error` state de `HistoryPage`), chargement des documents/exécutions/détail gérés indépendamment (`loadingDocuments`, `loadingRuns`, `loadingRun`) |
| Suppression échouée (document ou exécution) | Message d'erreur affiché dans la modale, la modale reste ouverte (pas de fermeture automatique sur échec) |

**Constat global** : la gestion des erreurs côté frontend est cohérente et couvre correctement les cas d'échec réseau/API. Les écarts identifiés dans ce document (§3, §5.1, §5.3, §5.6) ne sont pas des bugs de gestion d'erreur, mais des écarts entre la donnée affichée et la donnée attendue par le cahier des charges.

---

# 9. Plan de tests de la phase

| ID | Tâches couvertes | Scénario | Résultat attendu | Priorité |
|---|---|---|---|---|
| G5-01 | 5.1 → 5.5 | Parcours complet : import → traitement → résumé → export Markdown/PDF | Chaque étape aboutit, fichiers téléchargés valides | Haute |
| G5-02 | 5.6 | Parcours complet historique : liste → exécutions → détail → suppression | Cohérence entre les données affichées à chaque niveau | Haute |
| G5-03 | 5.3 | Comparaison texte affiché vs texte réellement extrait (Phase 2) | **Actuellement en échec** (contenu identique au résumé, pas au texte source) | Haute — reproductible immédiatement |
| G5-04 | 5.1 | Upload d'un document, puis consultation de l'historique sans avoir lancé de traitement | Document absent de l'historique (cf. §5.6, comportement actuel) | Moyenne — à confirmer comme comportement voulu ou non |
| G5-05 | 5.2, 5.4, 5.5 | Cohérence entre le résumé affiché à l'écran et les 3 exports (Markdown, JSON, PDF) | Contenu identique dans les 4 représentations | Haute |
| G5-06 | Toutes | Utilisation sur mobile (largeur réduite) | Menu latéral escamotable fonctionnel (`mobileOpen`), pas de rupture de mise en page | Basse |

---

# 10. Sécurité et confidentialité

| Risque | Impact | Protection actuelle |
|---|---|---|
| Absence d'authentification | Toute personne ayant accès à l'URL du frontend peut importer, consulter et supprimer n'importe quel document de n'importe quel autre utilisateur | **Non traité** — aucune notion de compte ou de session dans le code actuel ; cohérent avec un MVP mono-utilisateur, mais bloquant avant toute mise à disposition multi-utilisateurs réelle |
| Collision de nom de fichier entre documents (§3) | Un utilisateur pourrait, en théorie, accéder au résumé d'un document d'un autre utilisateur simplement en devinant/réutilisant le même nom de fichier, via la route filename-based | Non protégé — dépend entièrement de l'absence d'authentification plus généralement |
| Suppression sans confirmation forte | Perte de données accidentelle | Mitigé par les modales de confirmation dédiées (§5.6), mais aucune sauvegarde/corbeille |
| Affichage de données brutes persistées (`PersistedJson`, historique) | Fuite de chemins de fichiers serveur internes | Filtré explicitement (`safePersistedValue` retire les clés contenant `path`, `file_path`, `input pdf`, `output markdown`) |
| Contenu Markdown du résumé rendu tel quel (`ReactMarkdown`) | Risque d'injection si le Markdown contenait du HTML actif | `react-markdown` désactive le rendu HTML brut par défaut (comportement standard de la bibliothèque, non reconfiguré dans le code du projet) — protection par défaut de la dépendance, pas une mesure explicite du projet |

---

# 11. Performance et limites

- **Aucune pagination** sur `GET /documents` ni sur `GET /documents/{id}/pipeline-runs` : l'historique charge l'intégralité des enregistrements en une seule requête. Acceptable pour le volume du dataset de test (Documentation Phase 2, Tâche 2.5), mais à surveiller si le nombre de documents/exécutions grandit significativement.
- **Uploads séquentiels** (§5.1) : l'import de N fichiers prend un temps proportionnel à N appels réseau successifs, sans parallélisation.
- **Aucune virtualisation de liste** : les tableaux (historique) rendent l'intégralité des lignes dans le DOM, sans limite ; non problématique au volume actuel.
- **Régénération du PDF à chaque export** (§5.5) : coût CPU/E-S à chaque téléchargement (relecture disque + mise en page ReportLab), plutôt qu'un PDF généré une fois et mis en cache — acceptable au volume actuel, à revoir si les exports PDF deviennent fréquents sur de gros documents.

---

# 12. MVP et évolutions futures

## 12.1 MVP (état actuel)

- Parcours complet import → traitement → résumé → mots-clés → export, fonctionnel de bout en bout (vérifié réellement en session de développement).
- Historique des documents traités avec détail par exécution et suppression, à deux granularités (exécution, document).
- Trois formats d'export fonctionnels (Markdown, JSON, PDF).

## 12.2 Évolutions futures

- **Priorité haute** : reconnecter l'écran « Texte extrait » (5.3) aux données réelles de la Phase 3 (via `GET /pipeline-runs/{id}` ou une route dédiée filename-based), au lieu du résumé final.
- Unifier les deux sources de vérité (§3) — a minima, faire porter `GET /summary/{filename}` par `document_id` pour éliminer le risque de collision de nom de fichier.
- Remplacer la barre de progression à 3 paliers (§5.1) par un suivi réel de l'avancement du pipeline (WebSocket, SSE, ou endpoint de statut interrogé par polling).
- Décider explicitement si un document non traité doit apparaître dans l'historique (§5.6) et ajuster `list_documents` en conséquence.
- Exposer `summary_structured` (JSON par section, Phase 4) dans `SummaryDetailResponse` pour éviter le reparsing côté client (§5.2).
- Authentification et cloisonnement des documents par utilisateur, avant toute mise à disposition au-delà d'un usage interne/démo.

---

# 13. Décisions techniques actées

| Décision | Choix retenu | Justification |
|---|---|---|
| Pas de routeur d'URL (React Router ou équivalent) | Navigation par état interne (`useState`) | Simplicité pour un MVP à un seul utilisateur actif à la fois, sans besoin de partage de lien profond |
| Deux identifiants coexistants (filename, document_id) | Conservés tels quels plutôt qu'unifiés au moment de l'ajout de la persistance DB | Éviter de retoucher les routes d'export déjà fonctionnelles (Markdown/JSON/PDF) lors de l'ajout de la persistance ; dette technique assumée (implicitement) plutôt que décidée explicitement — voir §14 |
| PDF régénéré à chaque export plutôt que mis en cache | `generate_summary_pdf` appelé à chaque requête | Simplicité, fraîcheur garantie (toujours basé sur le dernier `summary.json`/`summary.md` écrit sur disque) |
| Suppression à deux granularités (exécution / document) | Deux actions et deux modales distinctes | Permet de nettoyer l'historique d'essais ratés sans perdre le document lui-même |

---

# 14. Points ouverts et zones grises

### Zone grise — Écran « Texte extrait » affichant en réalité le résumé
**Constat :** détaillé en §5.3 — le composant `ExtractionPage` est câblé sur la même donnée que `SummaryPage`.
**Recommandation :** priorité haute, correction directe possible via `GET /pipeline-runs/{id}` déjà existante.

### Zone grise — Coexistence non arbitrée de deux sources de vérité
**Constat :** détaillé en §3 — aucune trace dans le code d'une décision explicite de maintenir les deux chemins plutôt que de les unifier.
**Recommandation :** documenter le choix comme dette assumée si le temps manque pour l'unifier, plutôt que de laisser la question implicite.

### Zone grise — Documents non traités absents de l'historique
**Constat :** détaillé en §5.6 — comportement de `list_documents` (jointure interne), potentiellement non intentionnel au vu du libellé du cahier des charges.
**Interprétations possibles :** (a) volontaire, un document non traité n'a rien à montrer dans un historique de traitements ; (b) oubli, l'intention étant de lister tous les documents avec un statut « non traité » pour ceux sans exécution.
**Recommandation :** trancher explicitement avec le porteur du cahier des charges plutôt que de laisser le comportement actuel faire foi par défaut.

### Zone grise — Absence de suivi de progression réel
**Constat :** détaillé en §5.1 — la barre de progression à 8 étapes visuelles ne reflète que 3 paliers réels.
**Recommandation :** acceptable pour un MVP de démonstration ; à corriger si la latence perçue par l'utilisateur devient un sujet (documents longs, Documentation Phase 4 §12).

---

# 15. Livrables de la phase

- Application frontend : `frontend/src/App.jsx`, `api.js`, `data.js`, styles associés.
- Routes backend consommées (déjà livrées en Phases 2/4, réutilisées ici) : `summary.py`, `documents.py`, `pipeline_runs.py`.
- Fonctionnalité d'export PDF : `export/pdf_generator.py`.
- Documentation : le présent document.

---

# 16. Definition of Done globale

```text
☐ Parcours complet import → traitement → résumé → export fonctionnel
☐ Export Markdown, JSON et PDF tous fonctionnels et vérifiés
☐ Historique des documents traités et de leurs exécutions consultable
☐ Suppression (exécution et document) fonctionnelle avec confirmation
☐ Écran "Texte extrait" reconnecté aux données réelles de la Phase 3 (non fait à ce jour)
☐ Décision actée sur la visibilité des documents non traités dans l'historique
☐ Décision actée sur l'unification (ou le maintien documenté) des deux sources de vérité
☐ Documentation technique à jour (ce document)
```

---

# 17. Matrice de traçabilité

| Exigence (cahier des charges) | Tâche | Composant / Route | Test | Statut |
|---|---|---|---|---|
| Upload PDF depuis l'interface | 5.1 | `UploadPage`, `POST /upload` | T5.1-01 | Fait |
| Lancement du traitement | 5.1 | `startProcessing`, `POST /summarize` | T5.1-04 | Fait |
| Affichage des résultats | 5.1, 5.2 | `SummaryPage` | T5.2-01 | Fait |
| Messages d'état/erreurs visibles | 5.1 | `apiRequest`, bandeaux d'alerte | T5.1-04 | Fait |
| Affichage métadonnées, résumé, sections, mots-clés | 5.2 | `SummaryPage` | T5.2-01 | Fait |
| Boutons export accessibles depuis le résumé | 5.2 | `SummaryPage` → `exports` | T5.2-01 | Fait |
| Affichage texte brut | 5.3 | `ExtractionPage` | T5.3-03 | **Non satisfait** |
| Affichage texte nettoyé | 5.3 | `ExtractionPage` | T5.3-03 | **Non satisfait** |
| Affichage par section (sections réelles) | 5.3 | `ExtractionPage` | T5.3-04 | **Non satisfait** |
| Recherche dans le texte | 5.3 | `ExtractionPage` | T5.3-01 | Fait (sur la mauvaise donnée) |
| Export Markdown | 5.4 | `ExportsPage`, `GET /summary/{filename}/markdown` | T5.4-01 | Fait |
| Export PDF | 5.5 | `ExportsPage`, `GET /summary/{filename}/pdf` | T5.5-01 | Fait, vérifié réellement |
| Historique des traitements | 5.6 | `HistoryPage`, `GET /documents` | T5.6-01 | Fait (documents traités uniquement) |
| Consultation d'un ancien résumé | 5.6 | `HistoryPage`, `GET /pipeline-runs/{id}` | T5.6-03 | Fait |
| Suppression éventuelle | 5.6 | `DELETE /documents/{id}`, `DELETE /pipeline-runs/{id}` | T5.6-04, T5.6-05 | Fait |

---

*Fin du document — Phase 5. Cette collection de cinq documents (Phases 2 à 5) constitue la documentation technique complète du MVP Yonnov'IA, chacun structuré selon la nature propre de sa phase plutôt que selon un gabarit unique reconduit mécaniquement.*
