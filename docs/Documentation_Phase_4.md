> **Note de mise en forme (conversion `.docx`)**
> Titres (`#`/`##`/`###`) → bleu Yonnov'IA `#2596BE`, police serif grasse (ex. Georgia Bold), conforme au rendu de la charte. Corps de texte, tableaux, code → noir uniquement. Logo Yonnov'IA (`frontend/public/logo.jpg`) en en-tête Word sur **chaque page**, pas seulement la page de garde. Procédure d'application détaillée en tête du document Phase 2.
>
> **Sommaire volontairement distinct des Phases 2 et 3.** La Phase 4 n'ajoute ni infrastructure (Phase 2) ni heuristiques de traitement de texte (Phase 3) : elle porte sur le **comportement d'un modèle de langage** — prompts, fiabilité, dégradation, contrôle qualité. La structure ci-dessous reflète cette nature spécifique (contrat de sortie, couches de résilience) plutôt qu'un calque des documents précédents.

---

# PAGE DE GARDE

![Logo Yonnov'IA](../frontend/public/logo.jpg)

# Yonnov'IA
## Documentation technique

# Phase 4 — Résumé automatique structuré
## Sprint 4 — Génération IA du résumé scientifique

**Durée estimée :** Semaine 4 à Semaine 5
**Version du document :** 1.0
**Date :** 26/08/2026
**Auteur :** Équipe Yonnov'IA — Team07-E26

---

# SOMMAIRE

*(champ TOC à régénérer automatiquement lors de la conversion Word)*

1. Vue d'ensemble de la phase
2. Position dans la chaîne IA
3. Les trois couches de résilience face à l'échec
4. Panorama des modules
5. Le contrat de sortie imposé au modèle
6. Documentation détaillée des tâches
   6.1 Conception des prompts de résumé
   6.2 Intégration LLM local ou configurable
   6.3 Génération du résumé structuré
   6.4 Résumé hiérarchique pour articles longs
   6.5 Contrôle qualité du résumé
7. Dépendances entre les tâches
8. Modèles de données produits
9. Gestion des erreurs et dégradations
10. Plan de tests de la phase
11. Sécurité, confidentialité et anti-hallucination
12. Performance, coûts et limites
13. MVP et évolutions futures
14. Décisions techniques actées
15. Points ouverts et zones grises
16. Livrables de la phase
17. Definition of Done globale
18. Matrice de traçabilité

---

# 1. Vue d'ensemble de la phase

## 1.1 Objectif

La Phase 4 transforme les chunks priorisés et les prompts construits en Phase 3 en un résumé scientifique structuré, fidèle au document source, rédigé en français ou en anglais selon la langue détectée ; c'est la seule phase du pipeline qui invoque effectivement un modèle de langage.

## 1.2 Ce qui distingue cette phase des précédentes

Les Phases 2 et 3 sont déterministes : à entrées identiques, elles produisent toujours les mêmes sorties. La Phase 4, à l'inverse, introduit un composant non déterministe — un LLM local via Ollama — dont la sortie peut varier, halluciner, mal se structurer, ou tout simplement être indisponible. La majeure partie de la complexité technique de cette phase ne réside donc pas dans l'appel au modèle lui-même, réduit à une seule fonction (`ollama.chat`), mais dans **tout ce qui encadre cet appel** : des contraintes de prompt strictes, un post-traitement de « rattrapage » du résultat, et des mécanismes de repli en cascade.

## 1.3 Résultat attendu en sortie de phase

- Un résumé Markdown structuré (12 sections imposées), en français ou en anglais.
- La même information sous forme JSON structurée (une clé par section), pour une consommation programmatique par la Phase 5.
- Persistance en base (`Summary`) et sur disque (`summary.md`, `summary.json`), liée à l'exécution de pipeline (`PipelineRun`).
- *(Prévu par le cahier des charges, non branché actuellement)* Un score de qualité et une décision PASS/REVIEW/FAIL par résumé généré — voir Tâche 6.5.

## 1.4 Périmètre

**Inclus** : conception et gestion des prompts (chunk et fusion), appel au moteur d'inférence configurable, post-traitement/structuration du résumé final, stratégie de repli en cas d'échec du LLM.

**Non inclus** : l'affichage du résumé (Phase 5), l'export Markdown/PDF (Phase 5, Tâches 5.4–5.5), l'extraction des chunks eux-mêmes (Phase 3, Tâche 3.5 — la Phase 4 les consomme tels quels).

**Point de périmètre à noter d'emblée** : le module de contrôle qualité (`app/services/quality/`) prévu par la Tâche 4.5 du cahier des charges **existe dans le code, entièrement implémenté, mais n'est appelé par aucune autre partie de l'application**. Il est documenté en détail en section 6.5 et signalé dans la matrice de traçabilité comme « livré, non intégré ».

---

# 2. Position dans la chaîne IA

```text
Phase 3 (Préparation)
   inference_requests[] (un prompt par chunk, hors "Title")
   metadata{}, keywords{}
        │
        ▼
┌─────────────────────────────────────────────┐
│                 PHASE 4                        │
│                                                 │
│  6.2 Moteur d'inférence (Ollama / vLLM)         │
│        │                                       │
│        ▼                                       │
│  generate_partial_summaries()                  │
│    - un appel LLM par chunk                    │
│    - repli extractif si un appel échoue         │
│        │                                       │
│        ▼                                       │
│  partial_summaries[]                            │
│        │                                       │
│        ▼                                       │
│  6.3 merge_summary()                            │
│    - un seul prompt de fusion (tous les          │
│      partial_summaries + metadata + keywords)   │
│    - repli extractif si la fusion échoue         │
│        │                                       │
│        ▼                                       │
│  6.3 finalize_summary() + parse_summary_to_json  │
│    - "grounding" métadonnées/mots-clés            │
│    - nettoyage des fragments incomplets           │
│        │                                       │
│        ▼                                       │
│  summary_markdown + summary_structured (JSON)    │
│                                                 │
│  [non branché] 6.5 SummaryQualityJudge          │
└─────────────────────────────────────────────┘
        │
        ▼
Phase 5 (Interface, exports)
```

**Entrées** : `inference_requests` (Phase 3), `metadata`, `keywords` (Phase 3).

**Sorties consommées par la Phase 5** : `summary_markdown` (affichage, export Markdown/PDF), `summary_structured` / `summary.json` (affichage par section).

**Couplage avec la Phase 2/3** : comme déjà noté dans les documents précédents, l'ensemble Extraction → Préparation → Résumé s'exécute aujourd'hui en un seul appel synchrone `POST /summarize`. La Phase 4 hérite donc de cette contrainte : il n'existe pas de point d'entrée permettant de relancer uniquement la génération du résumé sur des `inference_requests` déjà calculés, sans repasser par l'extraction et le nettoyage complets.

---

# 3. Les trois couches de résilience face à l'échec

C'est l'angle le plus structurant de cette phase et il traverse les tâches 4.2, 4.3 et 4.4 du cahier des charges : **à quel niveau le système absorbe-t-il un échec du LLM ?** Le code actuel superpose trois couches indépendantes, qu'il est utile de comprendre ensemble avant le détail par tâche.

| Couche | Portée | Déclencheur | Mécanisme | Module |
|---|---|---|---|---|
| **1. Par chunk** | Un seul appel LLM (un chunk) | Toute exception levée par `engine.generate(request)` | Capture de l'exception, appel à `generate_extractive_partial_summary` (résumé extractif déterministe du chunk), le résultat est marqué `"status": "fallback"` | `summarization/partial_summary.py` |
| **2. Fusion finale** | L'appel de fusion (`merge_summary`) | Toute exception pendant la fusion (modèle indisponible, JSON malformé, dépassement de contexte, etc.) | Capture de l'exception, appel à `generate_extractive_final_summary` (résumé extractif structuré à partir des `partial_summaries` déjà produits) | `summarization/merge_summary.py` (appelant), `summarization/extractive_fallback.py` (repli) |
| **3. Moteur d'inférence** | Le choix du backend lui-même | Configuration (`BACKEND_ENGINE`) | Fabrique (`InferenceFactory`) sélectionnant `OllamaEngine` (fonctionnel) ou `VLLMEngine` (stub, lève `NotImplementedError` à l'appel) | `inference/factory.py` |

