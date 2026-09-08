const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'object'
      ? payload.detail || payload.message
      : payload;
    throw new Error(message || `Erreur HTTP ${response.status}`);
  }

  return payload;
}

export function getHealth() {
  return apiRequest('/health');
}

export function uploadPdf(file) {
  const body = new FormData();
  body.append('file', file);
  return apiRequest('/upload', { method: 'POST', body });
}

export function summarizePdf(documentId, model = null) {
  return apiRequest('/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      document_id: documentId,
      model,
     }),
  });
}

export function getSummary(filename) {
  return apiRequest(`/summary/${encodeURIComponent(filename)}`);
}

export function getDocuments() {
  return apiRequest('/documents');
}

export function getDocumentPipelineRuns(documentId) {
  return apiRequest(`/documents/${encodeURIComponent(documentId)}/pipeline-runs`);
}

export function getPipelineRun(pipelineRunId) {
  return apiRequest(`/pipeline-runs/${encodeURIComponent(pipelineRunId)}`);
}
export function deletePipelineRun(pipelineRunId) {
  return apiRequest(`/pipeline-runs/${encodeURIComponent(pipelineRunId)}`, {
    method: 'DELETE',
  });
}
export function deleteDocument(documentId) {
  return apiRequest(`/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
  });
}

export function downloadPdf(filename) {
  return downloadArtifact(
    `/summary/${encodeURIComponent(filename)}/pdf`,
    `${filename.replace(/\.pdf$/i, '') || 'document'}_summary.pdf`,
  );
}

export async function downloadArtifact(path, fallbackFilename) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    let message = `Erreur HTTP ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // The backend returned a non-JSON error body.
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackFilename;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
