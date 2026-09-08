import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpenText,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clipboard,
  Clock3,
  Download,
  FileJson,
  FileText,
  FolderClock,
  Gauge,
  Home,
  KeyRound,
  Menu,
  PanelLeftClose,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  Trash2,
  X,
} from 'lucide-react';
import {
  navigation,
  pipelineSteps,
} from './data';
import {
  downloadArtifact,
  downloadPdf,
  getDocumentPipelineRuns,
  getDocuments,
  getPipelineRun,
  deletePipelineRun,
  deleteDocument,
  getSummary,
  summarizePdf,
  uploadPdf,
} from './api';

const iconMap = {
  home: Home,
  upload: Upload,
  processing: Activity,
  extraction: BookOpenText,
  summary: Sparkles,
  keywords: KeyRound,
  history: FolderClock,
  exports: Download,
};

function formatBytes(bytes) {
  if (!bytes) return 'Taille indisponible';
  const mb = bytes / 1024 / 1024;
  return `${mb.toFixed(mb >= 10 ? 0 : 1)} Mo`;
}

function keywordLabel(item) {
  return typeof item === 'string' ? item : item?.keyword || '';
}

function parseSummarySections(markdown = '') {
  return markdown
    .split(/^##\s+/m)
    .slice(1)
    .map((block) => {
      const [title, ...body] = block.trim().split('\n');
      return [title.trim(), body.join('\n').replace(/^---$/gm, '').trim()];
    })
    .filter(([title, body]) => title && body);
}

function displayValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'Non disponible';
  return value ?? 'Non disponible';
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('fr-FR') : 'Non disponible';
}

function formatDuration(value) {
  return Number.isFinite(value) ? `${(value / 1000).toFixed(1)} s` : 'Non disponible';
}

function safePersistedValue(value) {
  if (Array.isArray(value)) return value.map(safePersistedValue);
  if (!value || typeof value !== 'object') return value;

  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !/(path|file_path|input pdf|output markdown)/i.test(key))
    .map(([key, item]) => [key, safePersistedValue(item)]));
}

function PersistedJson({ value }) {
  if (value === null || value === undefined) return <p className="muted">Aucune donnée disponible.</p>;
  return <pre className="persisted-json">{JSON.stringify(safePersistedValue(value), null, 2)}</pre>;
}

function Badge({ children, tone = 'teal' }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

function PageHeading({ eyebrow, title, description, action }) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action}
    </header>
  );
}

function Metric({ label, value, detail, tone = 'default', icon: Icon }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon metric-icon--${tone}`}><Icon size={18} /></div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{detail}</span>
      </div>
    </article>
  );
}

function AppShell({ page, onNavigate, onReset, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigate = (nextPage) => {
    onNavigate(nextPage);
    setMobileOpen(false);
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar--open' : ''}`}>
        <div className="brand">
          <img src="/logo.jpg" alt="YONNOVIA" />
          <div><strong>PDF Intelligence</strong><span>Workspace IA</span></div>
          <button className="icon-button sidebar-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu"><PanelLeftClose size={19} /></button>
        </div>
        <nav aria-label="Navigation principale">
          <p className="nav-label">Espace de travail</p>
          {navigation.map((item) => {
            const Icon = iconMap[item.id];
            return (
              <button
                key={item.id}
                className={`nav-item ${page === item.id ? 'nav-item--active' : ''}`}
                onClick={() => navigate(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
                {page === item.id && <ChevronRight size={16} />}
              </button>
            );
          })}
        </nav>
      </aside>

      {mobileOpen && <button className="backdrop" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)} />}

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <button className="icon-button menu-button" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu"><Menu size={20} /></button>
            <div><span>YONNOVIA</span><strong>{navigation.find((item) => item.id === page)?.label}</strong></div>
          </div>
          <div className="topbar-actions">
            <button className="button button--secondary button--compact" onClick={onReset}><Plus size={17} /> Nouveau document</button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

