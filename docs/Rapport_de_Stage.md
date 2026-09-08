> **Note de mise en forme** : ce document suit la structure exacte du gabarit de référence fourni — Remerciements, Résumé, Table des matières, Liste des figures, Liste des tableaux, Liste des acronymes, Introduction générale, Présentation de l'organisme d'accueil (non numérotée), puis 4 chapitres numérotés avec page de séparation (grand chiffre + mini-sommaire) : 1 Introduction, 2 Contexte théorique, 3 Conception du système et pile technologique, 4 Implémentation. Police Lora, noir uniquement, corps de texte justifié, filet fin en en-tête/pied de page, logo Yonnov'IA en en-tête de chaque page. La table des matières est calculée à partir de la pagination réelle du document (pas un champ à mettre à jour manuellement). Les passages entre crochets `[À compléter — ...]` sont des espaces volontairement laissés vides.

---

# PAGE DE GARDE

![Logo Yonnov'IA](../frontend/public/logo.jpg)

# Rapport de stage

## Conception et développement d'un pipeline d'intelligence artificielle pour l'extraction et la synthèse automatique d'articles scientifiques

**Projet :** Yonnov'IA — Team07-E26
**Période de stage :** [À compléter]
**Étudiant·e :** [À compléter]
**Établissement :** [À compléter]
**Encadrant·e académique :** [À compléter]
**Encadrant·e en entreprise :** [À compléter]
**Date :** 03/09/2026

---

# Remerciements

[À compléter — paragraphe de remerciements. Modèle indicatif à adapter :]

*Je tiens à remercier [Nom de l'encadrant en entreprise], pour son encadrement, sa disponibilité et les conseils apportés tout au long de ce stage au sein de Yonnov'IA. Je remercie également [Nom de l'encadrant académique] pour son suivi pédagogique et ses retours sur l'avancement du projet. Mes remerciements vont aussi à l'ensemble de l'équipe projet — [Firas Foued, Karim Moalla, Khouloud Cherif] — pour la collaboration et l'entraide tout au long du développement de ce pipeline. Enfin, je remercie [établissement / jury] de m'avoir donné l'opportunité de réaliser ce stage.*

---

# Résumé

Ce rapport présente le travail réalisé dans le cadre d'un stage au sein de Yonnov'IA, portant sur la conception et le développement d'un pipeline d'intelligence artificielle capable de traiter automatiquement des articles scientifiques au format PDF : extraction du texte, évaluation et amélioration de la qualité d'extraction, nettoyage et structuration linguistique du contenu, génération d'un résumé scientifique structuré à l'aide d'un modèle de langage exécuté localement, et mise à disposition de l'ensemble via une application web complète avec historique et exports.

Le projet a été découpé en quatre phases correspondant chacune à un sprint de développement : l'ingestion et l'extraction des documents PDF (Phase 2), la préparation linguistique du texte extrait (Phase 3), la génération du résumé par un modèle de langage (Phase 4), et l'interface web permettant de piloter l'ensemble du pipeline (Phase 5). Chacune de ces phases a fait l'objet d'une implémentation complète, documentée en détail dans quatre documents techniques distincts, et synthétisée dans ce rapport.

Au-delà de la description fonctionnelle du système, ce rapport adopte une démarche d'analyse critique : chaque composant est confronté à son implémentation réelle, ce qui permet d'identifier précisément ce qui fonctionne, ce qui reste partiel (comme l'intégration de l'OCR ou du contrôle qualité automatique du résumé), et les axes d'amélioration à prioriser pour la suite du projet.

**Mots-clés :** extraction de documents PDF, traitement automatique du langage naturel, modèles de langage, résumé automatique, FastAPI, React, PostgreSQL.

---

# Table des matières

*(remplacée par une table des matières calculée sur la pagination réelle lors de la génération du document)*

---

# Liste des figures

---

# Liste des tableaux

---

# Liste des acronymes

---

# Introduction générale

Les articles scientifiques constituent une source d'information dense, longue et difficile à parcourir rapidement, en particulier lorsqu'il s'agit d'évaluer si un document mérite une lecture approfondie. Cette difficulté s'accentue lorsque les documents proviennent de sources hétérogènes : certains sont des exports natifs depuis LaTeX ou Word, directement exploitables, tandis que d'autres sont des numérisations, pour lesquelles aucun texte n'est directement accessible sans une étape de reconnaissance optique de caractères. Automatiser la lecture, la structuration et la synthèse de ce type de documents représente donc un problème technique à plusieurs facettes, qui ne se limite pas à l'appel d'un modèle de langage : il faut d'abord garantir que le texte fourni à ce modèle est fiable, complet et correctement organisé.

C'est dans ce contexte que s'inscrit le projet Yonnov'IA, dont l'objectif est de concevoir un pipeline complet transformant un PDF scientifique brut en une synthèse structurée, exploitable et vérifiable. Le projet a été mené selon une démarche itérative, découpée en sprints successifs, chacun correspondant à une étape fonctionnelle du pipeline : l'extraction du contenu, sa préparation linguistique, la génération du résumé, puis la mise à disposition du résultat via une interface web.

Ce rapport rend compte de l'ensemble de ce travail. Il s'ouvre par une présentation de l'organisme d'accueil, avant d'exposer, dans un premier chapitre, la motivation, le périmètre et la méthodologie retenus pour le projet. Un deuxième chapitre de contexte théorique revient ensuite sur les concepts mobilisés — extraction documentaire, traitement automatique du langage, modèles de langage, architecture web — avant qu'un troisième chapitre ne détaille la conception du système et la pile technologique retenue, puis qu'un quatrième ne présente l'implémentation effective, phase par phase. Le rapport se conclut par un bilan critique du travail accompli et par les perspectives d'évolution identifiées pour la suite du projet.

---

# Présentation de l'organisme d'accueil

[À compléter — présentation de l'entreprise/l'organisation Yonnov'IA : secteur d'activité, mission, positionnement, année de création, taille de l'équipe, principaux produits ou services. Exemple de structure à suivre : *Yonnov'IA est [statut juridique / structure] spécialisée dans [domaine]. Fondée en [année], l'organisation se positionne sur [marché/problématique] et développe [produits/services]. L'équipe compte actuellement [nombre] personnes réparties entre [pôles/rôles].*]

[À compléter — contexte du stage : dans quelle équipe/pôle le stage s'est déroulé, qui étaient les autres membres du projet (Firas Foued, Karim Moalla, Khouloud Cherif — à confirmer/compléter), quel était le rôle spécifique de l'étudiant·e au sein de cette équipe, durée et modalités du stage (présentiel/distanciel).]

---

# Chapitre 1 — Introduction

## 1.1 Motivation

La lecture manuelle d'articles scientifiques pour en extraire les éléments essentiels — problématique, méthodologie, résultats, limites — est une tâche chronophage, répétitive, et dont la qualité dépend fortement de l'attention du lecteur. Cette charge devient particulièrement lourde pour toute personne devant effectuer une veille scientifique régulière ou traiter un volume important de documents dans un temps contraint. L'essor récent des modèles de langage a rendu envisageable une automatisation partielle de cette tâche, à condition toutefois de résoudre un problème préalable souvent sous-estimé : un modèle de langage ne peut produire un résumé fiable que s'il reçoit en entrée un texte lui-même fiable, correctement extrait et débarrassé du bruit inhérent à la conversion d'un PDF en texte brut.

C'est cette double exigence — fiabilité de l'extraction et qualité du résumé généré — qui a motivé la conception d'un pipeline complet plutôt qu'un simple appel direct à un modèle de langage sur le contenu brut d'un PDF. Le projet Yonnov'IA a ainsi été pensé comme une chaîne de traitement où chaque étape prépare et sécurise la suivante, plutôt que comme un unique composant monolithique.

## 1.2 Périmètre

Le périmètre du projet a été défini autour de quatre grandes capacités fonctionnelles, correspondant chacune à une phase de développement distincte :

1. **L'ingestion et l'extraction** de documents PDF, qu'ils soient nativement textuels ou scannés, avec une évaluation automatique de la qualité de l'extraction et un mécanisme de secours en cas d'échec.
2. **La préparation linguistique** du texte extrait : nettoyage, détection des sections scientifiques, extraction des métadonnées bibliographiques et des mots-clés, puis découpage du contenu en segments adaptés à la fenêtre de contexte d'un modèle de langage.
3. **La génération du résumé** lui-même, structuré selon un gabarit fixe (sujet, problématique, méthodologie, résultats, contributions, limites, perspectives), produit par un modèle de langage exécuté localement, avec des mécanismes de repli en cas d'indisponibilité du modèle.
4. **L'exposition du pipeline via une interface web**, permettant à un utilisateur sans connaissance technique d'importer un document, de suivre son traitement, de consulter les résultats et de les exporter, tout en conservant un historique des traitements effectués.

Ce périmètre exclut volontairement, au stade actuel du projet, l'authentification multi-utilisateurs, le traitement de documents autres que des PDF, et l'entraînement d'un modèle de langage spécifique au domaine scientifique — le projet s'appuie sur des modèles pré-entraînés génériques, exécutés localement.

## 1.3 Méthodologie

Le développement a suivi une démarche itérative et incrémentale, structurée en sprints correspondant chacun à une phase fonctionnelle du pipeline. Cette organisation a permis de valider progressivement chaque brique du système avant de construire la suivante : la Phase 3 (préparation linguistique) ne pouvait être développée et testée de façon pertinente qu'une fois la Phase 2 (extraction) suffisamment stable pour produire un texte exploitable, et il en va de même pour l'enchaînement entre la Phase 3 et la Phase 4 (génération du résumé).

Chaque phase a fait l'objet d'un cahier des charges détaillé, décrivant les tâches attendues, les livrables et les critères d'acceptation. Le travail d'implémentation a ensuite été confronté systématiquement à ces critères, plutôt que documenté a posteriori de façon déclarative : cette démarche de vérification — relire le code réellement exécuté, reproduire les scénarios d'échec, mesurer les temps de traitement plutôt que les estimer — a permis d'identifier plusieurs écarts entre ce que le cahier des charges demandait et ce que l'implémentation fournissait effectivement (l'intégration de l'OCR ou du contrôle qualité automatique du résumé, par exemple, cf. Chapitre 4). Cette exigence de vérification constitue un principe méthodologique central de ce rapport : chaque affirmation technique qu'il contient a été vérifiée directement dans le code source du projet plutôt que supposée à partir des spécifications initiales.

Le travail d'équipe s'est appuyé sur Git et GitHub, avec un développement organisé par branches individuelles intégrées à la branche principale via des pull requests (détaillé en section 4.1). La documentation technique a été produite en parallèle du développement, sous la forme de quatre documents distincts correspondant chacun à une phase du projet, dont ce rapport constitue la synthèse.

---

# Chapitre 2 — Contexte théorique

## 2.1 Extraction et traitement de documents PDF

Le format PDF (*Portable Document Format*) a été conçu pour garantir la fidélité de la mise en page d'un document indépendamment du logiciel ou du système utilisé pour l'afficher. Cette priorité donnée à la mise en page a une conséquence directe sur l'extraction automatique de texte : un PDF ne contient pas nécessairement une structure logique explicite (paragraphes, titres, ordre de lecture), mais une collection d'objets positionnés dans l'espace de la page — blocs de texte, images, tracés vectoriels. Extraire le « texte » d'un PDF revient donc à reconstruire, à partir de ces objets, une séquence de caractères cohérente avec l'ordre de lecture attendu par un humain, ce qui devient particulièrement délicat sur des mises en page complexes telles que les articles scientifiques à deux colonnes.

On distingue classiquement deux grandes familles de PDF du point de vue de l'extraction. Les PDF dits **natifs** contiennent une couche de texte réelle, généralement produite par un traitement de texte ou un moteur de composition comme LaTeX : chaque caractère affiché correspond à un caractère encodé, directement récupérable par une bibliothèque d'extraction sans traitement d'image. Les PDF **scannés**, à l'inverse, ne contiennent qu'une image de chaque page, sans aucune couche de texte sous-jacente ; en extraire le contenu textuel nécessite un traitement d'OCR (*Optical Character Recognition*, reconnaissance optique de caractères), qui identifie les formes correspondant à des caractères dans l'image et les convertit en texte encodé. Entre ces deux cas extrêmes existent des situations intermédiaires — documents partiellement scannés, ou dont la couche texte est présente mais corrompue — qui imposent de mettre en place un mécanisme de détection capable d'orienter automatiquement le document vers la stratégie d'extraction appropriée, plutôt que de supposer a priori sa nature.

## 2.2 Traitement automatique du langage naturel

Une fois le texte extrait, celui-ci reste rarement directement exploitable par un système automatisé : il contient du bruit structurel hérité de la mise en page d'origine (numéros de page, en-têtes et pieds de page répétés sur chaque page, mots coupés en fin de ligne par une césure typographique) qui doit être éliminé avant toute analyse plus poussée. Cette étape de nettoyage relève du traitement automatique du langage naturel (NLP, *Natural Language Processing*), discipline qui regroupe l'ensemble des techniques permettant à un système informatique d'analyser, de transformer ou de générer du texte en langue naturelle.

Au-delà du nettoyage, deux tâches de NLP jouent un rôle central dans ce projet. La première est la **segmentation en sections**, qui consiste à repérer, au sein d'un texte continu, les frontières correspondant aux sections logiques d'un article scientifique (résumé, introduction, méthodologie, résultats, conclusion) — une tâche rendue plus complexe par l'absence de balisage explicite dans le texte extrait, et par la variabilité des conventions de nommage selon les revues, les auteurs et la langue de rédaction. La seconde est l'**extraction de mots-clés**, qui vise à identifier automatiquement les termes les plus représentatifs du contenu d'un document. Une approche classique et peu coûteuse en ressources pour cette tâche est la méthode **TF-IDF** (*Term Frequency – Inverse Document Frequency*), qui attribue à chaque terme un score proportionnel à sa fréquence dans le document analysé, mais inversement proportionnel à sa fréquence générale dans un corpus de référence : un terme très fréquent dans un seul segment de texte mais rare ailleurs obtient ainsi un score élevé, ce qui permet de distinguer les termes réellement discriminants des mots grammaticaux ou génériques.

## 2.3 Modèles de langage et inférence locale

Les modèles de langage (LLM, *Large Language Models*) sont des réseaux de neurones entraînés sur de très grands volumes de texte, capables de générer du texte cohérent en prédisant, de façon itérative, le mot ou fragment de mot le plus probable étant donné le contexte qui le précède. Appliqués à la synthèse de documents, ces modèles permettent de produire un résumé qui ne se contente pas d'extraire des phrases existantes (résumé dit *extractif*), mais qui reformule et condense l'information de façon plus proche d'une synthèse rédigée par un humain (résumé dit *abstractif*).

L'utilisation de tels modèles pose cependant deux difficultés majeures. La première est le risque d'**hallucination** : un modèle de langage génère du texte statistiquement plausible, sans garantie intrinsèque de fidélité au document source, et peut donc produire des affirmations qui semblent crédibles sans être réellement fondées sur le texte fourni en entrée. La seconde est la **fenêtre de contexte**, c'est-à-dire la quantité maximale de texte qu'un modèle peut prendre en compte simultanément pour générer sa réponse : un article scientifique complet dépasse fréquemment cette limite, ce qui impose de découper le texte en segments traités séparément, avant de fusionner les résultats intermédiaires.

Le projet a fait le choix d'une **inférence locale**, c'est-à-dire l'exécution du modèle de langage directement sur l'infrastructure du projet plutôt que via une API cloud tierce, au moyen d'Ollama, un outil qui simplifie le déploiement et l'exécution de modèles de langage open-source sur une machine locale. Ce choix répond à des considérations de confidentialité des documents traités, de maîtrise des coûts d'exploitation, et d'indépendance vis-à-vis d'un fournisseur externe, au prix d'une dépendance aux ressources de calcul (notamment la mémoire vidéo disponible) de la machine hôte.

## 2.4 Génération de résumés automatiques et prompting

La qualité d'un résumé généré par un modèle de langage dépend très largement de la façon dont la requête qui lui est adressée — le **prompt** — est formulée. Le *prompt engineering*, ou conception de prompts, désigne l'ensemble des techniques consistant à structurer cette requête de façon à orienter le comportement du modèle vers le résultat attendu : imposer une structure de sortie précise, formuler des règles explicites contre l'invention d'informations, fournir des exemples du format attendu, ou encore distinguer clairement les instructions du contenu à traiter.

Dans le cadre d'une synthèse scientifique, ces techniques sont particulièrement importantes pour limiter le risque d'hallucination évoqué en section 2.3 : demander explicitement au modèle d'indiquer qu'une information est absente plutôt que de la déduire, imposer une structure de sortie fixe pour faciliter la vérification automatique du résultat, ou encore exiger une attribution précise pour toute valeur numérique rapportée (à quelle entité, quelle métrique, quelle configuration expérimentale elle se rattache), sont autant de contraintes qui réduisent — sans l'éliminer complètement — le risque de production d'un contenu non fondé sur le document source.

## 2.5 Architecture web et API REST

Une architecture web moderne distingue généralement deux composants communiquant via un réseau : un **frontend**, exécuté dans le navigateur de l'utilisateur et responsable de l'interface graphique, et un **backend**, exécuté sur un serveur et responsable du traitement des données et de la logique métier. Cette séparation permet de faire évoluer indépendamment l'interface et les traitements qu'elle déclenche, et facilite la réutilisation du backend par d'autres clients qu'une interface web (application mobile, script d'automatisation).

La communication entre ces deux composants s'appuie fréquemment sur une **API REST** (*Representational State Transfer*), un style d'architecture pour les services web qui organise les échanges autour de ressources identifiées par une URL et manipulées via les méthodes standard du protocole HTTP (`GET` pour consulter, `POST` pour créer, `DELETE` pour supprimer). FastAPI, le framework retenu pour le backend de ce projet, permet de définir ce type d'API en Python tout en générant automatiquement la validation des données échangées et une documentation interactive du service, à partir des types déclarés dans le code.

## 2.6 Bases de données relationnelles et persistance

Une base de données relationnelle organise l'information sous forme de tables reliées entre elles par des clés, garantissant la cohérence des données par un ensemble de contraintes (unicité, intégrité référentielle) et l'atomicité des opérations qui les modifient. PostgreSQL, le système de gestion de base de données retenu pour ce projet, appartient à cette famille et permet de conserver, de façon durable et interrogeable, l'historique des documents traités et de chaque exécution du pipeline.

Plutôt que d'écrire directement des requêtes SQL, le projet s'appuie sur SQLAlchemy, un *ORM* (*Object-Relational Mapper*) qui permet de manipuler les données sous forme d'objets Python, ainsi que sur Alembic, un outil de gestion des migrations qui permet de faire évoluer la structure de la base de données de façon versionnée et reproductible, à mesure que de nouveaux besoins de persistance apparaissent au fil du projet.

## 2.7 Interfaces web modernes

Le développement d'interfaces web s'appuie aujourd'hui largement sur des bibliothèques permettant de construire l'interface comme une composition de **composants** réutilisables, dont l'affichage se met à jour automatiquement en fonction de l'état de l'application, plutôt que par manipulation manuelle du contenu de la page. React, la bibliothèque retenue pour le frontend de ce projet, repose sur ce principe : chaque écran de l'application (import d'un document, suivi du traitement, consultation du résumé) est modélisé comme un composant recevant des données en entrée et produisant l'affichage correspondant, ce qui facilite la maintenance et l'évolution de l'interface à mesure que de nouvelles fonctionnalités sont ajoutées.

---

# Chapitre 3 — Conception du système et pile technologique

## 3.1 Vue d'ensemble de l'application

Yonnov'IA est un pipeline de traitement automatique qui transforme un article scientifique déposé au format PDF en une synthèse structurée, sans que l'utilisateur ait à configurer ou orchestrer lui-même les différents outils de traitement du langage et d'inférence sous-jacents. Un utilisateur dépose un document depuis l'interface web ; le backend le stocke, l'enregistre en base de données, puis exécute successivement l'extraction du texte, l'évaluation optionnelle de sa qualité, le nettoyage et la structuration linguistique, l'extraction des métadonnées et des mots-clés, le découpage en segments, puis la génération du résumé par un modèle de langage exécuté localement via Ollama. Le résumé final, produit par fusion des résumés partiels de chaque segment, est ensuite consultable depuis l'interface et exportable aux formats Markdown, JSON ou PDF ; chaque traitement reste par ailleurs retrouvable dans un historique persistant.

Le principe de conception central de cette version de l'application est la simplicité du modèle d'exécution : l'ensemble du pipeline s'exécute de façon synchrone, à l'intérieur d'un unique appel HTTP bloquant, sans file d'attente de tâches ni notification en temps réel — la barre de progression affichée à l'utilisateur pendant le traitement est une simulation côté client plutôt qu'un reflet de l'avancement réel du backend. Ce choix simplifie considérablement le raisonnement sur les erreurs et l'implémentation initiale, au prix d'un temps de réponse perceptible pour l'utilisateur, en particulier sur un document volumineux ou lorsque le modèle de langage est sollicité sur de nombreux segments. De la même façon, l'application ne dispose aujourd'hui d'aucune authentification ni d'aucune isolation des données par utilisateur : il s'agit d'un système mono-tenant, où toute donnée est visible par tout appelant de l'API — un choix cohérent avec le périmètre actuel du projet, mais qui constitue une limite explicite à garder à l'esprit pour toute évolution vers un usage multi-utilisateurs.

L'application cible en priorité un usage individuel de veille scientifique : un utilisateur souhaitant obtenir rapidement une première synthèse fiable d'un article — sujet, méthodologie, résultats, limites — sans avoir à lire l'intégralité du document ni à interagir directement avec un modèle de langage.

## 3.2 Analyse des besoins

### 3.2.1 Exigences fonctionnelles

Les exigences fonctionnelles ci-dessous ont été établies à partir des routes effectivement exposées par le backend (`backend/app/main.py` et les routeurs associés) et des écrans réellement implémentés dans le frontend, plutôt que reconstruites à partir du seul cahier des charges initial.

| ID | Exigence |
|---|---|
| EF-1 | Un utilisateur peut téléverser un document PDF, avec validation de l'extension et du nom de fichier (`POST /upload`). |
| EF-2 | Un utilisateur peut lancer le traitement complet du pipeline sur un document téléversé et recevoir le résumé structuré une fois l'ensemble des étapes terminées (`POST /summarize`). |
| EF-3 | Le système peut, si l'option est activée, évaluer la qualité de l'extraction du texte à l'aide d'un modèle de langage juge. |
| EF-4 | Un utilisateur peut consulter la liste des documents ayant fait l'objet d'au moins un traitement (`GET /documents`). |
| EF-5 | Un utilisateur peut consulter la liste des exécutions du pipeline, globalement ou pour un document donné (`GET /pipeline-runs`, `GET /documents/{id}/pipeline-runs`). |
| EF-6 | Un utilisateur peut consulter le détail complet d'une exécution — extraction, prétraitement, inférence, résumé (`GET /pipeline-runs/{id}`). |
| EF-7 | Un utilisateur peut supprimer un document et l'ensemble des données associées : exécutions, fichiers stockés (`DELETE /documents/{id}`). |
| EF-8 | Un utilisateur peut supprimer une exécution de pipeline individuelle (`DELETE /pipeline-runs/{id}`). |
| EF-9 | Un utilisateur peut consulter le résumé structuré généré pour un document, avec ses métadonnées et ses mots-clés (`GET /summary/{filename}`). |
| EF-10 | Un utilisateur peut exporter le résumé au format Markdown, JSON ou PDF (`GET /summary/{filename}/markdown`, `/json`, `/pdf`). |
| EF-11 | Le système expose un point de contrôle de disponibilité du service (`GET /health`). |

### 3.2.2 Exigences non fonctionnelles

| ID | Catégorie | Exigence |
|---|---|---|
| ENF-1 | Fiabilité | Si l'appel au modèle de langage échoue pour un segment de texte, le système bascule automatiquement vers un résumé extractif déterministe pour ce segment plutôt que d'interrompre le traitement. |
| ENF-2 | Fiabilité | Si la fusion finale par le modèle de langage échoue, le système bascule vers un résumé extractif final complet plutôt que de renvoyer une erreur. |
| ENF-3 | Traçabilité | Le nombre de segments ayant basculé vers le mode de secours est conservé pour chaque exécution du pipeline. |
| ENF-4 | Confidentialité | Les chemins de fichiers internes du serveur sont systématiquement retirés des réponses de l'API avant transmission au client. |
| ENF-5 | Configurabilité | Le contrôle qualité de l'extraction par un modèle de langage juge est activable ou désactivable par variable d'environnement, désactivé par défaut afin de limiter le temps de traitement. |
| ENF-6 | Testabilité | Une suite de tests automatisés (pytest) couvre les règles de garde du résumé — présence des sections obligatoires, respect des règles d'attribution numérique — sans constituer à ce stade une suite d'intégration complète de l'API. |
| ENF-7 | Isolation des données | Non satisfaite à ce stade : le système ne dispose d'aucune authentification ni d'aucun cloisonnement des données par utilisateur. |
| ENF-8 | Performance perçue | Le traitement d'un document s'exécute de façon synchrone dans un unique appel HTTP bloquant, sans file d'attente ni canal de notification en temps réel. |
| ENF-9 | Robustesse des entrées | La limite de taille de fichier (50 Mo) n'est aujourd'hui appliquée que côté interface web ; elle n'est pas revérifiée côté serveur. |
| ENF-10 | Intégration continue | Absente à ce stade : aucun workflow d'intégration continue n'est configuré dans le dépôt du projet. |

## 3.3 Conception du système

### 3.3.1 Architecture du système

L'architecture retenue s'organise en trois couches. Le **frontend** est une application React à page unique qui communique avec le backend exclusivement par des appels REST classiques, sans canal temps réel. Le **backend API**, construit avec FastAPI, porte l'authentification des requêtes HTTP standards, la persistance des données et l'exposition des routes ; il invoque directement, dans son propre processus, l'orchestrateur du pipeline plutôt que de déléguer le traitement à un service ou une file de tâches séparée — une conséquence directe du modèle d'exécution synchrone décrit en section 3.1. L'**orchestrateur du pipeline** (`DocumentPipeline`) séquence enfin les étapes de traitement proprement dites — extraction, prétraitement linguistique, inférence, fusion du résumé — en s'appuyant sur des modules dédiés à chacune de ces responsabilités, et en persistant à chaque étape un instantané du résultat produit.

Cette organisation modulaire présente l'avantage de circonscrire la complexité de chaque étape à son propre module, mais introduit en contrepartie un couplage fort entre les phases au niveau de l'orchestration : l'extraction, la préparation linguistique et la génération du résumé s'exécutent aujourd'hui comme une seule opération indivisible du point de vue de l'API, sans point d'arrêt intermédiaire permettant, par exemple, de consulter le texte extrait avant de lancer la génération du résumé. Ce choix, ses conséquences concrètes et les pistes d'évolution envisageables sont détaillés au Chapitre 4.

### 3.3.2 Identification des acteurs

| Acteur | Type | Description |
|---|---|---|
| Utilisateur | Acteur humain | Téléverse un document, déclenche son traitement, consulte l'historique et le résumé produit, exporte les résultats, supprime des données. |
| Orchestrateur du pipeline | Acteur système | Séquence l'extraction, le prétraitement linguistique, l'inférence et la fusion du résumé pour chaque document soumis. |
| Ollama (serveur LLM local) | Système externe | Exécute localement le modèle de langage sollicité pour la génération des résumés partiels, la fusion finale, et l'évaluation optionnelle de la qualité d'extraction. |
| Base de données PostgreSQL | Système externe | Persiste les documents, les exécutions du pipeline et l'historique des traitements. |

### 3.3.3 Diagramme de cas d'utilisation

Le diagramme de cas d'utilisation représente un unique acteur humain (l'utilisateur) interagissant avec les cas d'utilisation exposés par le système : téléverser un document, lancer un traitement, consulter l'historique, consulter un résumé, exporter un résumé, supprimer un document ou une exécution. Aucun de ces cas d'utilisation ne dépend d'un rôle ou d'une permission particulière, conformément à l'absence d'authentification constatée en ENF-7.

*[Figure 3.1 — Diagramme de cas d'utilisation, à insérer]*

### 3.3.4 Diagramme de classes

Le diagramme de classes reflète le modèle de données persisté (`backend/app/db/models.py`) : un `Document` est associé à une ou plusieurs `PipelineRun`, chacune reliée à un `ExtractionResult`, un `PreprocessingResult`, un `InferenceRun` et une `Summary`, dans une relation en chaîne qui reproduit fidèlement les étapes du pipeline décrites en section 3.3.1.

*[Figure 3.2 — Diagramme de classes, à insérer]*

### 3.3.5 Diagramme de séquence

Le diagramme de séquence trace le cycle complet d'une requête de traitement : dépôt du fichier par l'utilisateur, création du document en base, appel bloquant au pipeline, exécution séquentielle de l'extraction, du prétraitement, de l'inférence et de la fusion, persistance du résultat, puis retour de la réponse au frontend. Ce tracé met en évidence le caractère strictement synchrone du traitement évoqué en section 3.1 : aucune réponse intermédiaire n'est renvoyée à l'utilisateur avant l'achèvement complet du pipeline.

*[Figure 3.3 — Diagramme de séquence, à insérer]*

## 3.4 Pile technologique

### 3.4.1 Backend

| Composant | Technologie |
|---|---|
| Langage | Python |
| Framework web | FastAPI |
| Serveur ASGI | Uvicorn |
| Validation / sérialisation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Pilote base de données | psycopg2-binary (PostgreSQL) |
| Tests | pytest |

### 3.4.2 Frontend

| Composant | Technologie |
|---|---|
| Bibliothèque UI | React 18 |
| Langage | JavaScript (JSX) |
| Outil de build | Vite |
| Rendu Markdown | react-markdown |
| Icônes | lucide-react |
| Style | CSS classique, polices Fontsource (DM Sans, Manrope) |
| Linting | ESLint 9 |

### 3.4.3 Bases de données

| Système | Rôle |
|---|---|
| PostgreSQL | Base de données relationnelle unique du projet — persistance des documents, des exécutions et des résultats du pipeline. Le projet ne dispose d'aucune base de données vectorielle. |

### 3.4.4 Traitement et intelligence artificielle

| Composant | Technologie | Rôle |
|---|---|---|
| Extraction PDF | PyMuPDF (`fitz`) | Lecture du contenu textuel des PDF nativement textuels |
| OCR (secours) | Docling (point d'intégration présent, non implémenté) | Prévu pour les documents scannés ; retourne aujourd'hui un contenu vide |
| Extraction de mots-clés | scikit-learn (TF-IDF) | Extraction statistique des termes représentatifs du document |
| NLP complémentaire | spaCy (optionnel) | Reconnaissance d'entités nommées en dernier recours pour les métadonnées |
| Inférence LLM | Ollama (`qwen2.5:3b` par défaut) | Génération des résumés partiels et fusion du résumé final |
| Évaluation qualité (optionnelle) | Ollama (`qwen2.5vl:7b`, modèle juge) | Évaluation de la qualité d'extraction, désactivée par défaut |
| Export PDF | ReportLab | Génération du résumé final au format PDF |

Ce choix technologique privilégie systématiquement des solutions open-source, exécutables localement, plutôt que des services cloud propriétaires — un fil directeur cohérent avec l'objectif de maîtrise des coûts et de confidentialité des documents traités évoqué au Chapitre 2. Un second moteur d'inférence (vLLM) est présent dans le code sous forme de point d'extension, mais n'est pas encore implémenté à ce stade du projet.

---

# Chapitre 4 — Implémentation

## Introduction

Ce chapitre présente l'implémentation effective du pipeline, phase par phase, en s'appuyant sur les quatre documents techniques produits en parallèle du développement (`Documentation_Phase_2.md` à `_5.md`), auxquels le lecteur est invité à se référer pour le détail exhaustif de chaque tâche, des tests associés et des critères d'acceptation. Ce chapitre en propose une synthèse narrative, centrée sur les choix de conception les plus structurants et sur les écarts significatifs identifiés entre le cahier des charges et le comportement réel du système.

## 4.1 Workflow Git

Le développement s'est organisé autour d'un dépôt Git hébergé sur GitHub, avec une branche principale (`main`) protégée, et une branche de travail par contributeur, intégrée à `main` par l'intermédiaire de pull requests. Cette organisation a permis à plusieurs membres de l'équipe de faire progresser des parties distinctes du pipeline en parallèle — extraction, persistance en base de données, interface web — avant de fusionner régulièrement leur travail dans la branche principale, au prix de conflits de fusion ponctuels sur les fichiers partagés (notamment l'orchestrateur central du pipeline), résolus au fil de l'avancement du projet.

## 4.2 Upload, extraction et OCR (Phase 2)

La première phase du pipeline construit son point d'entrée : un endpoint d'upload valide et stocke le fichier PDF déposé par l'utilisateur, lui attribue un identifiant unique, et crée l'enregistrement correspondant en base de données. L'extraction du texte s'appuie sur PyMuPDF pour les documents disposant d'une couche de texte native, avec un mécanisme de détection destiné à orienter les documents insuffisamment extraits vers une stratégie de secours par OCR.

C'est précisément sur ce mécanisme de secours que porte l'écart le plus significatif identifié pour cette phase : au moment de la rédaction de ce rapport, le connecteur OCR (Docling) est un module présent dans le code mais volontairement non implémenté, qui retourne systématiquement un contenu vide plutôt que d'effectuer une reconnaissance de caractères. Un document entièrement scanné produit donc, à ce stade du projet, une sortie vide plutôt qu'un texte exploitable — un comportement qui doit être rendu explicite auprès de l'utilisateur plutôt que de rester silencieux, en attendant l'implémentation effective de cette capacité. La documentation technique correspondante (`Documentation_Phase_2.md`) détaille par ailleurs une évaluation optionnelle de la qualité d'extraction par un modèle de vision, ainsi qu'une limite de taille de fichier encore absente côté serveur.

## 4.3 Nettoyage, segmentation et extraction d'informations (Phase 3)

La troisième phase prend en charge le texte brut produit par l'extraction et le transforme en données structurées et calibrées pour le modèle de langage. Le nettoyage élimine les numéros de page et le bruit résiduel de l'extraction, fusionne les mots coupés par une césure typographique, et — dans une moindre mesure actuellement — retire les en-têtes et pieds de page répétés sur chaque page. La détection de sections s'appuie sur un dictionnaire de motifs bilingues (français/anglais) permettant de reconnaître les titres scientifiques usuels (résumé, introduction, méthodologie, résultats), avec un repli sur l'intégralité du texte lorsqu'aucune section n'est reconnue.

L'extraction des métadonnées bibliographiques (titre, auteurs, année, source, DOI) combine plusieurs sources par ordre de priorité — métadonnées internes du PDF, position du texte par rapport au titre, puis reconnaissance d'entités nommées en dernier recours — de façon à ne jamais bloquer la suite du traitement lorsqu'un champ reste introuvable. L'extraction de mots-clés repose sur une combinaison des mots-clés explicitement fournis par les auteurs, lorsqu'ils existent, et d'une extraction statistique par TF-IDF, filtrée pour exclure les termes trop génériques. Enfin, le texte est découpé en segments de taille contrôlée, avec un recouvrement entre segments consécutifs destiné à limiter la perte de contexte à la frontière d'une coupure, avant d'être assemblé avec les prompts qui seront transmis au modèle de langage en Phase 4.

## 4.4 Résumé automatique structuré (Phase 4)

La génération du résumé constitue la seule étape du pipeline invoquant effectivement un modèle de langage. Chaque segment de texte fait l'objet d'un résumé partiel indépendant, avant qu'un unique appel de fusion ne combine l'ensemble de ces résumés partiels en un document final structuré selon un gabarit fixe de douze sections (sujet, problématique, objectifs, méthodologie, résultats, contributions, limites, perspectives, mots-clés, résumé exécutif, points à retenir), décliné en français ou en anglais selon la langue détectée du document source.

La fiabilité de cette étape repose sur deux mécanismes complémentaires. D'une part, des règles de prompt strictes imposent au modèle de signaler explicitement l'absence d'une information plutôt que de l'inventer, et exigent une attribution complète pour toute valeur numérique rapportée. D'autre part, un mécanisme de repli en cascade — au niveau de chaque segment, puis au niveau de la fusion finale — bascule automatiquement vers un résumé extractif déterministe, produit sans appel au modèle de langage, lorsque celui-ci est indisponible ou échoue, garantissant qu'un résultat reste toujours produit plutôt que de faire échouer intégralement la requête.

Le cahier des charges prévoyait par ailleurs un module de contrôle qualité automatique du résumé généré, comparant systématiquement le résumé produit au contenu source pour détecter d'éventuelles informations non fondées. Ce module existe dans le code sous une forme complète et fonctionnelle — un second modèle de langage joue le rôle de juge, évalue chaque section du résumé et produit une décision d'acceptation ou de rejet — mais n'est, au moment de la rédaction de ce rapport, appelé par aucune autre partie de l'application : aucun score de qualité n'est donc actuellement calculé en usage normal. Il s'agit du principal point à finaliser pour clore complètement le périmètre initialement défini pour cette phase.

## 4.5 Interface web et exports (Phase 5)

L'interface web assemble l'ensemble du pipeline en une application React à page unique, organisée autour d'un parcours simple : import du document, suivi du traitement, consultation du résumé structuré et des mots-clés, puis export au format Markdown, JSON ou PDF. Un écran d'historique, connecté à la base de données plutôt qu'au système de fichiers, permet de retrouver les documents précédemment traités et de consulter le détail de chaque exécution passée, avec la possibilité de supprimer une exécution isolée ou un document dans son intégralité.

Cette interface expose cependant deux composants de données distincts et non unifiés : les écrans de consultation du résumé s'appuient sur des fichiers générés sur le système de fichiers du serveur, tandis que l'écran d'historique s'appuie sur la base de données relationnelle. Cette dualité, héritée de l'évolution du projet — la persistance en base de données ayant été ajoutée après les premières routes de consultation du résumé — constitue une dette d'architecture identifiée pour une prochaine itération. Par ailleurs, l'écran nommé « Texte extrait », destiné à afficher le texte brut et les sections réellement détectées par la Phase 3, affiche en réalité le résumé final de la Phase 4 sous un autre habillage : les données attendues par cet écran existent bien côté serveur, mais ne sont pas encore connectées à l'interface correspondante.

## 4.6 Tests et intégration continue

La fiabilité du pipeline, en particulier des règles de fidélité imposées au modèle de langage (Phase 4), est vérifiée par une suite de tests automatisés écrite avec pytest, couvrant notamment la présence systématique des sections obligatoires du résumé, le respect des règles d'attribution numérique dans les prompts de fusion, et la récupération correcte des métadonnées lorsque certaines d'entre elles sont absentes du document source. Ces tests s'exécutent localement, via la commande `pytest`, et n'ont pas encore été intégrés à un pipeline d'intégration continue automatisé (aucune configuration GitHub Actions n'est présente dans le dépôt à ce stade du projet) : leur exécution avant fusion d'une branche repose aujourd'hui sur la discipline individuelle des contributeurs plutôt que sur une vérification automatique déclenchée à chaque contribution. La mise en place d'une telle intégration continue constitue une évolution naturelle et peu coûteuse à mettre en œuvre pour fiabiliser davantage le processus de fusion des contributions.

---

# Conclusion générale et perspectives

Le travail réalisé au cours de ce stage a permis de construire un pipeline complet et fonctionnel, capable de transformer un article scientifique au format PDF en une synthèse structurée, depuis l'import du document jusqu'à sa consultation et son export via une interface web. Chacune des quatre phases fonctionnelles définies au démarrage du projet — extraction, préparation linguistique, génération du résumé, interface — a été implémentée et validée sur le jeu de données de test constitué à cet effet, avec une attention particulière portée à la fiabilité du système face aux cas dégradés : document scanné, modèle de langage temporairement indisponible, métadonnées bibliographiques incomplètes.

Cette démarche de vérification systématique, confrontant le cahier des charges à l'implémentation réellement exécutée plutôt qu'à sa seule description, a également permis d'identifier avec précision les limites actuelles du système. Trois d'entre elles se distinguent par leur impact potentiel : l'absence d'implémentation effective de l'OCR pour les documents scannés, malgré la présence du point d'intégration correspondant dans le code ; l'existence d'un module de contrôle qualité du résumé complet et fonctionnel, mais non connecté au pipeline principal ; et la déconnexion de l'écran « Texte extrait » de l'interface, qui n'affiche pas aujourd'hui les données pour lesquelles il a été conçu. Ces trois points constituent, avec l'unification des deux sources de données actuellement distinctes de l'application (système de fichiers et base de données), les priorités les plus immédiates pour la poursuite du projet.

Au-delà de ces corrections, plusieurs axes d'évolution plus structurants ont été identifiés au fil du développement : la mise en place d'une fusion progressive et multi-niveaux du résumé pour les documents comportant un grand nombre de segments, afin d'éviter tout dépassement silencieux de la fenêtre de contexte du modèle de langage ; l'intégration d'une intégration continue automatisée pour fiabiliser le processus de contribution ; et, à plus long terme, l'introduction d'une authentification multi-utilisateurs, actuellement absente d'un projet conçu pour un usage mono-utilisateur. Ce projet, mené selon une démarche itérative et documentée avec un niveau d'exigence proche de celui attendu en environnement professionnel, constitue ainsi une base solide et honnêtement caractérisée sur laquelle les développements futurs pourront s'appuyer.

---

*Fin du rapport. Le détail exhaustif de chaque tâche, des algorithmes, des structures de données, des tests et des critères d'acceptation est disponible dans les quatre documents techniques `Documentation_Phase_2.md` à `Documentation_Phase_5.md`.*
