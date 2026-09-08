> **Note de mise en forme (conversion `.docx`)**
> Titres (`#`/`##`/`###`) → bleu Yonnov'IA `#2596BE`, police serif grasse (ex. Georgia Bold), conforme au rendu de la charte. Corps de texte, tableaux, code → noir uniquement. Logo Yonnov'IA (`frontend/public/logo.jpg`) en en-tête Word sur **chaque page**, pas seulement la page de garde. Voir la note complète en tête du document Phase 2 pour la procédure d'application (styles Word / gabarit Pandoc).
>
> **Ce document adopte volontairement un sommaire différent de celui de la Phase 2.** La Phase 2 est une phase d'infrastructure (API, stockage, base de données) ; la Phase 3 est une phase de traitement algorithmique du texte (règles, heuristiques, TF-IDF, chunking). La structure ci-dessous a été adaptée en conséquence plutôt que reconduite à l'identique.

---

# PAGE DE GARDE

![Logo Yonnov'IA](../frontend/public/logo.jpg)

# Yonnov'IA
## Documentation technique

# Phase 3 — Nettoyage, segmentation et extraction d'informations
## Sprint 3 — Préparation NLP du texte scientifique

**Durée estimée :** Semaines 3 et 4
**Version du document :** 1.0
**Date :** 26/08/2026
**Auteur :** Équipe Yonnov'IA — Team07-E26

---

# SOMMAIRE

*(champ TOC à régénérer automatiquement lors de la conversion Word)*

1. Vue d'ensemble de la phase
2. Position dans la chaîne de traitement
3. Panorama des modules
4. Choix méthodologiques
5. Flux de données : du texte brut au texte prêt pour l'IA
6. L'enjeu bilingue français/anglais
7. Documentation détaillée des tâches
   7.1 Nettoyage du texte extrait
   7.2 Détection des sections scientifiques
   7.3 Extraction des métadonnées
   7.4 Extraction des mots-clés
   7.5 Préparation du texte pour le LLM
8. Dépendances entre les tâches
9. Modèles de données produits
10. Gestion des erreurs et dégradations
11. Plan de tests de la phase
12. Sécurité et confidentialité
13. Performance, limites et échelle
14. MVP et évolutions futures
15. Décisions techniques actées
16. Points ouverts et zones grises
17. Livrables de la phase
18. Definition of Done globale
19. Matrice de traçabilité

---

# 1. Vue d'ensemble de la phase

## 1.1 Objectif

La Phase 3 transforme le texte brut produit par la Phase 2 (extraction PDF) en données structurées, propres et calibrées, exploitables par un LLM, sans jamais produire elle-même de résumé : son rôle se limite à préparer le terrain pour la Phase 4.

## 1.2 Pourquoi cette phase est nécessaire

Le texte issu de l'extraction PDF (Phase 2) est brut : numéros de page mêlés au contenu, en-têtes répétés, césures de fin de ligne, absence de structure explicite (le PDF ne sait pas ce qu'est un « Abstract »), aucune métadonnée fiable, aucun découpage adapté à la fenêtre de contexte d'un LLM. Sans cette phase, la Phase 4 recevrait un flux de texte indifférencié, sans priorisation, avec un risque élevé de dépassement de contexte et de dilution du contenu utile par les références bibliographiques.

## 1.3 Nature des traitements

Contrairement à la Phase 2, essentiellement construite autour de flux binaires et d'appels d'entrées-sorties, la Phase 3 est une phase **algorithmique sur du texte** : elle repose sur des expressions régulières, des règles heuristiques, du TF-IDF (`scikit-learn`) et, en dernier recours seulement, sur la reconnaissance d'entités nommées (`spaCy`). Aucun appel réseau ni aucune inférence LLM n'intervient à ce stade, puisque le modèle de langage n'entre en jeu qu'en Phase 4.

## 1.4 Résultat attendu en sortie de phase

- Texte nettoyé (numéros de page et bruit OCR retirés, césures fusionnées).
- Sections scientifiques identifiées (`Abstract`, `Introduction`, `Methodology`, `Results`, …) avec le contenu associé, et la liste des sections manquantes.
- Métadonnées bibliographiques structurées (titre, auteurs, année, source, DOI, langue), avec traçabilité de la méthode d'extraction par champ.
- Mots-clés globaux et par section, avec score de pertinence.
- Une liste de « chunks » (sections découpées et priorisées), assortis d'un prompt pré-construit par chunk, prêts à être envoyés au moteur d'inférence de la Phase 4.

## 1.5 Périmètre

**Inclus** : nettoyage du texte, détection de sections, extraction de métadonnées, extraction de mots-clés, découpage en chunks avec priorisation, construction des prompts partagés/par chunk.

**Non inclus** : génération de résumé par LLM (Phase 4), interface de consultation du texte/des sections (Phase 5, Tâche 5.3), OCR (Phase 2, Tâche 2.4 — le texte reçu ici est supposé déjà extrait, quelle que soit sa qualité).

**Hors périmètre par construction (à noter)** : la Phase 3 n'a aucun moyen de compenser un texte déjà vide en entrée. Si la Tâche 2.4 (OCR) n'a pas produit de texte (cf. Documentation Phase 2, §17), la Phase 3 s'exécute sur une chaîne vide et produit des artefacts vides ou des sections par défaut (`"Full Text"` vide, métadonnées quasi entièrement `None`) — ce n'est pas un bug de la Phase 3, mais une conséquence directe d'un défaut amont.

---

# 2. Position dans la chaîne de traitement

```text
Phase 2 (Extraction)
   texte brut par page
        │
        ▼
┌───────────────────────────────────────────┐
│              PHASE 3                        │
│                                               │
│  3.1 Nettoyage du texte                      │
│        │                                     │
│        ▼                                     │
│  3.2 Détection des sections ──────┐          │
│        │                          │          │
│        ▼                          ▼          │
│  3.3 Métadonnées           3.4 Mots-clés      │
│        │                          │          │
│        └────────────┬─────────────┘          │
│                      ▼                        │
│           3.5 Chunking + prompts               │
└───────────────────────────────────────────┘
        │
        ▼
Phase 4 (Résumé LLM) — reçoit inference_requests[]
```

**Entrées** : texte brut concaténé (`extracted_markdown`), issu de `extract_pdf_content` (Phase 2).

**Sorties consommées par la Phase 4** : `inference_requests` (liste de prompts par chunk), `metadata`, `keywords` (réutilisés pour construire le contexte partagé des prompts).

**Sorties consommées par la Phase 5** : `sections`, `missing_sections`, `keywords`, `article_metadata` — pour l'affichage du texte extrait et des mots-clés (Tâches 5.2, 5.3).

**Remarque d'implémentation** : dans le code actuel, ces sous-étapes ne sont pas appelées via une fonction d'orchestration unique de la Phase 3. `app/services/preprocessing/pipeline.py` définit bien une fonction `preprocess_document()` qui enchaîne nettoyage → sections → métadonnées → mots-clés → chunking, mais **l'orchestrateur réellement exécuté** (`app/services/pipeline/document_pipeline.py`) rappelle chacune de ces fonctions individuellement, dans le même ordre, sans passer par `preprocess_document()`. Les deux chemins sont fonctionnellement équivalents mais constituent une duplication de logique d'orchestration — voir section 16.

---

# 3. Panorama des modules

La Phase 3 ne crée pas de nouvelle infrastructure (pas de nouvel endpoint HTTP, pas de nouvelle table dédiée — ses résultats sont persistés dans `PreprocessingResult`, déjà modélisée). Elle ajoute des modules de traitement purs, sans état, dans `app/services/preprocessing/` et `app/services/prompting/`.