function HomePage({ file, processed, summaryDetail, onNavigate }) {
  const metadata = summaryDetail?.metadata || {};
  const keywordCount = summaryDetail?.keywords?.length || 0;
  return (
    <>
      <section className="hero">
        <div className="hero-content">
          <Badge tone="teal"><Sparkles size={13} /> Pipeline documentaire intelligent</Badge>
          <h1>Transformez un article scientifique en informations exploitables.</h1>
          <p>Importez un PDF, suivez chaque étape de traitement et obtenez une synthèse structurée, traçable et prête à exporter.</p>
          <div className="button-row">
            <button className="button button--primary" onClick={() => onNavigate('upload')}>Importer un PDF <ArrowRight size={17} /></button>
            <button className="button button--ghost" disabled={!processed} onClick={() => onNavigate('summary')}>Voir la synthèse</button>
          </div>
        </div>
        <div className="hero-visual">
          <div className="document-card">
            <div className="document-top"><FileText size={22} /><span>{file?.name || 'AUCUN DOCUMENT'}</span><Badge tone={processed ? 'teal' : 'slate'}>{processed ? 'Analysé' : 'En attente'}</Badge></div>
            <div className="skeleton-line skeleton-line--wide" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line--short" />
            <div className="document-insight"><Sparkles size={17} /><div><strong>{processed ? 'Synthèse générée' : 'Pipeline disponible'}</strong><span>{processed ? `${keywordCount} mots-clés détectés` : 'Importez un document'}</span></div><CheckCircle2 size={19} /></div>
          </div>
        </div>
      </section>

      <section className="metrics-grid">
        <Metric label="Document actif" value={file ? file.name : 'Aucun'} detail={file ? formatBytes(file.size) : 'Importez un PDF pour commencer'} icon={FileText} />
        <Metric label="Traitement" value={processed ? 'Terminé' : 'En attente'} detail={processed ? 'Résultats disponibles' : 'Pipeline prêt'} tone="teal" icon={Activity} />
        <Metric label="Langue détectée" value={metadata.language?.toUpperCase() || '—'} detail={processed ? 'Détection automatique' : 'En attente'} tone="purple" icon={Gauge} />
        <Metric label="Mots-clés" value={String(keywordCount)} detail={processed ? 'Concepts disponibles' : 'En attente'} tone="amber" icon={KeyRound} />
      </section>

      <section className="section-grid">
        <article className="panel panel--large">
          <PageHeading eyebrow="Pipeline" title="Un parcours clair, du PDF au résultat" description="Chaque étape expose son état pour faciliter le contrôle qualité du traitement backend." />
          <div className="flow-grid">
            {[
              [Upload, '01', 'Import sécurisé', 'Validation du format, de la taille et de la lisibilité.'],
              [BookOpenText, '02', 'Extraction structurée', 'Texte brut, nettoyage et détection des sections.'],
              [Sparkles, '03', 'Synthèse IA', 'Résumé, concepts clés et limites identifiées.'],
              [Download, '04', 'Exports prêts', 'Markdown, JSON et impression PDF.'],
            ].map(([Icon, number, title, text]) => (
              <div className="flow-step" key={title}>
                <span className="flow-number">{number}</span>
                <div className="flow-icon"><Icon size={20} /></div>
                <strong>{title}</strong><p>{text}</p>
              </div>
            ))}
          </div>
        </article>
        <aside className="panel trust-panel">
          <ShieldCheck size={27} />
          <h2>Confidentialité intégrée</h2>
          <p>Les documents sélectionnés sont transmis au backend FastAPI pour exécuter le pipeline scientifique.</p>
          <ul>
            <li><Check size={16} /> Validation par le backend</li>
            <li><Check size={16} /> Validation côté navigateur</li>
            <li><Check size={16} /> Téléchargements contrôlés par l’API</li>
          </ul>
        </aside>
      </section>

      <section className="team-section">
        <PageHeading eyebrow="Équipe projet" title="Conçu pour YONNOVIA" description="Une interface produit sobre, rapide et orientée vers la lecture scientifique." />
        <div className="team-grid">
          {[
            ['firas.jpg', 'Firas Foued', 'Développeur projet'],
            ['kmoalla.png', 'Karim Moalla', 'Développeur projet'],
            ['khouloud.png', 'Khouloud Cherif', 'Développeuse projet'],
          ].map(([photo, name, role]) => (
            <article className="team-card" key={name}><img src={`/team/${photo}`} alt={`Portrait de ${name}`} /><div><strong>{name}</strong><span>{role}</span></div></article>
          ))}
        </div>
      </section>
    </>
  );
}