**Ce qui n'existe pas** : un mécanisme de détection *a priori* de la disponibilité du moteur (type `engine.is_available()`) avant de lancer le traitement complet. La résilience actuelle est entièrement **réactive** (on tente, on rattrape l'échec après coup), jamais **préventive**. En pratique, cela signifie qu'un document peut déclencher jusqu'à N+1 tentatives d'appel au modèle avant de basculer intégralement en mode extractif (N chunks + 1 fusion), chacune pouvant consommer du temps avant d'échouer, plutôt que de basculer immédiatement en mode extractif dès le premier échec constaté.

---

# 4. Panorama des modules

| Module | Rôle |
|---|---|
| `prompting/templates.py` | `SYSTEM_PROMPT` partagé, utilisé pour chaque prompt de chunk (hérité de la Phase 3) |
| `inference/base_engine.py` | Interface commune (`generate(request) -> dict`) |
| `inference/ollama_engine.py` | Implémentation fonctionnelle via Ollama (modèle configurable, `SUMMARY_MODEL`) |
| `inference/vllm_engine.py` | Implémentation stub, lève explicitement `NotImplementedError` |
| `inference/factory.py` | Sélection du moteur selon `BACKEND_ENGINE` (`"ollama"` ou `"vllm"`) |
| `summarization/partial_summary.py` | Orchestration des appels par chunk + repli par chunk (couche 1) |
| `summarization/merge_summary.py` | Construction du prompt de fusion, appel au moteur, post-traitement (« grounding »), structuration JSON |
| `summarization/extractive_fallback.py` | Génération d'un résumé structuré sans LLM (repli des couches 1 et 2) |
| `quality/judge_prompt.py`, `judge.py`, `quality_schema.py` | Juge de qualité LLM du résumé final (**non intégré au pipeline**, voir §6.5) |

---

# 5. Le contrat de sortie imposé au modèle

Avant de détailler les tâches, il est utile de fixer le vocabulaire : la Phase 4 impose au LLM une **structure Markdown fixe**, déclinée en français (`FRENCH_SUMMARY_STRUCTURE`) et en anglais (`ENGLISH_SUMMARY_STRUCTURE`), à 12 sections identiques dans les deux langues :

`Métadonnées` · `Sujet principal` · `Problématique` · `Objectifs` · `Méthodologie` · `Résultats principaux` · `Contributions scientifiques` · `Limites` · `Perspectives` · `Mots-clés` · `Résumé synthétique` · `Points à retenir`

Cette structure est à la fois :
- **injectée dans le prompt de fusion** (le modèle reçoit littéralement le gabarit à remplir), et
- **réutilisée après coup** par `parse_summary_to_json` pour extraire chaque section du Markdown généré vers un objet JSON (`heading_map`), quelle que soit la langue.

Deux sections (`Métadonnées`, `Mots-clés`) sont considérées **non fiables si écrites par le modèle** : elles sont systématiquement écrasées après génération par les valeurs authentiques de la Phase 3 (`_ground_metadata`, `_ground_keywords`). Le LLM ne les invente donc jamais réellement dans le produit final, même s'il les a mal reproduites ou omises dans sa réponse brute.

---

# 6. Documentation détaillée des tâches

## 6.1 Conception des prompts de résumé

### Objectif
Définir les prompts qui contraignent le modèle à produire un résumé fidèle, structuré et dans la bonne langue, à deux niveaux : par chunk (Phase 3) et pour la fusion finale (cette phase).

### Les deux prompts effectifs