| Module | Rôle | Entrée principale | Sortie principale |
|---|---|---|---|
| `preprocessing/cleaning.py` | Nettoyage ligne par ligne du texte extrait | Texte brut | Texte nettoyé + rapport de nettoyage |
| `preprocessing/sections.py` | Détection des sections scientifiques canoniques | Lignes nettoyées, taguées par page | Liste de sections + sections manquantes |
| `preprocessing/metadata.py` | Extraction bibliographique (titre, auteurs, année, source, DOI, langue) | Texte nettoyé + chemin PDF | Dictionnaire de métadonnées structuré |
| `preprocessing/keywords.py` | Extraction de mots-clés (TF-IDF + mots-clés fournis) | Texte nettoyé + langue détectée | Mots-clés globaux et par section |
| `preprocessing/chunking.py` | Découpage des sections en blocs de taille contrôlée | Sections priorisées | Liste de chunks (avec chevauchement) |
| `preprocessing/pipeline.py` | Orchestrateur alternatif + règles de priorisation/exclusion de sections | Sections détectées | Sections priorisées, sections filtrées |
| `prompting/builder.py` | Construction du préfixe de prompt partagé et du prompt par chunk | Métadonnées, mots-clés, chunk | Chaînes de prompt |
| `prompting/requests.py` | Assemblage des requêtes d'inférence (une par chunk, hors « Title ») | Chunks + préfixe partagé | Liste `inference_requests` |
| `prompting/templates.py` | Contient le `SYSTEM_PROMPT` partagé | — | Constante texte |

**Aucune dépendance externe lourde** en dehors de `scikit-learn` (TF-IDF) et, en secours optionnel, `spaCy` (`fr_core_news_sm`, `en_core_web_sm`) pour la reconnaissance d'auteurs par NER.

---

# 4. Choix méthodologiques

Contrairement à la Phase 2 (choix d'outils d'infrastructure), les décisions structurantes de la Phase 3 sont **méthodologiques** : quelle heuristique appliquer, avec quel niveau de rigueur, pour compenser l'absence d'une bibliothèque NLP scientifique lourde (type GROBID) au MVP.

| Choix | Décision retenue dans le code | Alternative structurante | Compromis assumé |
|---|---|---|---|
| Détection de sections | Dictionnaire de motifs regex par nom canonique (`SECTION_KEYWORDS`), anglais + français | GROBID / modèle de layout entraîné (type LayoutLM) | Rapide et sans dépendance lourde, mais fragile aux formats non standards (titres stylisés en image, PDF très design) |
| Extraction de mots-clés | TF-IDF (`scikit-learn`) + mots-clés fournis par l'auteur si trouvés dans le texte | RAKE, KeyBERT (embeddings) | Résultat explicable et déterministe, sans modèle supplémentaire à charger ; moins performant sur des formulations peu fréquentes en corpus mais sémantiquement fortes |
| Extraction d'auteurs | Priorité : métadonnées PDF → règle positionnelle (juste après le titre) → NER spaCy en dernier recours | NER systématique dès le départ | Les métadonnées PDF et la position sont plus fiables quand disponibles ; spaCy n'est sollicité (coût, dépendance modèle) que si les deux premières méthodes échouent |
| Nettoyage du texte | Règles déterministes (regex) : numéros de page, bruit OCR par ratio alphanumérique, fusion de césures | Modèle de correction de texte (LLM léger) | Aucune latence ni coût d'inférence ; ne corrige pas les erreurs sémantiques profondes (mots mal reconnus par l'OCR en amont, par exemple) |
| Détection de la langue | Comptage de mots-outils fréquents FR vs EN sur un échantillon de 10 000 caractères | Bibliothèque dédiée (`langdetect`, `fasttext`) | Suffisant pour un corpus binaire FR/EN scientifique ; ne généralise pas à d'autres langues |
| Chunking | Découpage par mots avec taille et chevauchement fixes (2000 tokens ≈ 1500 mots, 200 tokens ≈ 150 mots de recouvrement) | Découpage sémantique (par phrase/paragraphe avec un modèle d'embedding) | Simple et prévisible, mais peut couper une phrase en plein milieu ; le recouvrement atténue partiellement ce risque |

---

# 5. Flux de données : du texte brut au texte prêt pour l'IA

```text
extracted_markdown (str, Phase 2)
 │
 ▼
[3.1] clean_extracted_text(min_repeat_ratio=0.6)
   - normalisation Unicode (NFKC) + espaces
   - suppression des lignes "numéro de page" (regex)
   - suppression des lignes de bruit OCR (ratio alphanumérique < 0.35)
   - fusion des césures de fin de ligne
 │
 ├──▶ cleaned_text (str)
 └──▶ page_tagged_lines (liste de (n° page, ligne))
 │
 ▼
[3.2] detect_sections(page_tagged_lines)
   - repérage des titres canoniques (Abstract, Introduction, ...)
   - découpage du texte entre deux titres consécutifs
 │
 ├──▶ sections[] (section_name, content, metadata.page_start/end)
 └──▶ missing_sections[]
 │
 ├──────────────┬───────────────────────┐
 ▼              ▼                       │
[3.3] extract_article_metadata   [3.4] extract_article_keywords
   - titre, auteurs, année,          - mots-clés fournis (regex)
     source, DOI, langue,            - TF-IDF global (1-3 grammes)
     nombre de pages                 - TF-IDF par section
 │                                    - filtrage termes génériques
 ▼                                    - déduplication (sous-ensembles)
 metadata{}                        │
                                     ▼
                                  keywords{}
 │                                    │
 └──────────────┬─────────────────────┘
                ▼
[3.5a] select_relevant_sections() + remove_excluded_sections()
   - priorité core / optional / excluded / unknown
   - retrait des sections "excluded" (références, annexes, ...)
 │
 ▼
[3.5b] chunk_document()
   - découpage par section en blocs de ≤ 1500 mots, chevauchement 150 mots
 │
 ▼
[3.5c] build_shared_prefix(metadata, keywords) + build_inference_requests(chunks)
   - préfixe partagé (system prompt + titre/langue/mots-clés)
   - un prompt par chunk (hors chunk "Title")
 │
 ▼
inference_requests[] ──────────────────▶ Phase 4
```

---

# 6. L'enjeu bilingue français/anglais

Le cahier des charges impose explicitement la prise en charge d'articles en français et en anglais. Cette contrainte traverse presque tous les modules de la Phase 3 et mérite d'être traitée comme un sujet transversal plutôt que dispersée tâche par tâche :

- **Détection de sections** (`sections.py`) : chaque nom canonique dispose de motifs FR et EN (`Methodology` ↔ `méthodologie`/`méthode`, `Results` ↔ `résultats`, `Related Work` ↔ `travaux connexes`/`état de l'art`).
- **Extraction de mots-clés** (`keywords.py`) : deux listes de mots vides distinctes et volumineuses (`FRENCH_STOP_WORDS`, `ENGLISH_STOP_WORDS`), sélectionnées selon la langue détectée.
- **Extraction d'auteurs** (`metadata.py`) : le modèle spaCy chargé en secours dépend de la langue détectée (`fr_core_news_sm` vs `en_core_web_sm`) — **ces modèles ne sont pas installés par défaut** (ils s'installent via `python -m spacy download <modèle>`, absent de `requirements.txt`) ; si le modèle n'est pas présent, `extract_authors` échoue silencieusement à cette étape (`OSError` capturée, retour `[]`).
- **Détection de la langue** (`metadata.detect_language`) : limitée à un choix binaire FR/EN par comptage de mots-outils — un article dans une troisième langue serait arbitrairement classé FR ou EN selon le score le plus élevé, sans détection d'anomalie.