function UploadPage({ files, error, uploading, onFiles, onRemove, onProcess }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const acceptFiles = (list) => {
    onFiles(Array.from(list));
    setDragging(false);
  };

  return (
    <>
      <PageHeading eyebrow="Nouveau traitement" title="Importer des articles PDF" description="Ajoutez un ou plusieurs documents. Le premier fichier importé sera utilisé pour le traitement." />
      <div className="two-column">
        <section className="panel">
          <button
            className={`dropzone ${dragging ? 'dropzone--active' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); acceptFiles(event.dataTransfer.files); }}
          >
            <span className="upload-icon"><Upload size={25} /></span>
            <strong>Déposez vos fichiers ici</strong>
            <span>ou cliquez pour parcourir vos documents</span>
            <small>PDF uniquement · 50 Mo maximum par fichier</small>
          </button>
          <input ref={inputRef} className="sr-only" type="file" accept=".pdf,application/pdf" multiple onChange={(event) => acceptFiles(event.target.files)} />

          {error && <div className="alert alert--error"><CircleAlert size={18} /><span>{error}</span></div>}

          {files.length > 0 && (
            <div className="file-list">
              <div className="list-heading"><strong>File de documents</strong><Badge>{files.length} PDF</Badge></div>
              {files.map((file, index) => (
                <div className="file-row" key={`${file.name}-${file.lastModified}`}>
                  <span className="file-icon"><FileText size={19} /></span>
                  <div><strong>{file.name}</strong><span>{formatBytes(file.size)} · {file.uploadStatus === 'uploaded' ? 'Importé' : 'Import en cours'}</span></div>
                  {index === 0 && <Badge>{file.uploadStatus === 'uploaded' ? 'Actif' : 'Envoi'}</Badge>}
                  <button className="icon-button" onClick={(event) => { event.stopPropagation(); onRemove(index); }} aria-label={`Retirer ${file.name}`}><X size={18} /></button>
                </div>
              ))}
            </div>
          )}

          <div className="panel-footer">
            <button className="button button--primary" disabled={!files.length || uploading || files[0]?.uploadStatus !== 'uploaded'} onClick={onProcess}>{uploading ? 'Import en cours…' : 'Lancer le traitement'} <ArrowRight size={17} /></button>
          </div>
        </section>
        <aside className="stack">
          <section className="panel compact-panel">
            <h2>Contrôles avant traitement</h2>
            {[
              ['Format du fichier', files.length ? 'PDF valide' : 'En attente', files.length],
              ['Taille maximale', '50 Mo par document', true],
              ['Connexion API', uploading ? 'Import en cours' : 'Backend FastAPI', true],
            ].map(([label, value, ready]) => <div className="status-row" key={label}><span>{ready ? <CheckCircle2 size={18} /> : <Clock3 size={18} />}{label}</span><strong>{value}</strong></div>)}
          </section>
          <section className="panel compact-panel privacy-card"><ShieldCheck size={23} /><h2>Traitement contrôlé</h2><p>Le document est envoyé uniquement au backend FastAPI configuré pour cette application.</p></section>
        </aside>
      </div>
    </>
  );
}

function ProcessingPage({ progress, logs, error, processingStage }) {
  const activeStep = Math.min(Math.floor((progress / 100) * pipelineSteps.length), pipelineSteps.length - 1);
  return (
    <>
      <PageHeading eyebrow="Pipeline en direct" title="Suivi du traitement" description="Visualisez la progression et les contrôles appliqués au document." action={<Badge tone={progress === 100 ? 'teal' : 'blue'}>{progress === 100 ? 'Terminé' : progress ? 'En cours' : 'En attente'}</Badge>} />
      {error && <div className="alert alert--error"><CircleAlert size={18} /><span>{error}</span></div>}
      <section className="panel progress-panel">
        <div className="progress-header"><div><strong>{progress ? pipelineSteps[activeStep][0] : 'Prêt à démarrer'}</strong><span>{progress ? pipelineSteps[activeStep][1] : 'Importez un PDF depuis l’espace de travail'}</span></div><b>{progress}%</b></div>
        <div className="progress-track"><div style={{ width: `${progress}%` }} /></div>
        <div className="pipeline-grid">
          {pipelineSteps.map(([title, detail], index) => {
            const complete = progress === 100 || index < activeStep;
            const active = progress > 0 && index === activeStep && progress < 100;
            return (
              <article className={`pipeline-step ${complete ? 'pipeline-step--complete' : ''} ${active ? 'pipeline-step--active' : ''}`} key={title}>
                <span>{complete ? <Check size={16} /> : index + 1}</span><div><strong>{title}</strong><p>{detail}</p></div>
              </article>
            );
          })}
        </div>
      </section>
      <div className="section-grid section-grid--logs">
        <section className="panel"><h2 className="panel-title"><Activity size={19} /> Journal d’exécution</h2><div className="log-list">{logs.length ? logs.map((log, index) => <div key={log}><span>{String(index + 1).padStart(2, '0')}</span><p>{log}</p></div>) : <p className="muted">Le journal apparaîtra au lancement du traitement.</p>}</div></section>
        <section className="panel"><h2 className="panel-title"><BarChart3 size={19} /> État du backend</h2><div className="quality-preview"><strong>{progress}%</strong><div><span>{processingStage || 'En attente'}</span><p>Le statut reflète les appels réels aux endpoints FastAPI.</p></div></div></section>
      </div>
    </>
  );
}

function ExtractionPage({ summaryDetail, notify }) {
  const [tab, setTab] = useState('clean');
  const [query, setQuery] = useState('');
  const source = summaryDetail?.summary || 'Aucun résultat disponible. Lancez d’abord le traitement d’un document.';
  const count = query ? source.toLowerCase().split(query.toLowerCase()).length - 1 : 0;
  const sections = parseSummarySections(summaryDetail?.summary).map(([title, text]) => [title, 'Disponible', text]);
  const wordCount = source.trim() ? source.trim().split(/\s+/).length : 0;

  const copy = async () => {
    await navigator.clipboard.writeText(source);
    notify('Texte copié dans le presse-papiers.');
  };

  return (
    <>
      <PageHeading eyebrow="Résultats" title="Texte extrait" description="Explorez le contenu brut, nettoyé ou segmenté par section." action={<button className="button button--secondary" onClick={copy}><Clipboard size={17} /> Copier le texte</button>} />
      <div className="two-column two-column--wide">
        <section className="panel">
          <label className="search-field"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher dans le texte…" /><span>{query ? `${count} résultat${count > 1 ? 's' : ''}` : ''}</span></label>
          <div className="tabs" role="tablist">
            {[['raw', 'Synthèse Markdown'], ['clean', 'Résumé généré'], ['sections', 'Par section']].map(([id, label]) => <button className={tab === id ? 'active' : ''} onClick={() => setTab(id)} key={id}>{label}</button>)}
          </div>
          {tab === 'sections' ? <div className="section-list">{sections.map(([title, status, text]) => <article className="markdown-rendered" key={title}><div><strong>{title}</strong><Badge tone="teal">{status}</Badge></div><ReactMarkdown>{text}</ReactMarkdown></article>)}</div> : tab === 'clean' ? <div className="text-view markdown-rendered"><ReactMarkdown>{source}</ReactMarkdown></div> : <pre className="text-view">{source}</pre>}
        </section>
        <aside className="stack">
          <section className="panel compact-panel"><h2>Indicateurs</h2>{[['Mots disponibles', wordCount], ['Sections disponibles', sections.length], ['Statut', summaryDetail?.status || 'En attente'], ['Source', 'API FastAPI']].map(([label, value]) => <div className="data-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>
          <section className="alert-card"><CircleAlert size={21} /><div><strong>Contenu exposé</strong><p>L’API publique fournit la synthèse générée ; les artefacts internes restent privés.</p></div></section>
        </aside>
      </div>
    </>
  );
}

function SummaryPage({ file, summaryDetail, summaryPath, notify, onNavigate }) {
  const markdown = summaryDetail?.summary || '';
  const metadata = summaryDetail?.metadata || {};
  const keywords = summaryDetail?.keywords || [];
  const sections = parseSummarySections(markdown);
  const executive = sections.find(([sectionTitle]) => /executive summary|résumé synthétique/i.test(sectionTitle));
  const title = metadata.title || summaryDetail?.filename || 'Synthèse scientifique';

  const copy = async () => {
    if (!markdown) return;
    await navigator.clipboard.writeText(markdown);
    notify('Synthèse Markdown copiée.');
  };

  return (
    <>
      <PageHeading eyebrow="Synthèse scientifique" title={title} description={file?.name || 'Aucun document traité'} action={<div className="button-row"><button className="button button--secondary" disabled={!markdown} onClick={copy}><Clipboard size={17} /> Copier</button><button className="button button--primary" disabled={!summaryDetail} onClick={() => onNavigate('exports')}>Exporter <Download size={17} /></button></div>} />
      <div className="two-column two-column--summary">
        <article className="stack">
          <section className="summary-highlight"><div className="summary-icon"><Sparkles size={21} /></div><div><span>Résumé exécutif</span><p>{executive?.[1] || (markdown ? 'Consultez la synthèse structurée ci-dessous.' : 'Lancez un traitement pour afficher la synthèse scientifique.')}</p></div></section>
          <section className="panel">
            <h2>Lecture structurée</h2>
            <div className="summary-sections">{sections.length ? sections.map(([sectionTitle, text], index) => <article key={sectionTitle}><span>{String(index + 1).padStart(2, '0')}</span><div><h3>{sectionTitle}</h3><p>{text}</p></div></article>) : <article><span>—</span><div><h3>En attente</h3><p>Aucune synthèse générée.</p></div></article>}</div>
          </section>
          <section className="panel markdown-panel"><div className="list-heading"><h2>Aperçu Markdown</h2><button className="text-button" disabled={!markdown} onClick={copy}>Copier</button></div><pre>{markdown || 'Aucun contenu disponible.'}</pre></section>
        </article>
        <aside className="stack">
          <section className="score-card"><div className="score-ring"><strong>{summaryDetail ? '✓' : '—'}</strong></div><div><Badge tone={summaryDetail ? 'teal' : 'slate'}>{summaryDetail?.status || 'En attente'}</Badge><h2>Statut du traitement</h2><p>{summaryPath || 'Aucun fichier de synthèse disponible.'}</p></div></section>
          <section className="panel compact-panel"><h2>Métadonnées</h2>{[['Auteurs', displayValue(metadata.authors)], ['Source', displayValue(metadata.source)], ['Année', displayValue(metadata.year)], ['Pages', displayValue(metadata.page_count)]].map(([label, value]) => <div className="data-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>
          <section className="panel compact-panel"><h2>Concepts principaux</h2><div className="tag-cloud">{keywords.slice(0, 5).map((item) => <Badge key={keywordLabel(item)}>{keywordLabel(item)}</Badge>)}</div></section>
        </aside>
      </div>
    </>
  );
}

function KeywordsPage({ summaryDetail }) {
  const keywords = summaryDetail?.keywords || [];
  const grouped = Object.entries(keywords.reduce((groups, item) => {
    const method = typeof item === 'string' ? 'keyword' : item.method || 'keyword';
    groups[method] = [...(groups[method] || []), keywordLabel(item)];
    return groups;
  }, {}));
  const scored = keywords.filter((item) => item && typeof item === 'object' && Number.isFinite(item.score));
  const averageScore = scored.length
    ? Math.round((scored.reduce((total, item) => total + item.score, 0) / scored.length) * 100)
    : 0;

  return (
    <>
      <PageHeading eyebrow="Analyse sémantique" title="Mots-clés et concepts" description="Les concepts détectés sont regroupés pour accélérer l’exploration du document." />
      <div className="section-grid">
        <section className="panel"><h2>Concepts détectés</h2><div className="tag-cloud tag-cloud--large">{keywords.length ? keywords.map((item) => <Badge key={keywordLabel(item)}>{keywordLabel(item)}</Badge>) : <span className="muted">Aucun mot-clé disponible.</span>}</div></section>
        <section className="panel"><h2>Regroupement par source</h2>{grouped.length ? grouped.map(([method, items]) => <div className="theme-row" key={method}><span>{method}</span><p>{items.join(', ')}</p></div>) : <p className="muted">Lancez un traitement pour afficher les concepts.</p>}</section>
      </div>
      <section className="panel quality-panel"><PageHeading eyebrow="Qualité sémantique" title="Indicateurs disponibles" /><div className="quality-grid">{[['Mots-clés', keywords.length, 'teal'], ['Sources', grouped.length, 'purple'], ['Score moyen', averageScore, 'amber']].map(([label, value, tone]) => <div key={label}><div><span>{label}</span><strong>{value}{label === 'Score moyen' ? '%' : ''}</strong></div><div className="mini-track"><span className={`fill--${tone}`} style={{ width: `${label === 'Score moyen' ? averageScore : Math.min(value * 10, 100)}%` }} /></div></div>)}</div></section>
    </>
  );
}

function HistoryPage() {
  const [documents, setDocuments] = useState([]);
  const [pipelineRuns, setPipelineRuns] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingRun, setLoadingRun] = useState(false);
  const [error, setError] = useState('');
  const [runToDelete, setRunToDelete] = useState(null);
  const [deletingRun, setDeletingRun] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [deletingDocument, setDeletingDocument] = useState(false);

  useEffect(() => {
    let active = true;
    getDocuments()
      .then((items) => { if (active) setDocuments(Array.isArray(items) ? items : []); })
      .catch((requestError) => { if (active) setError(requestError.message || 'Historique indisponible.'); })
      .finally(() => { if (active) setLoadingDocuments(false); });
    return () => { active = false; };
  }, []);

  const documentId = (document) => document?.document_id || document?.id;
  const documentName = (document) => document?.filename || document?.original_filename || documentId(document);

  const selectDocument = async (document) => {
    const id = documentId(document);
    if (!id) return;
    setSelectedDocument(document);
    setSelectedRun(null);
    setPipelineRuns([]);
    setLoadingRuns(true);
    setError('');
    try {
      const runs = await getDocumentPipelineRuns(id);
      setPipelineRuns(Array.isArray(runs) ? runs : []);
    } catch (requestError) {
      setError(requestError.message || 'Exécutions indisponibles.');
    } finally {
      setLoadingRuns(false);
    }
  };

  const selectRun = async (run) => {
    const id = run?.pipeline_run_id || run?.id;
    if (!id) return;
    setLoadingRun(true);
    setError('');
    try {
      setSelectedRun(await getPipelineRun(id));
    } catch (requestError) {
      setError(requestError.message || 'Détails de l’exécution indisponibles.');
    } finally {
      setLoadingRun(false);
    }
  };

const deleteDocumentRecord = (document) => {
  const id = documentId(document);

  if (!id) return;

  setDocumentToDelete(document);
};

const deleteRun = (run) => {
  const id = run?.pipeline_run_id || run?.id;

  if (!id) return;

  setRunToDelete(run);
}; 
const confirmDeleteRun = async () => {
  if (!runToDelete) return;

  const id = runToDelete.pipeline_run_id || runToDelete.id;

  setDeletingRun(true);
  setError('');

  try {
    await deletePipelineRun(id);

    setPipelineRuns((runs) =>
      runs.filter(
        (item) => (item.pipeline_run_id || item.id) !== id
      )
    );

    if (
      selectedRun &&
      (selectedRun.pipeline_run_id || selectedRun.id) === id
    ) {
      setSelectedRun(null);
    }

    setRunToDelete(null);
  } catch (requestError) {
    setError(
      requestError.message ||
        'Impossible de supprimer cette exécution.'
    );
  } finally {
    setDeletingRun(false);
  }
};
const confirmDeleteDocument = async () => {
  if (!documentToDelete) return;

  const id = documentId(documentToDelete);

  setDeletingDocument(true);
  setError('');

  try {
    await deleteDocument(id);

    setDocuments((items) =>
      items.filter((item) => documentId(item) !== id)
    );

    if (selectedDocument && documentId(selectedDocument) === id) {
      setSelectedDocument(null);
      setSelectedRun(null);
      setPipelineRuns([]);
    }

    setDocumentToDelete(null);
  } catch (requestError) {
    setError(
      requestError.message ||
        'Impossible de supprimer le document.'
    );
  } finally {
    setDeletingDocument(false);
  }
};


  return (
    <>
      <PageHeading eyebrow="Traçabilité" title="Historique des documents" description="Consultez les documents et exécutions précédemment persistés par le pipeline." />
      {error && <div className="alert alert--error"><CircleAlert size={18} /><span>{error}</span></div>}
      <section className="panel table-panel">
        <table><thead><tr><th>Document</th><th>Statut</th><th>Date</th><th /></tr></thead><tbody>
          {loadingDocuments && <tr><td colSpan="4">Chargement des documents…</td></tr>}
          {!loadingDocuments && !documents.length && <tr><td colSpan="4">Aucun document persisté.</td></tr>}
          {documents.map((document) => <tr key={documentId(document)}><td><span className="table-file"><FileText size={18} /><strong>{documentName(document)}</strong></span></td><td><Badge>{document.status || 'Disponible'}</Badge></td><td>{formatDate(document.created_at)}</td><td>
  <div className="history-document-actions">
    <button
      type="button"
      className="text-button"
      onClick={() => selectDocument(document)}
    >
      Exécutions
      <ArrowRight size={15} />
    </button>

    <button
      type="button"
      className="history-document__delete"
      aria-label={`Supprimer ${documentName(document)}`}
      onClick={() => deleteDocumentRecord(document)}
    >
      <Trash2 size={16} />
    </button>
  </div>
</td></tr>)}
        </tbody></table>
     </section>

{selectedDocument && (
  <section className="panel history-panel">
    <h2>Exécutions de {documentName(selectedDocument)}</h2>

    {loadingRuns ? (
      <p className="muted">Chargement des exécutions…</p>
    ) : pipelineRuns.length ? (
      <div className="history-run-list">
        {pipelineRuns.map((run) => {
          const runId = run.pipeline_run_id || run.id;

          return (
            <div className="history-run" key={runId}>
              <button
                type="button"
                className="history-run__content"
                onClick={() => selectRun(run)}
              >
                <span>
                  <strong>
                    {run.model || 'Modèle non renseigné'}
                  </strong>

                  <small>
                    {formatDate(run.started_at)} ·{' '}
                    {formatDuration(run.duration_ms)}
                  </small>
                </span>

                <Badge
                  tone={
                    run.status === 'completed'
                      ? 'teal'
                      : 'amber'
                  }
                >
                  {run.status}
                </Badge>

                <ArrowRight size={16} />
              </button>

              <button
                type="button"
                className="history-run__delete"
                aria-label={`Supprimer l'exécution ${runId}`}
                onClick={(event) => {
                  event.stopPropagation();
                  deleteRun(run);
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          );
        })}
      </div>
    ) : (
      <p className="muted">
        Aucune exécution persistée pour ce document.
      </p>
    )}
  </section>
)}
      {loadingRun && <p className="muted">Chargement des résultats persistés…</p>}
          
      {selectedRun && (
  <section className="history-details">
    <PageHeading
      eyebrow="Exécution sélectionnée"
      title="Résultats persistés"
      description={`Statut ${selectedRun.status} · ${formatDuration(
        selectedRun.duration_ms
      )}`}
    />

    <div className="section-grid">
      <section className="panel compact-panel">
        <h2>Exécution</h2>

        {[
          ['Document', selectedRun.document_id],
          ['Modèle', selectedRun.model],
          ['Démarrée', formatDate(selectedRun.started_at)],
          ['Terminée', formatDate(selectedRun.completed_at)],
          ['Étape en échec', selectedRun.failure_stage],
          ['Erreur', selectedRun.error_message],
        ].map(([label, value]) => (
          <div className="data-row" key={label}>
            <span>{label}</span>
            <strong>{displayValue(value)}</strong>
          </div>
        ))}
      </section>

      <section className="panel compact-panel">
        <h2>Inférence</h2>

        {selectedRun.inference ? (
          [
            ['Statut', selectedRun.inference.status],
            ['Requêtes', selectedRun.inference.request_count],
            ['Terminées', selectedRun.inference.completed_count],
            ['Échouées', selectedRun.inference.failed_count],
            ['Durée', formatDuration(selectedRun.inference.duration_ms)],
          ].map(([label, value]) => (
            <div className="data-row" key={label}>
              <span>{label}</span>
              <strong>{displayValue(value)}</strong>
            </div>
          ))
        ) : (
          <p className="muted">Aucun résultat d’inférence.</p>
        )}
      </section>
    </div>

    <div className="history-stage-grid">
      <section className="panel">
        <h2>Extraction</h2>

        {selectedRun.extraction ? (
          <>
            <div className="data-row">
              <span>Méthode</span>
              <strong>
                {selectedRun.extraction.extraction_method}
              </strong>
            </div>

            <div className="data-row">
              <span>Pages</span>
              <strong>
                {displayValue(selectedRun.extraction.page_count)}
              </strong>
            </div>

            <PersistedJson
              value={selectedRun.extraction.extraction_report}
            />
          </>
        ) : (
          <p className="muted">
            Aucun résultat d’extraction.
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Prétraitement</h2>
        <PersistedJson value={selectedRun.preprocessing} />
      </section>

      <section className="panel">
        <h2>Inférence</h2>
        <PersistedJson
          value={selectedRun.inference?.result_metadata}
        />
      </section>

        <section className="panel history-quality-panel">
  <div className="list-heading">
    <div>
      <span className="eyebrow">Contrôle qualité</span>
      <h2>Évaluation de la synthèse</h2>
    </div>
  </div>

  {selectedRun.summary?.summary_json?.quality_report ? (
    (() => {
      const quality = selectedRun.summary.summary_json.quality_report;

      return (
        <>
          <div className="quality-overview">
            <div className="quality-score">
              <strong>{quality.overall_score}/10</strong>
              <span>Score global</span>
            </div>

            <Badge
              tone={
                quality.decision === 'PASS'
                  ? 'teal'
                  : quality.decision === 'REVIEW'
                    ? 'amber'
                    : 'slate'
              }
            >
              {quality.decision}
            </Badge>
          </div>

          <div className="quality-section">
            <h3>Évaluation par section</h3>

            <div className="quality-grid">
              {Object.entries(quality.sections || {}).map(
                ([section, result]) => (
                  <div className="quality-item" key={section}>
                    <span>
                      {section.replaceAll('_', ' ')}
                    </span>
                    <strong>{result.score}/10</strong>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="quality-section">
            <h3>Contrôles globaux</h3>

            <div className="quality-grid">
              {Object.entries(quality.global_checks || {}).map(
                ([check, score]) => (
                  <div className="quality-item" key={check}>
                    <span>
                      {check.replaceAll('_', ' ')}
                    </span>
                    <strong>{score}/10</strong>
                  </div>
                )
              )}
            </div>
          </div>

          {quality.critical_errors?.length > 0 && (
            <div className="quality-section">
              <h3>Erreurs critiques</h3>

              <ul className="quality-list">
                {quality.critical_errors.map((error, index) => (
                  <li key={index}>
                    {String(error.issue || error.reason || error)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {quality.recommendations?.length > 0 && (
            <div className="quality-section">
              <h3>Recommandations</h3>

              <ul className="quality-list">
                {quality.recommendations.map(
                  (recommendation, index) => (
                    <li key={index}>
                      {String(recommendation)}
                    </li>
                  )
                )}
              </ul>
            </div>
          )}
        </>
      );
    })()
  ) : (
    <p className="muted">
      Aucune évaluation de qualité disponible.
    </p>
  )}
</section>

<section className="panel">
  <h2>Synthèse</h2>

        {selectedRun.summary ? (
          <>
            <div className="text-view markdown-rendered">
              <ReactMarkdown>
                {selectedRun.summary.summary_text}
              </ReactMarkdown>
            </div>

            <PersistedJson
              value={selectedRun.summary.summary_json}
            />
          </>
        ) : (
          <p className="muted">
            Aucune synthèse persistée.
          </p>
        )}
      </section>
    </div>
  </section>
)}
      {runToDelete && (
        <div
          className="delete-modal-backdrop"
          onClick={() => {
            if (!deletingRun) {
              setRunToDelete(null);
            }
          }}
        >
          <div
            className="delete-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="delete-modal__icon">
              <Trash2 size={20} />
            </div>

            <h3 id="delete-modal-title">
              Supprimer l'exécution ?
            </h3>

            <p>
              Cette action supprimera cette exécution et ses
              résultats persistés.
            </p>

            <p className="delete-modal__note">
              Le document PDF sera conservé.
            </p>

            <div className="delete-modal__actions">
              <button
                type="button"
                className="delete-modal__cancel"
                disabled={deletingRun}
                onClick={() => setRunToDelete(null)}
              >
                Annuler
              </button>

              <button
                type="button"
                className="delete-modal__confirm"
                disabled={deletingRun}
                onClick={confirmDeleteRun}
              >
                {deletingRun ? 'Suppression…' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
      {documentToDelete && (
  <div
    className="delete-modal-backdrop"
    onClick={() => {
      if (!deletingDocument) {
        setDocumentToDelete(null);
      }
    }}
  >
    <div
      className="delete-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-document-modal-title"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="delete-modal__icon">
        <Trash2 size={20} />
      </div>

      <h3 id="delete-document-modal-title">
        Supprimer le document ?
      </h3>

      <p>
        Vous êtes sur le point de supprimer{' '}
        <strong>
          {documentName(documentToDelete)}
        </strong>
        .
      </p>

      <p className="delete-modal__note">
        Le PDF, les exécutions et tous les résultats
        persistés associés seront supprimés.
      </p>

      <div className="delete-modal__actions">
        <button
          type="button"
          className="delete-modal__cancel"
          disabled={deletingDocument}
          onClick={() => setDocumentToDelete(null)}
        >
          Annuler
        </button>

        <button
          type="button"
          className="delete-modal__confirm"
          disabled={deletingDocument}
          onClick={confirmDeleteDocument}
        >
          {deletingDocument
            ? 'Suppression…'
            : 'Supprimer'}
        </button>
      </div>
    </div>
  </div>
)}

    </>
  );
}
   
function ExportsPage({ summaryDetail, notify }) {
  const exports = [
    [FileText, 'Synthèse Markdown', 'Document structuré et lisible', '.md', () => downloadArtifact(summaryDetail?.downloads.markdown, 'summary.md')],
    [FileJson, 'Données JSON', 'Métadonnées et résultats sérialisés', '.json', () => downloadArtifact(summaryDetail?.downloads.json, 'summary.json')],
    [Download, 'Document PDF', 'Document PDF généré par le serveur', '.pdf', () => downloadPdf(summaryDetail.filename)],
  ];
  const run = async (action, title) => {
    try {
      await action();
      notify(`${title} préparé.`);
    } catch (error) {
      notify(error.message || 'Téléchargement impossible.');
    }
  };
  return (
    <>
      <PageHeading eyebrow="Livrables" title="Exporter les résultats" description="Choisissez le format adapté à votre usage et conservez une version portable de la synthèse." />
      {summaryDetail ? <div className="export-grid">{exports.map(([Icon, title, text, extension, action]) => <button className="export-card" onClick={() => run(action, title)} key={title}><span className="export-icon"><Icon size={23} /></span><div><strong>{title}</strong><p>{text}</p></div><Badge tone="slate">{extension}</Badge><Download size={18} /></button>)}</div> : <div className="alert alert--error"><CircleAlert size={18} /><span>Aucune synthèse disponible au téléchargement.</span></div>}
      <section className="panel export-doc"><h2>Contenu des exports</h2><div className="doc-grid">{['Titre et métadonnées', 'Résumé exécutif', 'Sections scientifiques', 'Mots-clés', 'Limites détectées', 'Score de qualité'].map((item) => <div key={item}><CheckCircle2 size={18} /><span>{item}</span></div>)}</div></section>
    </>
  );
}

export default function App() {
  const [page, setPage] = useState('home');
  const [files, setFiles] = useState([]);
  const [fileError, setFileError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [uploadedDocumentId, setUploadedDocumentId] = useState('');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [processingError, setProcessingError] = useState('');
  const [processingStage, setProcessingStage] = useState('En attente');
  const [processed, setProcessed] = useState(false);
  const [summaryDetail, setSummaryDetail] = useState(null);
  const [summaryPath, setSummaryPath] = useState('');
  const [toast, setToast] = useState('');

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(''), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const navigate = (nextPage) => {
    setPage(nextPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const notify = (message) => setToast(message);

  const handleFiles = async (incoming) => {
    const valid = incoming.filter((item) => (item.type === 'application/pdf' || item.name.toLowerCase().endsWith('.pdf')) && item.size <= 50 * 1024 * 1024);
    const rejected = incoming.length - valid.length;
    setFileError(rejected ? `${rejected} fichier(s) refusé(s). Utilisez un PDF de 50 Mo maximum.` : '');
    if (!valid.length) return;

    const pendingFiles = valid.map((file) => ({
      id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
      file,
      name: file.name,
      size: file.size,
      lastModified: file.lastModified,
      uploadStatus: 'uploading',
      uploadedFilename: '',
    }));
    setFiles((current) => [...current, ...pendingFiles]);
    setUploading(true);

    const failures = [];
    for (const pendingFile of pendingFiles) {
      try {
        const response = await uploadPdf(pendingFile.file);
        setFiles((current) => current.map((item) => item.id === pendingFile.id
          ? { ...item, uploadStatus: 'uploaded', uploadedFilename: response.filename,uploadedDocumentId: response.document_id }
          : item));
        setUploadedFilename((current) => current || response.filename);
setUploadedDocumentId((current) => current || response.document_id);
      } catch (error) {
        failures.push(`${pendingFile.name}: ${error.message}`);
        setFiles((current) => current.filter((item) => item.id !== pendingFile.id));
      }
    }

    setUploading(false);
    if (failures.length) {
      setFileError(failures.join(' · '));
    } else {
      notify(`${valid.length} document(s) importé(s).`);
    }
  };

  const reset = () => {
    setUploadedDocumentId('');
    setFiles([]);
    setFileError('');
    setUploading(false);
    setUploadedFilename('');
    setProgress(0);
    setLogs([]);
    setProcessingError('');
    setProcessingStage('En attente');
    setProcessed(false);
    setSummaryDetail(null);
    setSummaryPath('');
    navigate('upload');
    notify('Espace de travail réinitialisé.');
  };

  const removeFile = (index) => {
    setFiles((items) => {
      const remaining = items.filter((_, itemIndex) => itemIndex !== index);
      const uploadedItem = remaining.find(
      (item) => item.uploadStatus === 'uploaded'
      );

      setUploadedFilename(uploadedItem?.uploadedFilename || '');
    setUploadedDocumentId(uploadedItem?.uploadedDocumentId || '');
      return remaining;
    });
  };

  const startProcessing = async () => {
    if (!uploadedDocumentId || uploading) return;
    setProgress(25);
    setLogs(['Document importé par le backend.', 'Pipeline de synthèse démarré.']);
    setProcessingError('');
    setProcessingStage('Traitement et génération de la synthèse');
    setProcessed(false);
    navigate('processing');

    try {
      const summarizeResponse = await summarizePdf(uploadedDocumentId);
      if (summarizeResponse.status !== 'completed') {
        throw new Error(summarizeResponse.message || 'La synthèse a échoué.');
      }

      setProgress(80);
      setProcessingStage('Chargement de la synthèse générée');
      setLogs((items) => [...items, 'Pipeline terminé.', 'Chargement des métadonnées, mots-clés et exports.']);
      setSummaryPath(summarizeResponse.summary_path || '');

      const detail = await getSummary(summarizeResponse.filename);
      setSummaryDetail(detail);
      setProgress(100);
      setProcessingStage('Synthèse disponible');
      setLogs((items) => [...items, 'Synthèse scientifique et téléchargements disponibles.']);
      setProcessed(true);
      notify('Traitement terminé. La synthèse est disponible.');
      navigate('summary');
    } catch (error) {
      const message = error.message || 'Le traitement a échoué.';
      setProcessingError(message);
      setProcessingStage('Échec du traitement');
      setLogs((items) => [...items, `Erreur : ${message}`]);
      setProgress(0);
      notify(message);
    }
  };

  const pages = {
    home: <HomePage file={files[0]} processed={processed} summaryDetail={summaryDetail} onNavigate={navigate} />,
    upload: <UploadPage files={files} error={fileError} uploading={uploading} onFiles={handleFiles} onRemove={removeFile} onProcess={startProcessing} />,
    processing: <ProcessingPage progress={progress} logs={logs} error={processingError} processingStage={processingStage} />,
    extraction: <ExtractionPage summaryDetail={summaryDetail} notify={notify} />,
    summary: <SummaryPage file={files[0]} summaryDetail={summaryDetail} summaryPath={summaryPath} notify={notify} onNavigate={navigate} />,
    keywords: <KeywordsPage summaryDetail={summaryDetail} />,
    history: <HistoryPage />,
    exports: <ExportsPage summaryDetail={summaryDetail} notify={notify} />,
  };

  return (
    <AppShell page={page} onNavigate={navigate} onReset={reset}>
      {pages[page] || pages.home}
      {toast && <div className="toast" role="status"><CheckCircle2 size={18} />{toast}</div>}
    </AppShell>
  );
}