| Niveau | Fonction | Contenu |
|---|---|---|
| **Par chunk** | `prompting/builder.build_prompt` (Phase 3) | `SYSTEM_PROMPT` (rôle, consignes générales : fidélité, pas d'invention, style académique) + contexte du document (titre, langue, mots-clés) + contenu du chunk |
| **Fusion finale** | `merge_summary.build_merge_prompt` | Liste de règles impératives très détaillées (voir extrait ci-dessous) + métadonnées JSON + mots-clés JSON + tous les `partial_summaries` en JSON + structure Markdown imposée |

### Règles anti-hallucination effectivement présentes dans le prompt de fusion

Le prompt de fusion (`build_merge_prompt`) ne se contente pas de demander un résumé : il impose, en langage naturel mais de façon très prescriptive, des règles vérifiables :

- Limite de longueur globale (600 mots), et par section (2 phrases pour les sections narratives, 3 puces pour Résultats/Contributions).
- Attribution numérique complète obligatoire pour tout résultat chiffré : **ENTITÉ → VALEUR → MÉTRIQUE → UNITÉ → CONFIGURATION**, sans jamais réassocier une valeur à un autre outil/modèle/matériel.
- Distinction stricte entre `Contributions scientifiques` (ce que l'article démontre déjà) et `Perspectives` (ce qui est seulement prévu/proposé) — interdiction explicite de mélanger les deux.
- Une limitation ne doit être rapportée que si elle est **explicitement énoncée comme telle** dans les résumés partiels ; en son absence, le modèle doit écrire exactement *"No explicit limitations were identified in the source"* (ou l'équivalent français) plutôt que d'en inventer une.
- Interdiction des marqueurs de gabarit non remplis (`"[Your ...]"`, `"[Insert ...]"`).
- Consigne explicite de langue, alignée sur la langue détectée par la Phase 3 (pas de traduction).
- Instruction de vérification interne avant de répondre (« avant de retourner la réponse, vérifie que le Résumé synthétique et les Points à retenir existent »).

### Ce que le prompt ne garantit pas structurellement

Ces règles sont des **instructions textuelles**, pas des contraintes vérifiées mécaniquement au moment de la génération (pas de grammaire de sortie contrainte, pas de mode JSON strict d'Ollama utilisé ici). Leur respect dépend donc entièrement de la capacité du modèle choisi (`qwen2.5:3b` par défaut) à les suivre. C'est précisément le rôle prévu — mais non branché — du juge de qualité (Tâche 6.5) que de vérifier après coup si ces règles ont été respectées.

### Tests couvrant cette tâche

`backend/tests/test_sprint_43_summary_guards.py::test_merge_prompt_requires_numerical_attribution_and_grounded_sections` vérifie explicitement la présence, dans le prompt généré, de l'exigence d'attribution numérique complète et des règles de grounding des sections.

### Critères d'acceptation

- [x] Le prompt de fusion exige explicitement la fidélité au texte source.
- [x] Le prompt exige que le modèle signale l'absence d'information plutôt que de l'inventer.
- [x] La réponse attendue est structurée (Markdown à 12 sections imposées).
- [x] Les prompts sont documentés dans le code source et testés (`test_sprint_43_summary_guards.py`).
- [ ] *(Non garanti structurellement)* Le respect des règles n'est vérifié par aucun mécanisme automatique au moment de la génération — seul un contrôle a posteriori (Tâche 6.5) pourrait le faire, et il n'est pas branché.

### Livrables
`prompting/templates.py`, `summarization/merge_summary.py` (`build_merge_prompt`, `FRENCH_SUMMARY_STRUCTURE`, `ENGLISH_SUMMARY_STRUCTURE`).

---

## 6.2 Intégration LLM local ou configurable

### Objectif
Permettre de générer les résumés via un moteur d'inférence configurable, avec repli si le moteur est indisponible.

### État réel par rapport aux options du cahier des charges

| Option prévue | État |
|---|---|
| LLM local via Ollama | **Fonctionnel** — `OllamaEngine`, modèle par défaut `qwen2.5:3b` (configurable via `SUMMARY_MODEL`) |
| Modèle open-source local | Couvert par Ollama (tout modèle compatible peut être configuré) |
| Connecteur configurable vers une API externe | **Stub explicite** — `VLLMEngine.generate` lève `NotImplementedError("VLLM inference is not implemented yet")` ; la fabrique (`InferenceFactory`) sait déjà router vers ce moteur via `BACKEND_ENGINE=vllm`, mais aucun appel réel n'est possible |
| Mode fallback résumé extractif simple | **Fonctionnel**, à deux niveaux (couches 1 et 2 de la section 3) |

### Configuration du moteur Ollama

```python
OLLAMA_CONFIG = {
    "model": SUMMARY_MODEL,        # défaut : "qwen2.5:3b"
    "temperature": OLLAMA_TEMPERATURE,   # défaut : 0.2
    "top_p": OLLAMA_TOP_P,               # défaut : 0.9
    "num_predict": OLLAMA_NUM_PREDICT,   # défaut : 2000
    "num_ctx": OLLAMA_NUM_CTX,           # défaut : 8192
}
```

Le modèle peut être surchargé par requête (`SummarizeRequest.model`, transmis jusqu'à `DocumentPipeline.run(model=...)`).

### Gestion des erreurs par chunk (rappel, couche 1)

```text
POUR CHAQUE requête d'inférence:
    TENTER:
        résumé ← moteur.generate(requête)
    SAUF Exception AS e:
        journaliser("Error on chunk ...: " + str(e))
        résumé ← generate_extractive_partial_summary(requête, mots_clés)
        marquer résumé.status = "fallback"
    ajouter résumé à la liste des résultats
```

Ce comportement, et le bug qui l'empêchait de fonctionner sur Windows (crash `UnicodeEncodeError` sur un caractère emoji dans un message de log), a été identifié et corrigé au cours du développement du projet — voir Documentation Phase 2, mention associée dans la matrice de traçabilité de cette phase (section 18) : sans ce correctif, un simple échec ponctuel du moteur LLM faisait échouer l'intégralité de la requête HTTP au lieu de basculer proprement sur le résumé extractif.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T4.2-01 | Modèle Ollama disponible et modèle installé | Appel normal | Résumé généré par le LLM, `status` absent (pas de fallback) | Haute |
| T4.2-02 | Modèle Ollama configuré mais non téléchargé | `ollama.chat` lève `ResponseError (model not found)` | Repli extractif par chunk, `status: "fallback"`, pipeline non interrompu | Haute *(reproduit et corrigé en session de développement réelle)* |
| T4.2-03 | `BACKEND_ENGINE=vllm` | Toute requête | `NotImplementedError` levée immédiatement, capturée par la couche 1 (par chunk) ou couche 2 (fusion) | Moyenne |
| T4.2-04 | Changement de modèle par requête | `SummarizeRequest.model="qwen2.5:7b"` | Le modèle demandé est utilisé, tracé dans `PipelineRun.model` | Moyenne |

### Critères d'acceptation

- [x] Le résumé peut être généré via un moteur configurable (Ollama).
- [x] Le modèle est configurable par variable d'environnement et par requête.
- [x] Les erreurs du moteur LLM sont gérées sans interrompre le pipeline (deux couches de repli).
- [ ] *(Non implémenté, mais explicitement documenté comme tel dans le code)* Le connecteur vers une API externe (vLLM) n'est pas opérationnel.

### Livrables
`inference/base_engine.py`, `inference/ollama_engine.py`, `inference/vllm_engine.py`, `inference/factory.py`.

---

## 6.3 Génération du résumé structuré

### Objectif
Produire, à partir des résumés partiels, un unique résumé Markdown structuré fidèle à la structure imposée, puis sa version JSON exploitable par l'interface.

### Fonctionnement détaillé

1. `build_merge_prompt` assemble le prompt de fusion (§6.1) à partir de `metadata`, `keywords` et **l'intégralité** de `partial_summaries` sérialisés en JSON.
2. `merge_summary` appelle le moteur d'inférence avec ce prompt unique (`chunk_id: "final_summary"`).
3. `finalize_summary` post-traite la réponse brute du modèle :
   - `_ground_metadata` : remplace intégralement le bloc « Métadonnées » écrit par le modèle par les valeurs authentiques issues de la Phase 3 (insertion après le titre si la section est absente de la réponse du modèle).
   - `_ground_keywords` : remplace de la même façon le bloc « Mots-clés » par la liste authentique (`keywords.global_keywords`) — uniquement si la section existe déjà dans la réponse du modèle (contrairement aux métadonnées, elle n'est pas réinsérée si absente).
   - `_remove_malformed_trailing_fragment` : supprime les fragments manifestement incomplets en fin de réponse (titre orphelin, caractère isolé, marqueur Markdown non refermé) — un filet de sécurité contre les réponses tronquées par une limite de génération (`num_predict`).
4. `parse_summary_to_json` convertit le Markdown final en objet JSON (une clé par section, via `heading_map` bilingue), pour un usage structuré côté API/Phase 5.

### Structures de données

```json
{
  "metadata": { "...": "cf. Documentation Phase 3, §7.3" },
  "main_topic": "...",
  "problem_statement": "...",
  "objectives": "...",
  "methodology": "...",
  "main_results": "...",
  "scientific_contributions": "...",
  "limitations": "...",
  "future_work": "...",
  "keywords": { "...": "cf. Documentation Phase 3, §7.4" },
  "executive_summary": "...",
  "key_takeaways": "..."
}
```

### Une limite de conception à noter : le « grounding » partiel

Le mécanisme de `finalize_summary` ne corrige que deux sections (métadonnées, mots-clés). Toutes les autres sections (méthodologie, résultats, limites, perspectives...) restent **telles que le modèle les a écrites**, sans vérification automatique de fidélité au texte source à ce stade — cette vérification est le rôle prévu de la Tâche 6.5, qui n'est pas branchée. Le prompt (§6.1) demande au modèle de rester fidèle, mais rien dans `merge_summary`/`finalize_summary` ne le vérifie après coup pour ces sections.

### Tests

`test_sprint_43_summary_guards.py::test_required_sections_keywords_and_grounded_sections`, `::test_keyword_artifact_is_the_shared_json_markdown_pdf_source`, `::test_metadata_recovers_header_and_preserves_missing_values` couvrent respectivement : la présence de toutes les sections requises et le grounding effectif des mots-clés, la cohérence entre l'artefact de mots-clés partagé et les exports Markdown/JSON/PDF, et la récupération correcte des métadonnées même lorsque certaines sont absentes.

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T4.3-01 | Fusion réussie, toutes sections présentes | Résumés partiels complets | Markdown à 12 sections, JSON correspondant, métadonnées et mots-clés authentiques (issus de la Phase 3, pas du modèle) | Haute |
| T4.3-02 | Modèle omet la section « Métadonnées » | Réponse LLM sans bloc métadonnées | Le bloc est réinséré après le titre par `_ground_metadata` | Haute |
| T4.3-03 | Réponse tronquée en fin de génération | Réponse se terminant par `"## Ke"` | Fragment incomplet supprimé par `_remove_malformed_trailing_fragment` | Moyenne |
| T4.3-04 | Résumé en français | `metadata.language == "fr"` | Structure et libellés en français, cohérents avec `parse_summary_to_json` (mapping bilingue) | Haute |

### Critères d'acceptation

- [x] Le résumé respecte la structure Markdown imposée (12 sections, ordre fixe).
- [x] Les métadonnées et mots-clés du résultat final sont toujours ceux, authentiques, de la Phase 3 — jamais réinventés par le modèle.
- [x] Les sections manquantes du gabarit métadonnées sont réinsérées automatiquement.
- [ ] *(Non couvert)* La fidélité des sections narratives (méthodologie, résultats, limites...) au texte source n'est vérifiée par aucun mécanisme automatique dans cette tâche.
- [x] Le résultat est disponible en Markdown et en JSON structuré.

### Livrables
`summarization/merge_summary.py` (fonctions `build_merge_prompt`, `merge_summary`, `finalize_summary`, `parse_summary_to_json`), persistance `Summary.summary_text` / `.summary_json`.

---

## 6.4 Résumé hiérarchique pour articles longs

### Objectif
Garantir qu'un article long, découpé en de nombreux chunks (Phase 3), produit malgré tout un résumé final cohérent sans dépasser les capacités de contexte du modèle.

### Ce qui est réellement implémenté : une hiérarchie à un seul niveau

Le pipeline actuel implémente bien un résumé en deux temps, conforme à l'esprit du cahier des charges :

1. **Niveau 1 — par chunk** : chaque chunk (Phase 3) reçoit son propre résumé partiel (`generate_partial_summaries`), avec repli extractif individuel en cas d'échec (couche 1, §3).
2. **Niveau 2 — fusion unique** : tous les résumés partiels, quel que soit leur nombre, sont assemblés et envoyés **en une seule fois** dans un unique prompt de fusion (`build_merge_prompt`).

### La limite non couverte

Le cahier des charges prévoit explicitement une hiérarchie à plusieurs niveaux pour les documents longs : *« Résumé par section, résumé par chunk si section absente, **fusion des résumés intermédiaires**, génération du résumé final »*. Le code actuel ne comporte **aucune étape de fusion intermédiaire** : `build_merge_prompt` sérialise l'intégralité de `partial_summaries` (JSON) dans un seul prompt, quelle que soit sa taille. Pour un article avec un grand nombre de chunks (un long article multi-sections, avec le chunking par défaut de 1500 mots/section, cf. Documentation Phase 3 §7.5), la taille cumulée des résumés partiels peut approcher, voire dépasser, la fenêtre de contexte configurée (`OLLAMA_NUM_CTX`, 8192 tokens par défaut pour le modèle de fusion) — sans qu'aucun mécanisme ne détecte ou ne prévienne ce dépassement avant l'appel.

En cas de dépassement effectif, le comportement observé dépend du moteur Ollama (troncature silencieuse du contexte le plus souvent) — ce n'est pas un cas actuellement testé dans la suite de tests du projet.

### Conservation des preuves/passages sources

Le cahier des charges suggère la « conservation des preuves ou passages sources si possible ». Le mécanisme le plus proche de cette exigence est indirect : les `partial_summaries` (résumés intermédiaires, niveau 1) sont persistés tels quels sur disque (`inference/partial_summaries.json`) et consultables via l'historique de pipeline (`InferenceRun`), ce qui permet de retracer, après coup, quel passage source a nourri quelle partie du résumé final — mais il n'existe pas de lien explicite (type citation ou renvoi) entre une affirmation du résumé final et le résumé partiel dont elle est issue.

### Tests

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T4.4-01 | Article court (1–3 chunks) | Dataset de test standard | Fusion en un seul prompt, résumé cohérent | Haute |
| T4.4-02 | Article long (> 15 chunks) | Article scientifique de plusieurs dizaines de pages | *(Non actuellement testé)* Comportement du modèle en cas d'approche/dépassement de `OLLAMA_NUM_CTX` à documenter | Haute — **à couvrir en priorité** |
| T4.4-03 | Tous les chunks en échec (couche 1) | Modèle indisponible pour chaque chunk | `partial_summaries` entièrement composés de résumés extractifs (`status: "fallback"`), fusion tentée malgré tout sur ces résumés extractifs | Moyenne |

### Critères d'acceptation

- [x] Un article de taille standard du dataset de test est traité correctement (résumé cohérent, structure respectée).
- [ ] *(Non satisfait)* Les articles très longs (nombreux chunks) sont gérés par une fusion progressive plutôt qu'un unique prompt cumulant tous les résumés partiels.
- [ ] *(Non satisfait)* Une limite explicite (nombre de chunks, taille cumulée) déclenche une stratégie dégradée documentée avant d'atteindre la limite de contexte du modèle.
- [x] Les sections importantes (issues des chunks `core`/`optional`, cf. Documentation Phase 3 §7.5) sont priorisées en amont, avant même la fusion.

### Livrables
`summarization/partial_summary.py` (niveau 1), `summarization/merge_summary.py` (niveau 2, fusion unique).

### Risque principal
| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Absence de fusion progressive pour les documents très longs | Dépassement silencieux de la fenêtre de contexte, résumé final tronqué ou incohérent, sans erreur explicite remontée à l'utilisateur | Moyenne à élevée sur des articles longs (dépend directement du nombre de chunks produits en Phase 3) | Introduire un seuil (nombre de chunks ou volume cumulé de `partial_summaries`) déclenchant une fusion en plusieurs passes (fusion par groupe de chunks, puis fusion des fusions) |

---

## 6.5 Contrôle qualité du résumé

### Objectif
Vérifier automatiquement que le résumé généré respecte les sections obligatoires, ne contient pas d'information inventée, et produire un score de confiance exploitable.

### Constat central de cette tâche : la fonctionnalité existe et n'est pas utilisée

Contrairement aux autres tâches de cette phase, où le code correspond globalement (avec des limites documentées) à l'exigence, la Tâche 4.5 présente un cas particulier : **un module de contrôle qualité complet, sophistiqué et bien structuré existe (`app/services/quality/`), mais n'est appelé nulle part** — ni par `DocumentPipeline.run`, ni par aucune route API. Aucun score de qualité n'est donc jamais réellement calculé en usage normal du produit à ce jour.

### Ce que fait `SummaryQualityJudge` (une fois invoqué manuellement)

`judge.py::SummaryQualityJudge.evaluate(source, summary)` appelle un modèle Ollama (`qwen2.5:3b` par défaut, indépendant du modèle de génération) avec un prompt d'audit (`judge_prompt.build_judge_prompt`, ~250 lignes de règles d'évaluation) qui :

1. Compare, **section par section** (les 12 sections du contrat de sortie, §5), le résumé généré à la source fournie.
2. Détermine, pour chaque section, la disponibilité de l'information dans la source (`AVAILABLE` / `PARTIAL` / `NOT_AVAILABLE`) — une information absente de la source n'est jamais pénalisée si le résumé le signale correctement.
3. Calcule 5 scores par section (`score`, `content_coverage`, `fidelity`, `readability`, `noise`), chacun de 0 à 10.
4. Calcule 5 vérifications globales (`metadata_accuracy`, `keyword_quality`, `numerical_accuracy`, `factual_accuracy`, `missing_information_handling`).
5. Détecte des **erreurs critiques** typées (contradiction factuelle, contradiction numérique, mauvaise attribution, information/métadonnée/limite/perspective fabriquée, mauvais placement de section).
6. Émet une **décision finale** : `PASS`, `REVIEW`, ou `FAIL`.
7. Le rapport brut du modèle est validé et normalisé par `quality_schema.validate_quality_report`, qui lève une erreur explicite si la structure JSON attendue n'est pas respectée (12 sections exactement, scores entiers 0–10, décision parmi les 3 valeurs autorisées) — cette validation stricte protège contre une réponse de juge mal formée, mais implique aussi qu'un juge qui échoue à produire un JSON valide fait échouer l'évaluation elle-même (aucun repli prévu pour le juge, contrairement à la génération de résumé elle-même, §3).

### Structure de données produite (si le module était invoqué)

```json
{
  "overall_score": 7,
  "decision": "REVIEW",
  "sections": {
    "methodology": {
      "source_availability": "AVAILABLE",
      "score": 6,
      "content_coverage": 7,
      "fidelity": 6,
      "readability": 8,
      "noise": 10,
      "issues": ["Dataset size mentioned in source is omitted."]
    }
  },
  "global_checks": {
    "metadata_accuracy": 9,
    "keyword_quality": 8,
    "numerical_accuracy": 5,
    "factual_accuracy": 7,
    "missing_information_handling": 9
  },
  "critical_errors": [],
  "recommendations": ["Include the reported dataset size in Methodology."]
}
```

### Ce qui manque pour une intégration effective

- Aucun appel à `SummaryQualityJudge` dans `DocumentPipeline.run` (par exemple juste après `parse_summary_to_json`, en lui passant `source` = les `partial_summaries` + `metadata`, et `summary` = `summary_structured`).
- Aucune table de persistance dédiée au rapport de qualité (contrairement à `ExtractionResult` pour la qualité d'extraction, Phase 2) — il faudrait soit étendre `Summary`, soit créer une table `SummaryQualityReport`.
- Aucun champ exposé dans `SummarizeResponse` ni dans `SummaryDetailResponse` pour restituer ce score côté API/Phase 5.
- Aucun test automatisé n'exerce `SummaryQualityJudge` ou `validate_quality_report` dans la suite de tests actuelle du projet (`backend/tests/`).

### Tests (état actuel : couverture nulle en pratique, cible ci-dessous)

| ID | Scénario | Entrée | Résultat attendu | Priorité |
|---|---|---|---|---|
| T4.5-01 *(à écrire)* | Rapport de juge valide | JSON conforme au schéma | `validate_quality_report` retourne le rapport normalisé sans erreur | Haute |
| T4.5-02 *(à écrire)* | Rapport de juge incomplet (section manquante) | JSON avec 11 sections au lieu de 12 | `ValueError` explicite levée | Haute |
| T4.5-03 *(à écrire)* | Décision hors énumération | `"decision": "MAYBE"` | `ValueError` explicite levée | Moyenne |
| T4.5-04 *(à écrire, intégration)* | Appel bout en bout après génération d'un résumé réel | Résumé généré par `merge_summary` | Rapport de qualité produit et cohérent avec le contenu réellement généré | Haute — conditionnée au branchement du module |

### Critères d'acceptation

- [ ] *(Non satisfait)* Les résumés incomplets sont signalés automatiquement après génération.
- [ ] *(Non satisfait)* Les sections manquantes ou vides sont visibles via un score ou une alerte exposée à l'utilisateur.
- [x] *(Satisfait au niveau du module isolé)* Les alertes/erreurs critiques produites par le juge sont compréhensibles (texte explicite : ce que dit la source, ce que dit le résumé, pourquoi ils divergent).
- [ ] *(Non documenté car non intégré)* Les limites du contrôle qualité en usage réel (coût, latence, dépendance à un second modèle) ne sont pas encore mesurées faute d'utilisation.

### Livrables
`quality/judge.py`, `quality/judge_prompt.py`, `quality/quality_schema.py` — **livrés en l'état, intégration au pipeline restant à faire**.

### Risque
| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Module non intégré perçu comme fonctionnalité manquante alors que le code existe | Effort dupliqué si quelqu'un le redéveloppe sans le savoir ; ou fonctionnalité annoncée au client sans être réellement active | Élevée (constat direct) | Décision explicite à prendre : brancher le module dans `DocumentPipeline.run` (coût : un appel LLM supplémentaire par résumé, cf. §12) ou documenter formellement son report à une itération ultérieure |

---

# 7. Dépendances entre les tâches

```text
6.1 Prompts (chunk + fusion)
    │  (le prompt de chunk est en réalité construit en Phase 3 ;
    │   le prompt de fusion est spécifique à cette phase)
    ▼
6.2 Moteur d'inférence configurable
    │  (nécessaire pour exécuter tout prompt, quel qu'il soit)
    ▼
6.3 Génération du résumé structuré
    │  (consomme les partial_summaries produits via 6.2 sur les prompts de 6.1)
    │
    ├──────────────► 6.4 Résumé hiérarchique
    │                 (6.4 n'est pas une tâche séquentielle distincte dans le code :
    │                  c'est une propriété — actuellement incomplète — de 6.3)
    │
    └──────────────► 6.5 Contrôle qualité
                      (dépendance forte sur le résumé final de 6.3,
                       mais non câblée dans le code actuel — dépendance
                       logique, pas dépendance d'exécution réelle)
```

- **Séquentielles strictes** : 6.1 → 6.2 → 6.3.
- **6.4 n'est pas une étape séparée dans l'exécution réelle** : c'est une caractéristique attendue de l'implémentation de 6.3 (comment la fusion gère un grand nombre de résumés partiels), actuellement non satisfaite — voir §6.4.
- **6.5 est dépendante de 6.3 mais non connectée** : le module pourrait s'insérer immédiatement après `parse_summary_to_json` sans dépendance technique bloquante ; son absence est un choix (ou un oubli) d'intégration, pas une contrainte technique.

---

# 8. Modèles de données produits

### `InferenceRun` (persistance, étape « par chunk »)

```json
{
  "pipeline_run_id": "uuid",
  "model": "qwen2.5:3b",
  "status": "completed | failed | running",
  "request_count": 8,
  "completed_count": 7,
  "failed_count": 1,
  "started_at": "2026-08-26T10:00:00Z",
  "completed_at": "2026-08-26T10:00:22Z",
  "duration_ms": 22150.4,
  "inference_config": { "model": "qwen2.5:3b", "temperature": 0.2, "top_p": 0.9, "num_predict": 2000, "num_ctx": 8192 },
  "result_metadata": { "total_results": 8, "fallback_count": 1 },
  "error_message": null
}
```

*(`failed_count` compte les chunks tombés en repli extractif — couche 1 de la section 3 — et non des échecs bloquants de la requête HTTP dans son ensemble.)*

### `Summary` (persistance, résultat final)

```json
{
  "pipeline_run_id": "uuid",
  "summary_text": "# Résumé scientifique\n\n## Métadonnées\n...",
  "summary_json": {
    "filename": "article.pdf",
    "metadata": { "...": "cf. Phase 3" },
    "summary": { "...": "cf. §6.3, structure à 12 clés" },
    "summary_markdown": "...",
    "generated_at": "2026-08-26T10:00:25Z",
    "model": "qwen2.5:3b"
  }
}
```

**Absence à noter** : aucun champ ne trace, sur ce modèle, si le résumé final provient de la génération LLM (couche 2 réussie) ou du repli extractif (couche 2 en échec) — contrairement aux résumés partiels, où `status: "fallback"` est explicite. Un consommateur de `Summary` ne peut donc pas distinguer, sans relire les logs serveur, un résumé réellement généré par le modèle d'un résumé entièrement extractif. Voir section 15.

---

# 9. Gestion des erreurs et dégradations

| Situation | Comportement actuel | Observabilité |
|---|---|---|
| Un appel LLM échoue pour un chunk | Repli extractif silencieux pour ce chunk (couche 1) | `status: "fallback"` sur le résumé partiel concerné, comptabilisé dans `InferenceRun.failed_count` |
| L'appel de fusion échoue entièrement | Repli extractif pour l'ensemble du résumé (couche 2) | **Aucun champ dédié** — seul un `logger.warning` côté serveur trace l'événement ; rien n'est visible depuis l'API ou la base |
| Le moteur configuré n'est pas implémenté (`vllm`) | `NotImplementedError` immédiate, capturée par la couche 1 ou 2 selon le moment de l'appel | Comportement identique à un échec Ollama classique du point de vue de l'observabilité |
| Erreur de structure dans la réponse du juge qualité (si le module était branché) | `ValueError` explicite (`validate_quality_report`) | Non applicable actuellement (module non appelé) |
| Erreur non prévue à n'importe quelle sous-étape | Remonte à l'exception globale de `DocumentPipeline.run` (`failure_stage` = `"inference"` ou `"merge"`) | Cohérent avec la stratégie documentée en Phase 2 §11 |

**Recommandation principale de cette section** : ajouter un indicateur explicite (`used_fallback: bool`, ou `generation_method: "llm" | "extractive_fallback"`) sur le modèle `Summary`, afin qu'un résumé entièrement extractif ne soit jamais confondu avec un résumé réellement généré par le LLM — une distinction actuellement invisible pour tout consommateur de l'API.

---

# 10. Plan de tests de la phase

| ID | Tâches couvertes | Scénario | Résultat attendu | Priorité |
|---|---|---|---|---|
| G4-01 | 6.1, 6.3 | Génération bout en bout, modèle disponible | Résumé Markdown à 12 sections, JSON cohérent, métadonnées/mots-clés authentiques | Haute |
| G4-02 | 6.2 | Modèle configuré absent (`ResponseError`) | Repli extractif par chunk puis fusion, `status: "completed"` malgré tout côté pipeline | Haute *(reproduit et corrigé en session réelle)* |
| G4-03 | 6.2 | Backend `vllm` sélectionné | Repli extractif immédiat, aucun crash serveur | Moyenne |
| G4-04 | 6.4 | Article long (nombreux chunks) | *(à définir)* Comportement documenté en cas d'approche de la limite de contexte de fusion | Haute — actuellement non testé |
| G4-05 | 6.5 | Appel manuel de `SummaryQualityJudge` sur un résumé connu | Rapport structuré valide, décision cohérente avec des erreurs volontairement injectées dans un résumé de test | Moyenne — à écrire, module non intégré |
| G4-06 | 6.1, 6.3 | Article en français | Résumé et structure entièrement en français, `parse_summary_to_json` fonctionnel sur les libellés français | Haute |

---

# 11. Sécurité, confidentialité et anti-hallucination

| Risque | Impact | Protection actuelle |
|---|---|---|
| Injection de prompt via le contenu du PDF (texte conçu pour manipuler le LLM) | Le modèle pourrait suivre des instructions cachées dans le texte source plutôt que résumer fidèlement | **Non traité explicitement** — le contenu des chunks est inséré tel quel dans le prompt, sans neutralisation des séquences ressemblant à des instructions |
| Hallucination de métadonnées | Un titre, auteur ou DOI inventé serait trompeur pour l'utilisateur | Neutralisé par construction pour les métadonnées et mots-clés (`_ground_metadata`, `_ground_keywords`, §6.3) — pas pour le reste du contenu |
| Hallucination de résultats/contributions/limites | Information scientifique incorrecte présentée comme fiable | Traité au niveau du **prompt** uniquement (règles anti-hallucination, §6.1) ; aucune vérification a posteriori active (le module capable de le faire, §6.5, n'est pas branché) |
| Fuite de contenu d'un document vers un autre | Un résumé mélangerait le contenu de deux documents différents | Non applicable en l'état : chaque exécution de pipeline traite un seul document, sans état partagé entre requêtes concurrentes au niveau de la génération |
| Consommation de ressources par appels multiples | Un document avec de nombreux chunks génère autant d'appels LLM séquentiels + un appel de fusion (+ potentiellement un appel de juge qualité) | Aucune limite de nombre de chunks à ce jour (cf. Documentation Phase 3 §13) |

---

# 12. Performance, coûts et limites

- **Coût dominant** : chaque chunk = un appel LLM synchrone. Un document à 8 chunks (exemple réel observé en session de test) prend de l'ordre de 20 secondes de bout en bout avec `qwen2.5:3b` sur le matériel de développement du projet (GPU d'entrée de gamme, VRAM partiellement disponible) ; ce chiffre dépend fortement du matériel et n'est pas une garantie contractuelle.
- **Coût du juge qualité (s'il était branché)** : un appel LLM supplémentaire par résumé généré (modèle indépendant, `qwen2.5:3b` par défaut) — à budgétiser explicitement si la Tâche 6.5 est activée, car il double potentiellement le temps de traitement perçu par l'utilisateur pour la seule étape finale.
- **Limite de contexte** : `OLLAMA_NUM_CTX=8192` tokens pour la fusion par défaut ; aucune garde-fou n'empêche de dépasser cette limite sur un document à très nombreux chunks (cf. §6.4).
- **Absence de traitement asynchrone/parallèle** : les appels par chunk sont strictement séquentiels (`generate_partial_summaries` itère un par un) ; aucune parallélisation des appels LLM indépendants n'est mise en œuvre, ce qui allonge linéairement le temps de traitement avec le nombre de chunks.
- **Valeur à déterminer expérimentalement** : le nombre maximal de chunks/pages avant dégradation notable de la qualité de fusion ou dépassement de contexte n'a pas été mesuré systématiquement sur le dataset de test (Documentation Phase 2, Tâche 2.5) à ce jour.

---

# 13. MVP et évolutions futures

## 13.1 MVP (état actuel)

- Prompts de chunk et de fusion opérationnels, avec règles anti-hallucination explicites.
- Moteur Ollama fonctionnel, configurable par variable d'environnement et par requête.
- Repli extractif à deux niveaux (chunk, fusion) — fonctionnel après correction du bug d'encodage identifié en développement.
- Résumé structuré Markdown + JSON, avec grounding des métadonnées et mots-clés.

## 13.2 Évolutions futures

- **Brancher le module de contrôle qualité existant** (`quality/judge.py`) dans `DocumentPipeline.run`, avec persistance dédiée et exposition API — c'est l'écart le plus significatif entre le cahier des charges et l'état actuel du code sur cette phase, et il ne nécessite aucun développement de zéro (le module est déjà écrit et cohérent).
- Introduire une fusion progressive (multi-niveaux) pour les documents à nombreux chunks, avec un seuil explicite déclenchant ce mode.
- Ajouter un indicateur explicite (`generation_method`) sur `Summary` pour distinguer un résumé LLM d'un résumé entièrement extractif.
- Détecter, a priori, l'indisponibilité du moteur d'inférence (`is_available()`) plutôt que de découvrir l'échec après une tentative complète.
- Implémenter réellement le connecteur `VLLMEngine` si un besoin de bascule vers une API externe se confirme.
- Paralléliser les appels par chunk (actuellement strictement séquentiels) pour réduire le temps de traitement total.

---

# 14. Décisions techniques actées

| Décision | Choix retenu | Justification |
|---|---|---|
| Deux niveaux de repli plutôt qu'un seul | Repli par chunk **et** repli de fusion, indépendants | Un échec isolé sur un chunk ne doit pas priver le résumé final du contenu des autres chunks ; un échec de fusion ne doit pas faire perdre tout le travail déjà produit au niveau des chunks |
| Grounding partiel (métadonnées/mots-clés) plutôt que réécriture complète | Seules ces deux sections sont systématiquement corrigées après génération | Ce sont les seules données pour lesquelles Yonnov'IA dispose d'une source de vérité indépendante du LLM (Phase 3) ; les sections narratives n'ont pas d'équivalent « autoritaire » à substituer |
| Structure Markdown imposée plutôt que JSON structuré demandé directement au modèle | Le modèle produit du Markdown, converti en JSON après coup (`parse_summary_to_json`) | Les modèles locaux de la taille utilisée (`qwen2.5:3b`) sont empiriquement plus fiables en génération de texte structuré Markdown qu'en JSON strict sans mode de génération contraint |
| Juge qualité en modèle séparé, non branché au MVP | Développé de façon autonome, isolé du flux principal | Décision (implicite, à confirmer explicitement) de prioriser la fiabilité de la génération elle-même avant d'ajouter une étape d'audit supplémentaire, coûteuse en temps de traitement |

---

# 15. Points ouverts et zones grises

### Zone grise — Module de contrôle qualité non intégré
**Constat :** développé, testé unitairement à l'échelle de sa propre validation (`validate_quality_report`), mais jamais appelé.
**Recommandation :** décision explicite à prendre en priorité — brancher (impact : latence et coût supplémentaires par résumé) ou acter formellement le report, plutôt que de laisser cette ambiguïté implicite.

### Zone grise — Fusion non progressive pour les documents longs
**Constat :** `build_merge_prompt` sérialise l'intégralité des résumés partiels sans limite ni découpage.
**Recommandation :** définir un seuil expérimental (nombre de chunks ou volume cumulé) au-delà duquel une fusion en plusieurs passes est déclenchée, et le tester sur un article volumineux du dataset (Documentation Phase 2, Tâche 2.5).

### Zone grise — Absence de traçabilité du mode de génération du résumé final
**Constat :** rien ne distingue, dans les données persistées, un résumé issu du LLM d'un résumé entièrement extractif (couche 2).
**Recommandation :** ajouter un champ dédié sur `Summary`, à faible coût d'implémentation, à haute valeur d'observabilité.

### Zone grise — Résilience réactive uniquement (pas de vérification préalable de disponibilité)
**Constat :** aucun moteur n'implémente de vérification de disponibilité avant traitement ; chaque échec est découvert après tentative.
**Interprétations possibles :** (a) choix assumé pour rester simple au MVP, le coût d'un échec ponctuel étant faible (repli rapide) ; (b) amélioration non priorisée faute de temps.
**Recommandation :** documenter ce choix comme assumé s'il l'est, plutôt que de le laisser passer pour un oubli.

---

# 16. Livrables de la phase

- Modules fonctionnels : `prompting/templates.py`, `inference/{base_engine,ollama_engine,vllm_engine,factory}.py`, `summarization/{partial_summary,merge_summary,extractive_fallback}.py`.
- Modules livrés mais non intégrés : `quality/{judge,judge_prompt,quality_schema}.py`.
- Données persistées : `InferenceRun`, `Summary`.
- Tests : `test_sprint_43_summary_guards.py`, `test_extractive_fallback.py` (repli extractif, Documentation session de développement).
- Documentation : le présent document.

---

# 17. Definition of Done globale

```text
☐ Prompts de chunk et de fusion opérationnels et testés
☐ Moteur Ollama fonctionnel, configurable (modèle, température, contexte)
☐ Repli extractif fonctionnel aux deux niveaux (chunk, fusion)
☐ Résumé structuré Markdown + JSON produit et persisté
☐ Grounding des métadonnées et mots-clés vérifié par test automatisé
☐ Décision actée sur l'intégration du module de contrôle qualité (branché ou explicitement reporté)
☐ Stratégie de fusion progressive définie pour les documents longs (ou limite documentée si non traitée)
☐ Indicateur de mode de génération (LLM vs extractif) ajouté au modèle Summary
☐ Documentation technique à jour (ce document)
```

---

# 18. Matrice de traçabilité

| Exigence (cahier des charges) | Tâche | Module | Test | Statut |
|---|---|---|---|---|
| Prompts : résumé court, structuré, problématique, méthodologie... | 4.1 | `merge_summary.py` (structures FR/EN) | `test_sprint_43_summary_guards.py` | Fait |
| Règles anti-hallucination | 4.1 | `merge_summary.build_merge_prompt` | `test_merge_prompt_requires_numerical_attribution_and_grounded_sections` | Fait (au niveau prompt uniquement) |
| LLM local via Ollama | 4.2 | `inference/ollama_engine.py` | T4.2-01 | Fait |
| Connecteur configurable vers une API | 4.2 | `inference/vllm_engine.py` | T4.2-03 | Stub explicite, non fonctionnel |
| Mode fallback résumé extractif | 4.2 | `partial_summary.py`, `extractive_fallback.py` | T4.2-02 | Fait |
| Sortie Markdown + JSON structurés | 4.3 | `merge_summary.py` (`finalize_summary`, `parse_summary_to_json`) | `test_required_sections_keywords_and_grounded_sections` | Fait |
| Informations absentes indiquées explicitement | 4.3 | `merge_summary._ground_metadata` | `test_metadata_recovers_header_and_preserves_missing_values` | Fait |
| Résumé par chunk puis fusion | 4.4 | `partial_summary.py` + `merge_summary.py` | G4-01 | Fait (hiérarchie à un seul niveau) |
| Gestion des articles longs sans dépassement de contexte | 4.4 | — | G4-04 | **Non satisfait** |
| Conservation des preuves/passages sources | 4.4 | `partial_summaries.json` persistés (lien indirect) | — | Partiel |
| Vérification des sections obligatoires remplies | 4.5 | `quality/quality_schema.py` | T4.5-01/02 (à écrire) | Livré, **non intégré** |
| Score qualité du résumé | 4.5 | `quality/judge.py` | T4.5-04 (à écrire) | Livré, **non intégré** |
| Alertes utilisateur sur résumé incomplet | 4.5 | — (dépend de l'intégration de `quality/judge.py`) | — | **Non satisfait** |

---

*Fin du document — Phase 4. Le prochain document indépendant (Phase 5) adoptera, de la même façon, une structure propre à son propre contenu (interface, exports, historique) plutôt qu'un calque des documents précédents.*
