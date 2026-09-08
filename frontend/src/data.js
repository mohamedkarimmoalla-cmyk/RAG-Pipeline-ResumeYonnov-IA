export const navigation = [
  { id: 'home', label: 'Vue d’ensemble', shortLabel: 'Accueil' },
  { id: 'upload', label: 'Importer un PDF', shortLabel: 'Importer' },
  { id: 'processing', label: 'Suivi du traitement', shortLabel: 'Suivi' },
  { id: 'extraction', label: 'Texte extrait', shortLabel: 'Texte' },
  { id: 'summary', label: 'Synthèse', shortLabel: 'Synthèse' },
  { id: 'keywords', label: 'Mots-clés', shortLabel: 'Mots-clés' },
  { id: 'history', label: 'Historique', shortLabel: 'Historique' },
  { id: 'exports', label: 'Exports', shortLabel: 'Exports' },
];

export const pipelineSteps = [
  ['Validation PDF', 'Type, taille et lisibilité'],
  ['Extraction', 'Lecture et consolidation du document'],
  ['Prétraitement', 'Nettoyage, métadonnées et sections'],
  ['Mots-clés', 'Extraction des concepts scientifiques'],
  ['Découpage', 'Création des segments de traitement'],
  ['Préparation', 'Construction des requêtes d’inférence'],
  ['Inférence', 'Génération des synthèses partielles'],
  ['Synthèse finale', 'Fusion et sauvegarde des résultats'],
];