**Point de vigilance** : la couverture FR/EN est réelle mais repose sur des listes closes (motifs regex, stop-words). Un titre de section formulé de façon inhabituelle (« Nos contributions » au lieu de « Contributions », par exemple) ne sera pas reconnu.

---

# 7. Documentation détaillée des tâches

## 7.1 Nettoyage du texte extrait

### Objectif
Réduire le bruit du texte brut extrait (Phase 2) sans en altérer le contenu scientifique, pour fiabiliser toutes les étapes suivantes (détection de sections, métadonnées, mots-clés).

### Traitements réellement appliqués

| Traitement | Mécanisme | Fonction |
|---|---|---|
| Normalisation Unicode et espaces | `unicodedata.normalize("NFKC", ...)`, compression des espaces/tabulations | `normalize_line` |
| Suppression des numéros de page | Regex `page_number_pattern` (ex. `"12"`, `"page 12"`, `"12/40"`, `"- 12 -"`) | `clean_extracted_text` |
| Suppression du bruit OCR | Ligne rejetée si ratio de caractères alphanumériques < 0,35 (et longueur ≥ 4) | `is_ocr_noise` |
| Fusion des césures de fin de ligne | Ligne se terminant par un mot suivi de `-`, suivie d'une ligne commençant par un mot → fusion | `merge_hyphenation` |

### Traitement prévu mais non branché

Le cahier des charges demande explicitement la **suppression des en-têtes et pieds de page répétitifs**. La fonction `detect_repeated_lines(page_lines, min_repeat_ratio)` existe dans `cleaning.py` et implémente cette logique (compte les 3 premières et 3 dernières lignes de chaque page, retient celles apparaissant sur au moins `min_repeat_ratio` des pages) — **mais elle n'est appelée nulle part dans `clean_extracted_text`**. Le champ `report["headers_footers_removed"]` reste donc toujours une liste vide en sortie. Voir section 16.

### Algorithme (fonctionnement réel)

```text
FONCTION clean_extracted_text(pages_text, min_repeat_ratio=0.6):
    pages ← [pages_text] si chaîne unique, sinon pages_text tel quel
    POUR CHAQUE page (indexée à partir de 1):
        POUR CHAQUE ligne DE la page:
            ligne ← normalize_line(ligne)
            SI ligne vide: passer
            SI ligne correspond à un numéro de page: compter, passer
            SI ligne est du bruit OCR: compter, passer
            conserver la ligne, avec son numéro de page associé
        fusionner les césures de fin de ligne sur les lignes conservées
    texte_nettoyé ← jointure des pages nettoyées ("\n\n")
    rapport ← { chars_before, chars_after, reduction_ratio,
                page_numbers_removed, ocr_noise_removed,
                hyphenation_fixes, headers_footers_removed: [] }
    RETOURNER (texte_nettoyé, lignes_taguées_par_page, rapport)
```

### Structures de données

```json
{
  "chars_before": 34521,
  "chars_after": 31890,
  "reduction_ratio": 0.0762,
  "headers_footers_removed": [],
  "page_numbers_removed": 12,
  "ocr_noise_removed": 4,
  "hyphenation_fixes": 7
}
```

### Limites linguistiques

Le seuil de bruit OCR (ratio alphanumérique < 0,35) et le motif de numéro de page sont indépendants de la langue — aucun ajustement FR/EN nécessaire à ce niveau.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T3.1-01 | Numéro de page isolé | Ligne `"12"` sur sa propre ligne | Ligne supprimée, `page_numbers_removed` incrémenté | Haute |
| T3.1-02 | Césure de fin de ligne | `"pipe-"` suivi de `"line performance"` | Fusion en `"pipeline performance"` | Haute |
| T3.1-03 | Ligne de bruit OCR | Ligne du type `"§ ¤ ¤ § ~ ¤"` | Ligne supprimée, `ocr_noise_removed` incrémenté | Moyenne |
| T3.1-04 | En-tête répété sur toutes les pages | `"Yonnov'IA — Internal Draft"` en tête de chaque page | **Actuellement non supprimé** (fonction non branchée) | Haute |
| T3.1-05 | Texte déjà propre | Article sans numéro de page ni bruit | `reduction_ratio` proche de 0, aucun texte perdu | Moyenne |

### Critères d'acceptation

- [x] Les numéros de page isolés sont supprimés.
- [x] Les césures de fin de ligne sont fusionnées.
- [x] Le bruit OCR grossier est filtré.
- [ ] *(Non satisfait)* Les en-têtes/pieds de page répétitifs sont supprimés — fonction existante non intégrée.
- [x] Le pipeline ne s'interrompt jamais sur un texte vide ou déjà propre (fonction pure, sans exception attendue en usage normal).

### Livrables
`preprocessing/cleaning.py` (`clean_extracted_text`, `detect_repeated_lines`, `is_ocr_noise`, `merge_hyphenation`, `normalize_line`) ; rapport de nettoyage persisté via `cleaning_report` dans `PreprocessingResult`.

### Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| En-têtes/pieds de page non supprimés | Pollution du texte transmis aux sections et aux mots-clés (répétition artificielle de termes) | Élevée (fonction non branchée) | Brancher `detect_repeated_lines` dans `clean_extracted_text` |
| Seuil de bruit OCR fixe (0,35) non calibré sur le dataset réel | Faux positifs (texte scientifique légitime avec formules/symboles supprimé) ou faux négatifs | Moyenne | Calibrer sur le dataset de test (Phase 2, Tâche 2.5), notamment sur les PDF avec tableaux/formules |

### Definition of Done
```text
☐ Suppression numéros de page fonctionnelle
☐ Fusion des césures fonctionnelle
☐ Filtrage du bruit OCR fonctionnel
☐ Suppression des en-têtes/pieds de page répétitifs branchée (non fait à ce jour)
☐ Rapport avant/après généré et persisté
☐ Tests sur au moins 3 PDF du dataset (Tâche 2.5)
```

---

## 7.2 Détection des sections scientifiques

### Objectif
Segmenter le texte nettoyé en sections scientifiques canoniques (Abstract, Introduction, Methodology, Results, …) pour permettre une priorisation et un résumé structurés en Phase 4.

### Stratégie de détection

`detect_sections` (dans `sections.py`) repère, ligne par ligne, un titre candidat (après retrait des marqueurs Markdown, de la numérotation type `"3.2"` et des emphases `*`/`_`), puis le compare à un dictionnaire `SECTION_KEYWORDS` de 14 noms canoniques, chacun associé à un ou plusieurs motifs regex FR/EN. Un garde-fou (`is_valid_section_heading`) rejette les faux positifs évidents (phrases longues, ponctuation finale, présence de connecteurs de phrase comme *"however"*, *"cependant"*) sauf si le mot suspect appartient au nom canonique lui-même.

Le contenu de chaque section correspond à toutes les lignes situées entre son titre et le titre suivant détecté. Les sections `Appendix`, `Supplementary Material`, `Prompts`, `Additional Results` et `References` sont détectées (pour calculer les sections manquantes) mais **exclues du résultat retourné** — elles ne font jamais partie du texte transmis en aval par cette fonction.

### Sections canoniques couvertes

`Abstract`, `Introduction`, `Related Work`, `Methodology`, `Experiments`, `Results`, `Discussion`, `Conclusion`, `Limitations`, `Future Work`, `Appendix`*, `Supplementary Material`*, `Prompts`*, `Additional Results`*, `References`* (*exclues du résultat final).

### Cas de repli

- **Aucun titre détecté avant la première section reconnue** → ce contenu est conservé comme section `"Title"` (le futur objet de la Tâche 3.3 s'appuiera partiellement sur ce contenu).
- **Aucune section reconnue du tout** → repli sur une unique section `"Full Text"` contenant l'intégralité du texte, et `missing_sections` = la liste complète des 11 noms canoniques (hors exclus).

### Une duplication de logique à connaître

Le module `keywords.py` (Tâche 3.4) contient **sa propre fonction indépendante de segmentation**, `split_text_into_sections`, utilisée uniquement pour calculer les mots-clés par section. Elle repose sur une heuristique différente (détection de titres génériques par capitalisation/numérotation, sans liste `SECTION_KEYWORDS`) et peut donc segmenter le même document différemment de `detect_sections`. Les deux mécanismes ne partagent ni code ni résultat. Voir section 16.

### Structures de données

```json
[
  {
    "section_name": "Introduction",
    "content": "Deep learning has recently...",
    "metadata": { "page_start": 1, "page_end": 1 }
  }
]
```

*(Remarque : `page_start`/`page_end` sont actuellement toujours fixés à `1` — l'information de page réelle n'est pas propagée jusqu'à la structure de sortie, bien que `page_tagged_lines` la contienne en entrée. Voir section 16.)*

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T3.2-01 | Article structuré standard EN | Sections numérotées `1 Introduction`, `2 Methodology`, ... | Toutes les sections principales détectées | Haute |
| T3.2-02 | Article structuré en français | `Résumé`, `Méthodologie`, `Résultats` | Sections détectées sous leur nom canonique anglais | Haute |
| T3.2-03 | Article sans structure reconnaissable | Texte continu sans titres | Repli sur section unique `"Full Text"` | Haute |
| T3.2-04 | Références en fin de document | Section `References` présente | Exclue du résultat, absente du texte transmis | Haute |
| T3.2-05 | Titre ambigu ("Results and Discussion") | Titre combiné | Détecté comme un seul nom canonique (le premier motif qui correspond, ordre du dictionnaire) — comportement à vérifier explicitement | Moyenne |

### Critères d'acceptation

- [ ] Les sections standards sont détectées sur les PDF structurés du dataset de test (Phase 2, Tâche 2.5).
- [ ] Les sections non trouvées apparaissent dans `missing_sections`.
- [ ] Le pipeline continue même en l'absence totale de section reconnue (repli `"Full Text"`).
- [ ] Les références sont exclues du texte transmis aux étapes suivantes.
- [ ] *(Point ouvert)* La numérotation de page par section est fiable — non satisfait actuellement (valeurs figées à 1).

### Livrables
`preprocessing/sections.py` ; sortie persistée dans `PreprocessingResult.sections` / `.missing_sections`.

### Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Deux logiques de segmentation indépendantes (`sections.py` vs `keywords.py`) | Incohérence entre les sections affichées (Phase 5) et celles utilisées pour les mots-clés par section | Moyenne | Unifier sur une seule fonction de segmentation, ou documenter explicitement la différence d'usage |
| Titres stylisés non textuels (image, police non standard mal extraite) | Section non détectée, contenu versé dans la section précédente ou en repli `"Full Text"` | Moyenne | Documenté comme limite connue (cf. Phase 2 sur les limites de l'extraction elle-même) |

### Definition of Done
```text
☐ Détection fonctionnelle sur les 11 sections canoniques
☐ Sections manquantes correctement listées
☐ Références exclues du résultat
☐ Repli "Full Text" fonctionnel si aucune section reconnue
☐ Tests sur dataset FR et EN
☐ Décision actée sur l'unification (ou non) avec la logique de keywords.py
```

---

## 7.3 Extraction des métadonnées

### Objectif
Extraire les informations bibliographiques (titre, auteurs, année, source, DOI, langue, nombre de pages) sans jamais bloquer la suite du pipeline si un champ est absent.

### Stratégie par champ

| Champ | Méthode 1 (priorité) | Méthode 2 (repli) | Méthode 3 (dernier recours) |
|---|---|---|---|
| **Titre** | Métadonnées internes du PDF (`fitz`), si non génériques (rejette *"Microsoft Word"*, *"Untitled"*, etc.) | Première ligne pertinente du texte (15 à 300 caractères, hors mots exclus type *"abstract"*, *"keywords"*) | — |
| **Auteurs** | Métadonnées internes du PDF | Ligne(s) situthey immédiatement après le titre, avant toute mention *"@"*, *"university"*, *"abstract"* | Reconnaissance d'entités nommées `PERSON` via spaCy (modèle selon la langue détectée) |
| **Année** | Première année plausible (1900–année courante+1) trouvée dans les 8000 premiers caractères | Date de création du PDF (métadonnées internes) | — |
| **Source** (revue/conférence) | Motif *"copyright \<année\> ..."* | Motifs *"journal:"*, *"conference:"*, *"revue:"*, *"conférence:"* | Champ `subject` des métadonnées PDF |
| **DOI** | Regex `10.XXXX/...` sur l'ensemble du texte | — | — |
| **Langue** | Comptage de mots-outils FR vs EN sur 10 000 caractères | — | — |
| **Nombre de pages** | Métadonnées internes du PDF (`document.page_count`) | — | — |

### Gestion des champs absents

Chaque champ manquant est explicitement `None` (jamais de valeur inventée). Deux listes sont calculées : `missing_required_fields` (`title`, `authors`, `year`, `source`) et `missing_optional_fields` (`doi`, `page_count`). Un statut synthétique en découle : `"complete"`, `"completed_with_missing_optional_fields"`, ou `"completed_with_missing_fields"`. Le champ `can_continue_summarization` est **toujours `True`** dans l'implémentation actuelle — la Phase 4 n'est donc jamais bloquée par des métadonnées incomplètes, quelle que soit leur importance.

### Structures de données

```json
{
  "title": "Indecomposable tournaments...",
  "authors": ["Houmem Belkhechine"],
  "year": 2010,
  "source": null,
  "doi": null,
  "page_count": 12,
  "language": "en",
  "extraction_sources": {
    "title": "First relevant text line",
    "authors": "Document header",
    "year": "Text or PDF metadata",
    "source": null,
    "doi": null,
    "page_count": "PDF"
  },
  "missing_required_fields": ["source"],
  "missing_optional_fields": ["doi"],
  "can_continue_summarization": true,
  "status": "completed_with_missing_optional_fields"
}
```

*(Exemple réel observé en session de test sur le dataset du projet.)*

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T3.3-01 | PDF avec métadonnées internes complètes | Métadonnées PDF standard (Word/LaTeX export) | Titre et auteurs issus des métadonnées PDF | Haute |
| T3.3-02 | PDF sans métadonnées internes | Métadonnées PDF vides | Repli sur la première ligne pertinente pour le titre | Haute |
| T3.3-03 | Auteurs positionnés juste sous le titre | Bloc `Titre\nJohn Doe, Jane Smith\nUniversity of...` | Auteurs extraits par la règle positionnelle | Haute |
| T3.3-04 | Auteurs non positionnés, modèle spaCy absent | Modèle `en_core_web_sm` non installé | Liste d'auteurs vide, `authors_source: null`, pas d'exception | Haute |
| T3.3-05 | DOI présent dans le texte | `"https://doi.org/10.1000/xyz123"` | DOI extrait, ponctuation finale nettoyée | Moyenne |
| T3.3-06 | Article français | Texte majoritairement en français | `language: "fr"` | Haute |

### Critères d'acceptation

- [ ] Le titre est extrait ou raisonnablement approché dans au moins 90 % des cas du dataset de test.
- [ ] Les auteurs sont détectés si présents sous une forme standard (métadonnées ou position sous le titre).
- [ ] Aucun champ absent ne provoque d'exception ou de blocage du pipeline.
- [ ] La méthode d'extraction de chaque champ est traçable (`extraction_sources`).
- [ ] La langue est correctement détectée sur les articles FR et EN du dataset.

### Livrables
`preprocessing/metadata.py` ; persistance dans `PreprocessingResult.article_metadata`.

### Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Modèles spaCy non installés en environnement de déploiement | Extraction d'auteurs dégradée silencieusement à une liste vide pour tout document sans métadonnées PDF ni position standard | Élevée (dépendance absente de `requirements.txt`) | Ajouter `spacy` + les modèles `fr_core_news_sm`/`en_core_web_sm` à l'installation, ou documenter explicitement cette dégradation comme acceptable au MVP |
| Détection de langue binaire (FR/EN uniquement) | Un article dans une autre langue est mal classé sans avertissement | Faible (corpus scientifique du projet majoritairement FR/EN) | Documenté comme limite connue |
| Extraction de la source (revue/conférence) peu robuste (motifs regex étroits) | `source` fréquemment `null` en pratique | Élevée (confirmée en test réel : champ `source` absent sur l'exemple observé) | Champ optionnel dans les critères d'acceptation minimaux ; amélioration possible en Phase future |

### Definition of Done
```text
☐ Extraction fonctionnelle des 6 champs sur PDF avec métadonnées internes
☐ Repli textuel fonctionnel en l'absence de métadonnées internes
☐ Détection de langue FR/EN fonctionnelle
☐ Aucun champ manquant ne bloque le pipeline
☐ Traçabilité de la méthode par champ
☐ Dépendance spaCy actée (installée ou dégradation documentée)
```

---

## 7.4 Extraction des mots-clés

### Objectif
Produire une liste de mots-clés pertinents, globale et par section, en combinant les mots-clés fournis par l'auteur (s'ils existent) et une extraction statistique (TF-IDF).

### Pipeline d'extraction

1. **Mots-clés fournis** : recherche d'une ligne `"Keywords:"` / `"Mots-clés:"` / `"Index Terms:"`, découpage sur `;`, `,`, `•`, `|`.
2. **TF-IDF global** : découpage du texte (hors section References) en segments (paragraphes ou groupes de phrases ≥ 80 caractères), vectorisation `TfidfVectorizer` (n-grammes 1 à 3, stop-words FR ou EN selon la langue détectée, `sublinear_tf=True`), tri par score moyen décroissant.
3. **Filtrage des termes génériques** : rejet des candidats contenant un stop-word, un terme structurel (*"figure"*, *"table"*, *"university"*, *"@"*...), un token de moins de 3 caractères, un candidat purement numérique, ou un terme appartenant à la liste de titres de section (évite qu'*"introduction"* devienne un mot-clé).
4. **Fusion mots-clés fournis + TF-IDF** : les mots-clés fournis par l'auteur sont favorisés (score ≥ 0,90), les candidats TF-IDF sont renormalisés en dessous (score max 0,89) pour ne jamais supplanter un mot-clé explicitement déclaré.
5. **Déduplication** : un candidat multi-mots dont l'ensemble de mots est un sur-ensemble d'un candidat déjà retenu est conservé en priorité sur sa version plus courte (ex. *"attention mechanism"* prime sur *"attention"* seul).
6. **Mots-clés par section** : la même mécanique TF-IDF est réappliquée indépendamment sur chaque section détectée par `split_text_into_sections` (Tâche 3.2 — logique dupliquée, voir section 16), hors section `references`/`références`.

### Structures de données

```json
{
  "provided_keywords": ["extractive summarization", "pdf pipeline"],
  "global_keywords": [
    { "keyword": "extractive summarization", "score": 0.95, "method": "provided_keywords" },
    { "keyword": "pdf conversion pipeline", "score": 0.81, "method": "tfidf" }
  ],
  "keywords_by_section": {
    "methodology": [{ "keyword": "pipeline architecture", "score": 1.0, "method": "tfidf" }]
  },
  "configuration": {
    "global_keyword_limit": 15,
    "keywords_per_section": 5,
    "ngram_range": [1, 3],
    "generic_term_filtering": true
  },
  "status": "keywords_generated"
}
```

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T3.4-01 | Article avec section "Keywords" explicite | Ligne `"Keywords: A, B, C"` | `provided_keywords` non vide, priorité sur le score | Haute |
| T3.4-02 | Article sans mots-clés fournis | Aucune ligne "Keywords" | `global_keywords` alimenté uniquement par TF-IDF | Haute |
| T3.4-03 | Texte très court (< 2 segments exploitables) | Résumé d'une phrase | Repli sur un découpage par blocs de 150 mots (`create_text_chunks`) | Moyenne |
| T3.4-04 | Termes génériques présents | Texte contenant *"figure"*, *"university"*, *"the"* | Ces termes n'apparaissent jamais dans les mots-clés retenus | Haute |
| T3.4-05 | Candidats redondants | *"neural network"* et *"network"* tous deux candidats | Seul *"neural network"* retenu | Moyenne |
| T3.4-06 | Article en français | Corpus FR | Stop-words français appliqués, mots-clés cohérents avec le contenu | Haute |

### Critères d'acceptation

- [ ] Des mots-clés sont générés pour tout texte non vide d'au moins quelques centaines de caractères.
- [ ] Les mots-clés fournis par l'auteur sont priorisés sur les mots-clés statistiques.
- [ ] Aucun terme structurel générique (figure, table, université...) n'apparaît dans le résultat final.
- [ ] Les mots-clés par section sont cohérents avec le contenu de chaque section.
- [ ] Le résultat est stable et déterministe (mêmes entrées → mêmes mots-clés, TF-IDF n'introduit pas d'aléa).

### Livrables
`preprocessing/keywords.py` ; persistance dans `PreprocessingResult.article_keywords`.

### Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Dépendance à la segmentation dupliquée (`split_text_into_sections`) | Mots-clés par section incohérents avec les sections affichées ailleurs dans l'application (issues de `sections.py`) | Moyenne | Voir §16 — unification à arbitrer |
| TF-IDF sur corpus mono-document | Les scores TF-IDF sont calculés sur les segments d'un seul article (pas de corpus de référence), ce qui limite la portée statistique de l'IDF | Faible à moyenne (compromis assumé, cf. §4) | Documenté comme limite connue du MVP |

### Definition of Done
```text
☐ Mots-clés fournis détectés et priorisés quand présents
☐ TF-IDF global fonctionnel sur corpus FR et EN
☐ Filtrage des termes génériques actif
☐ Déduplication des candidats redondants active
☐ Mots-clés par section générés
☐ Tests sur dataset FR et EN
```

---

## 7.5 Préparation du texte pour le LLM

### Objectif
Découper et prioriser le texte segmenté afin de produire des requêtes d'inférence maîtrisées en taille, avec un contexte partagé cohérent pour chaque appel au LLM de la Phase 4.

### Priorisation des sections

`select_relevant_sections` (dans `preprocessing/pipeline.py`) attribue une priorité à chaque section détectée :

| Priorité | Sections concernées |
|---|---|
| `core` | `title`, `abstract`, `introduction`, `results`, `discussion`, `conclusion` |
| `optional` | `methodology`, `methods`, `materials and methods`, `related work`, `background` |
| `excluded` | `references`, `bibliography`, `acknowledgements`/`acknowledgments`, `appendix`, `supplementary material` |
| `unknown` | Toute section détectée ne figurant dans aucune des listes ci-dessus (conservée, mais non priorisée explicitement) |

`remove_excluded_sections` retire ensuite toute section marquée `excluded` **avant** le chunking — c'est le mécanisme concret qui empêche les références de dominer le résumé, exigé par le cahier des charges.

### Chunking

`chunk_document` découpe chaque section (déjà filtrée) en blocs de mots avec chevauchement, section par section, puis numérote les chunks globalement.

| Paramètre | Valeur | Unité | Justification |
|---|---|---|---|
| Taille maximale de chunk | 2000 | tokens (approximés à 1500 mots, ratio 0,75 mot/token) | Marge sous la fenêtre de contexte typique d'un modèle local (`qwen2.5:3b`, `OLLAMA_NUM_CTX=4096`), en laissant de la place au préfixe partagé et au prompt système |
| Chevauchement | 200 | tokens (≈150 mots) | Évite la perte de contexte à la frontière de deux chunks (une idée à cheval sur la coupure reste partiellement présente dans les deux) |
| Découpage | Par mots (`str.split()`), pas par phrase ni par token réel du tokenizer LLM | — | Approximation simple ; l'équivalence mot/token (0,75) est une estimation générique, non calibrée sur le tokenizer réel du modèle utilisé |

*(Remarque : le ratio mots/tokens est une approximation usuelle pour l'anglais ; son exactitude pour le français, plus verbeux en tokens par mot dans certains tokenizers, n'est pas vérifiée.)*

### Construction des prompts

`prompting/builder.py` construit deux niveaux de contexte :

1. **Préfixe partagé** (`build_shared_prefix`, calculé une seule fois par document) : `SYSTEM_PROMPT` + bloc « Article Information » (titre, langue, liste des mots-clés globaux).
2. **Prompt par chunk** (`build_prompt`) : préfixe partagé + bloc « Section Information » (nom de section, priorité, contenu du chunk).

`prompting/requests.py` assemble la liste finale `inference_requests`, en excluant systématiquement les chunks de la section `"Title"` (jamais envoyée en inférence — son contenu sert uniquement à l'extraction de métadonnées, Tâche 3.3).

### Structures de données

```json
{
  "chunk_id": 3,
  "section_name": "Methodology",
  "priority": "optional",
  "content": "Our pipeline combines extraction, cleaning...",
  "prompt": "<SYSTEM_PROMPT>\n\nArticle Information\n...\n\nSection Information\n..."
}
```

### Le couplage avec la Phase 4

Cette tâche ne fait que **préparer** les requêtes ; elle ne les envoie pas au moteur d'inférence — cela relève de la Phase 4 (`generate_partial_summaries`). Comme documenté dans la Phase 2 (§17, point « Couplage extraction / résumé »), l'ensemble Phase 2 → Phase 3 → Phase 4 s'exécute aujourd'hui en un seul appel synchrone (`POST /summarize`) : il n'existe pas de point d'arrêt pour inspecter `inference_requests` avant le déclenchement effectif de l'inférence.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T3.5-01 | Article standard, sections core/optional présentes | Sections priorisées | `filtered_sections` ne contient aucune section `excluded` | Haute |
| T3.5-02 | Section très longue (> 1500 mots) | Section `Introduction` de 3000 mots | Découpée en plusieurs chunks avec chevauchement de 150 mots | Haute |
| T3.5-03 | Section courte (< 1500 mots) | Section de 400 mots | Un seul chunk produit, identique au contenu de la section | Moyenne |
| T3.5-04 | Chunk "Title" | Section nommée `"Title"` | Exclue de `inference_requests` malgré son passage par le chunking | Haute |
| T3.5-05 | Préfixe partagé | Métadonnées et mots-clés donnés | Le préfixe contient bien le titre, la langue et la liste des mots-clés globaux | Moyenne |

### Critères d'acceptation

- [ ] Les sections `excluded` (références, annexes...) n'apparaissent jamais dans les chunks envoyés en inférence.
- [ ] Aucun chunk ne dépasse la taille maximale configurée.
- [ ] Le chevauchement entre chunks consécutifs d'une même section est appliqué.
- [ ] Chaque requête d'inférence contient un prompt complet et auto-suffisant (préfixe + contexte de section).
- [ ] Le chunk `"Title"` n'est jamais transmis en inférence.

### Livrables
`preprocessing/pipeline.py` (priorisation/filtrage), `preprocessing/chunking.py`, `prompting/builder.py`, `prompting/requests.py`, `prompting/templates.py`.

### Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Approximation mot/token non calibrée sur le tokenizer réel | Dépassement effectif de la fenêtre de contexte du modèle sur des sections très denses (formules, symboles) | Moyenne | Calibrer expérimentalement le ratio sur le dataset de test avec le tokenizer réel du modèle utilisé |
| Découpage par mots sans respect des frontières de phrase | Une phrase coupée en plein milieu peut être présentée deux fois de façon incomplète (dans le chunk précédent tronqué, et dans le suivant) | Faible à moyenne (atténuée par le chevauchement) | Envisager un découpage par phrase pour une prochaine itération (cf. §14) |

### Definition of Done
```text
☐ Priorisation core/optional/excluded fonctionnelle
☐ Sections excluded retirées avant chunking
☐ Chunking respectant la taille et le chevauchement configurés
☐ Prompts par chunk générés et auto-suffisants
☐ Chunk "Title" exclu de l'inférence
☐ Tests sur sections longues et courtes
```

---

# 8. Dépendances entre les tâches

```text
3.1 Nettoyage
    │  (le texte nettoyé et les lignes taguées par page sont requis en entrée)
    ▼
3.2 Détection des sections
    │
    ├─────────────────────┐
    ▼                     ▼
3.3 Métadonnées      3.4 Mots-clés
    │                     │  (la langue détectée en 3.3 conditionne
    │                     │   le choix des stop-words en 3.4)
    └──────────┬──────────┘
               ▼
        3.5 Chunking + prompts
        (nécessite les sections de 3.2, priorisées ;
         les métadonnées et mots-clés du préfixe partagé
         proviennent de 3.3 et 3.4)
```

- **Séquentielle stricte** : 3.1 → 3.2 (le nettoyage doit précéder la détection de sections, qui travaille sur les lignes nettoyées).
- **Dépendance croisée légère** : 3.4 dépend du résultat de langue calculé en 3.3 (`extract_article_metadata` doit s'exécuter avant `extract_article_keywords` pour connaître la langue) — c'est l'ordre effectivement respecté dans `document_pipeline.py`.
- **Convergence obligatoire avant 3.5** : le chunking et la construction des prompts ont besoin simultanément des sections priorisées (3.2), des métadonnées (3.3) et des mots-clés (3.4).
- **Parallélisable en théorie** : 3.3 et 3.4 pourraient s'exécuter en parallèle si la contrainte de langue partagée était résolue autrement (ex. détection de langue isolée en amont) — non implémenté ainsi actuellement, exécution séquentielle.

---

# 9. Modèles de données produits

### `PreprocessingResult` (persistance, liée à `PipelineRun`)

```json
{
  "pipeline_run_id": "uuid",
  "article_metadata": { "...": "cf. §7.3" },
  "article_keywords": { "...": "cf. §7.4" },
  "sections": [ "...": "cf. §7.2" ],
  "missing_sections": ["Related Work", "Future Work"],
  "selected_sections": [ "...avec champ priority ajouté" ],
  "filtered_sections": [ "...sans les sections excluded" ],
  "chunked_sections": [ "...cf. §7.5" ],
  "cleaning_report": { "...": "cf. §7.1" }
}
```

Cette structure correspond exactement au modèle SQLAlchemy `PreprocessingResult` déjà en place (voir Documentation Phase 2, section 10, pour le pendant `ExtractionResult`), stockée en colonnes JSON. Aucune nouvelle table n'est requise pour la Phase 3.

---

# 10. Gestion des erreurs et dégradations

Contrairement à la Phase 2 (où les erreurs sont souvent des exceptions dures — fichier illisible, échec réseau), la Phase 3 est conçue autour de la **dégradation silencieuse et documentée** plutôt que l'échec :

| Situation | Comportement actuel | Conforme à l'esprit du cahier des charges ? |
|---|---|---|
| Aucune section détectée | Repli sur `"Full Text"` | Oui — le pipeline continue |
| Aucun titre extrait | `title: null`, statut `completed_with_missing_fields` | Oui — signalé, non bloquant |
| Modèle spaCy absent | Liste d'auteurs vide, pas d'exception | Oui, mais silencieux — un log explicite serait préférable (voir §16) |
| Texte d'entrée vide (ex. suite à un échec OCR en Phase 2) | Toutes les étapes s'exécutent sur une chaîne vide, produisent des structures vides ou par défaut, sans exception | Partiellement — aucun signal clair ne remonte que la cause racine est en amont (Phase 2) |
| Erreur inattendue dans un module de la Phase 3 | Remonte comme exception Python standard, capturée par le bloc `except` global de `DocumentPipeline.run` (`failure_stage` = nom de l'étape en cours, ex. `"preprocessing/keywords"`) | Oui, cohérent avec la stratégie globale documentée en Phase 2 §11 |

**Recommandation** : lorsque le texte nettoyé en entrée de 3.2 est vide ou quasi vide (ex. moins de 50 caractères), consigner explicitement un avertissement distinguant « la Phase 3 a échoué » de « la Phase 3 a reçu un texte déjà vide » — actuellement les deux cas produisent une sortie visuellement similaire (sections/métadonnées vides).

---

# 11. Plan de tests de la phase

| ID | Tâches couvertes | Scénario | Résultat attendu | Priorité |
|---|---|---|---|---|
| G3-01 | 3.1→3.5 | Article EN structuré standard (dataset Tâche 2.5) | Sections détectées, métadonnées complètes ou quasi, mots-clés cohérents, chunks valides | Haute |
| G3-02 | 3.1→3.5 | Article FR structuré standard | Idem, avec langue détectée `fr` et stop-words français appliqués | Haute |
| G3-03 | 3.2, 3.5 | Article sans structure de sections claire | Repli `"Full Text"`, chunking appliqué malgré tout sur la section unique | Haute |
| G3-04 | 3.3 | PDF sans aucune métadonnée interne | Extraction textuelle de repli, aucun champ inventé | Haute |
| G3-05 | 3.4 | Article avec et sans section « Keywords » explicite | Comportement différencié conforme à §7.4 | Moyenne |
| G3-06 | 3.5 | Article très long (> 20 pages) | Plusieurs chunks générés par section longue, aucune perte de contenu entre chunks (hors zones de chevauchement) | Haute |
| G3-07 | Bout en bout | Texte d'entrée vide (simulation d'échec OCR amont) | Le pipeline ne lève pas d'exception non gérée ; structures vides cohérentes en sortie | Haute |

---

# 12. Sécurité et confidentialité

La Phase 3 traite exclusivement du texte déjà présent sur le serveur (aucune entrée utilisateur directe, aucun appel réseau sortant). Les considérations de sécurité sont donc réduites par rapport à la Phase 2 :

| Risque | Impact | Protection |
|---|---|---|
| Injection via contenu du PDF dans les prompts LLM (Phase 4) | Un PDF malveillant pourrait tenter d'insérer des instructions dans son texte pour influencer le comportement du LLM en Phase 4 | Non traité au niveau de la Phase 3 elle-même — à couvrir explicitement dans les règles anti-hallucination/anti-injection de la Phase 4 (Tâche 4.1) ; la Phase 3 se contente de transmettre le contenu textuel tel quel dans le contexte du prompt |
| Fuite de données personnelles présentes dans le texte (noms d'auteurs, emails) | Les auteurs et parfois des emails de correspondance transitent par la reconnaissance d'entités et les métadonnées | Usage interne au pipeline uniquement ; pas d'exposition publique au-delà de ce que l'utilisateur a lui-même uploadé et consulte via son propre compte (Phase 5) |
| Consommation mémoire sur documents très volumineux | Le TF-IDF et le chunking opèrent sur l'intégralité du texte en mémoire | Aucune limite actuelle — dépend de la limite de taille de fichier à la Phase 2 (actuellement absente côté serveur, cf. Documentation Phase 2 §13) |

---

# 13. Performance, limites et échelle

- **Nettoyage, sections, chunking** : opérations sur chaînes de caractères et regex, coût négligeable (millisecondes) même sur des articles de plusieurs dizaines de pages.
- **TF-IDF (mots-clés)** : coût dominé par la vectorisation ; reste rapide pour un document unique (pas de corpus externe à charger). Le recalcul par section (Tâche 3.4) multiplie ce coût par le nombre de sections détectées — négligeable en pratique au vu des volumes du dataset de test.
- **spaCy (secours auteurs)** : coût de chargement du modèle non négligeable au premier appel (plusieurs centaines de ms), amortissable par un chargement unique au démarrage du service plutôt qu'à chaque requête — **non implémenté ainsi actuellement** (le modèle est rechargé à chaque appel de `extract_authors` qui l'atteint), point d'optimisation identifié.
- **Limite de volume** : aucune limite explicite sur le nombre de chunks générés pour un document extrêmement long ; en pratique bornée indirectement par l'absence de limite de taille de fichier en amont (Phase 2). *Valeur seuil à déterminer expérimentalement sur le dataset de test.*

---

# 14. MVP et évolutions futures

## 14.1 MVP (état actuel, considéré suffisant pour la validation de la Phase 3)

- Nettoyage par règles déterministes (numéros de page, bruit OCR, césures).
- Détection de sections par dictionnaire de motifs FR/EN.
- Métadonnées par cascade métadonnées PDF → règles positionnelles → NER de secours.
- Mots-clés par TF-IDF + mots-clés fournis, filtrés et dédupliqués.
- Chunking par mots avec chevauchement fixe, priorisation et exclusion de sections.

## 14.2 Évolutions futures

- Brancher `detect_repeated_lines` pour supprimer réellement les en-têtes/pieds de page répétitifs (Tâche 3.1).
- Unifier la segmentation en sections (`sections.py` vs `keywords.py`) sur une seule implémentation.
- Propager les numéros de page réels dans `sections[].metadata.page_start/page_end`.
- Calibrer le ratio mots/tokens du chunking sur le tokenizer réel du modèle d'inférence utilisé.
- Charger le modèle spaCy une seule fois au démarrage du service plutôt qu'à chaque appel.
- Étudier un chunking respectant les frontières de phrase plutôt qu'un découpage brut par nombre de mots.
- Détection de langue plus robuste (au-delà du choix binaire FR/EN).

---

# 15. Décisions techniques actées

| Décision | Choix retenu | Justification |
|---|---|---|
| Aucune dépendance à un modèle NLP lourd par défaut | TF-IDF + règles ; spaCy uniquement en secours optionnel | Vitesse et légèreté du MVP, cohérent avec l'exécution locale sans GPU garanti pour cette phase |
| Persistance des résultats en JSON dans `PreprocessingResult` | Une seule table, colonnes JSON typées par usage | Évite une explosion du schéma relationnel pour des structures encore amenées à évoluer (sections, mots-clés) |
| Exclusion explicite des références avant chunking | Filtrage par nom de section (`remove_excluded_sections`) plutôt que par heuristique de contenu | Fiable tant que la section est correctement nommée/détectée ; répond directement à l'exigence du cahier des charges |
| Chunking par mots plutôt que par tokenizer réel | Approximation 0,75 mot/token | Évite une dépendance au tokenizer spécifique du modèle Ollama utilisé, au prix d'une imprécision assumée |

---

# 16. Points ouverts et zones grises

### Zone grise — Fonction de suppression des en-têtes/pieds de page non branchée
**Constat :** `detect_repeated_lines` existe, est correctement implémentée, mais n'est appelée nulle part.
**Recommandation :** l'intégrer dans `clean_extracted_text` avant la prochaine itération ; c'est un gain rapide (la fonction est déjà écrite et testable isolément).

### Zone grise — Deux logiques de segmentation en sections coexistent
**Constat :** `sections.py::detect_sections` (référence pour l'affichage et le chunking) et `keywords.py::split_text_into_sections` (utilisée uniquement pour les mots-clés par section) sont indépendantes et peuvent diverger sur un même document.
**Interprétations possibles :** (a) séparation volontaire car les besoins diffèrent (l'une génère un résultat affiché/structurant, l'autre un simple regroupement interne pour le calcul de scores) ; (b) duplication non intentionnelle issue d'un développement parallèle.
**Recommandation :** documenter explicitement le choix s'il est volontaire, sinon unifier sur `detect_sections` pour la cohérence globale.

### Zone grise — Orchestrateur `preprocess_document()` non utilisé en production
**Constat :** `preprocessing/pipeline.py::preprocess_document` réimplémente l'enchaînement complet des 5 tâches, mais `document_pipeline.py` (le chemin réellement exécuté) rappelle chaque fonction séparément avec la même logique.
**Recommandation :** soit faire appel à `preprocess_document()` depuis `document_pipeline.py` pour éliminer la duplication, soit supprimer `preprocess_document()` s'il est devenu obsolète.

### Zone grise — Absence de signal distinguant « échec Phase 3 » et « entrée déjà vide »
**Constat :** un texte vide en entrée (par exemple suite à un échec de la Tâche 2.4, OCR) produit des sorties structurellement valides mais vides, indiscernables d'un cas normal côté monitoring.
**Recommandation :** ajouter une vérification de volume minimal de texte en début de Phase 3, avec un avertissement explicite si le seuil n'est pas atteint (cf. Documentation Phase 2, §17, sur l'importance de ne pas masquer un échec amont comme un succès).

---

# 17. Livrables de la phase

- Modules : `preprocessing/cleaning.py`, `sections.py`, `metadata.py`, `keywords.py`, `chunking.py`, `pipeline.py` ; `prompting/builder.py`, `requests.py`, `templates.py`.
- Données persistées : `PreprocessingResult` (texte nettoyé, sections, métadonnées, mots-clés, chunks) par exécution de pipeline.
- Rapports : rapport de nettoyage (`cleaning_report`).
- Documentation : le présent document.
- Tests : suite de tests couvrant les scénarios des sections 7.1 à 7.5 et 11, exécutés sur le dataset de la Phase 2 (Tâche 2.5).

---

# 18. Definition of Done globale

```text
☐ Nettoyage fonctionnel (numéros de page, bruit OCR, césures)
☐ Suppression des en-têtes/pieds de page répétitifs branchée
☐ Détection de sections fonctionnelle en FR et EN, avec repli "Full Text"
☐ Extraction de métadonnées fonctionnelle avec cascade de repli documentée
☐ Extraction de mots-clés (globale + par section) fonctionnelle et filtrée
☐ Chunking respectant taille et chevauchement configurés
☐ Sections exclues (références, annexes) retirées avant chunking
☐ Prompts par chunk générés et auto-suffisants
☐ Zones grises de la section 16 arbitrées ou explicitement actées comme dette technique assumée
☐ Tests exécutés sur le dataset FR + EN de la Phase 2
☐ Documentation technique à jour (ce document)
```

---

# 19. Matrice de traçabilité

| Exigence (cahier des charges) | Tâche | Module | Test | Statut |
|---|---|---|---|---|
| Suppression sauts de ligne excessifs | 3.1 | `cleaning.py` (`normalize_line`) | T3.1-05 | Fait |
| Suppression en-têtes/pieds de page répétitifs | 3.1 | `cleaning.py` (`detect_repeated_lines`, non branchée) | T3.1-04 | **Non satisfait** |
| Suppression/isolation des références | 3.1 / 3.2 / 3.5 | `sections.py` (exclusion), `pipeline.py` (`remove_excluded_sections`) | T3.2-04, T3.5-01 | Fait |
| Suppression des numéros de page | 3.1 | `cleaning.py` (`page_number_pattern`) | T3.1-01 | Fait |
| Correction des espaces | 3.1 | `cleaning.py` (`normalize_line`) | — | Fait |
| Reconstruction basique des paragraphes (césures) | 3.1 | `cleaning.py` (`merge_hyphenation`) | T3.1-02 | Fait |
| Détection des sections principales (FR/EN) | 3.2 | `sections.py` (`detect_sections`) | T3.2-01, T3.2-02 | Fait |
| Fallback si sections non détectées | 3.2 | `sections.py` (repli `"Full Text"`) | T3.2-03 | Fait |
| Extraction titre/auteurs/année/source/DOI/langue/pages | 3.3 | `metadata.py` (`extract_article_metadata`) | T3.3-01 à T3.3-06 | Fait (source peu robuste) |
| Champs absents non bloquants | 3.3 | `metadata.py` | T3.3-04 | Fait |
| Extraction depuis section « Keywords » | 3.4 | `keywords.py` (`extract_provided_keywords`) | T3.4-01 | Fait |
| TF-IDF | 3.4 | `keywords.py` (`generate_tfidf_keywords`) | T3.4-02 | Fait |
| Filtrage des termes génériques | 3.4 | `keywords.py` (`is_valid_keyword`) | T3.4-04 | Fait |
| Mots-clés par section | 3.4 | `keywords.py` (`extract_article_keywords`) | — | Fait (dépend de la segmentation dupliquée, §16) |
| Découpage en chunks | 3.5 | `chunking.py` (`chunk_document`) | T3.5-02, T3.5-03 | Fait |
| Priorisation des sections importantes | 3.5 | `pipeline.py` (`select_relevant_sections`) | T3.5-01 | Fait |
| Exclusion/réduction des références | 3.5 | `pipeline.py` (`remove_excluded_sections`) | T3.5-01 | Fait |
| Prompts par section | 3.5 | `prompting/builder.py`, `requests.py` | T3.5-04, T3.5-05 | Fait |

---

*Fin du document — Phase 3. Le prochain document indépendant (Phase 4) adoptera, comme celui-ci, une structure adaptée à son propre contenu plutôt qu'un calque des documents précédents.*
