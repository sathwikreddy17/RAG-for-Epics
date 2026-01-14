/**
 * Epic Explorer - Main Application JavaScript
 * Handles API communication, state management, and UI interactions
 */

// ============================================
// CONFIGURATION
// ============================================
const API_BASE = '';  // Same origin
const STREAM_ENABLED = true;

// ============================================
// STATE MANAGEMENT
// ============================================
const AppState = {
    isLoading: false,
    currentQuery: '',
    currentAnswer: null,
    sources: [],
    relatedQuestions: [],
    detectedCharacter: null,
    llmConnected: false,
    stats: {
        chunks: 0,
        characters: 0,
        events: 0,
        relations: 0
    }
};

// ============================================
// DOM ELEMENTS
// ============================================
const elements = {
    searchInput: () => document.getElementById('searchInput'),
    searchBtn: () => document.getElementById('searchBtn'),
    resultsArea: () => document.getElementById('resultsArea'),
    answerCard: () => document.getElementById('answerCard'),
    answerText: () => document.getElementById('answerText'),
    answerMeta: () => document.getElementById('answerMeta'),
    sourcesGrid: () => document.getElementById('sourcesGrid'),
    sourcesCount: () => document.getElementById('sourcesCount'),
    relatedPanel: () => document.getElementById('relatedPanel'),
    relatedList: () => document.getElementById('relatedList'),
    characterPanel: () => document.getElementById('characterPanel'),
    statusIndicator: () => document.getElementById('statusIndicator'),
    statusText: () => document.getElementById('statusText'),
    streamCheckbox: () => document.getElementById('streamCheckbox'),
    sourcesCheckbox: () => document.getElementById('sourcesCheckbox'),
    deepSearchCheckbox: () => document.getElementById('deepSearchCheckbox'),
    docSelect: () => document.getElementById('docSelect'),
    emptyState: () => document.getElementById('emptyState'),
    themeDropdown: () => document.getElementById('themeDropdown'),
    currentThemeName: () => document.getElementById('currentThemeName')
};

// ============================================
// API FUNCTIONS
// ============================================
async function checkLLMStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();

        // Backend contract: /api/health returns { status: "healthy"|..., backend_status: {...} }
        const isHealthy = data?.status === 'healthy';
        const lmStudioUrl = data?.backend_status?.lm_studio_url;

        AppState.llmConnected = Boolean(isHealthy && lmStudioUrl);
        updateStatusIndicator();
        return AppState.llmConnected;
    } catch (error) {
        console.error('Health check failed:', error);
        AppState.llmConnected = false;
        updateStatusIndicator();
        return false;
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        if (response.ok) {
            const data = await response.json();
            AppState.stats = {
                chunks: data.totals?.total_chunks || data.total_chunks || 0,
                characters: data.characters_count || 0,
                events: data.events_count || 0,
                relations: data.relationships_count || 0
            };
            updateStatsDisplay();
        }
    } catch (error) {
        console.error('Failed to fetch stats:', error);
    }
}

async function fetchDocuments() {
    try {
        const response = await fetch(`${API_BASE}/api/documents`);
        if (response.ok) {
            const data = await response.json();
            populateDocumentSelect(data.documents || []);
        }
    } catch (error) {
        console.error('Failed to fetch documents:', error);
    }
}

function setAskButtonLoading(isLoading, label = 'Ask') {
    const btn = elements.searchBtn();
    if (!btn) return;

    btn.disabled = Boolean(isLoading);
    if (isLoading) {
        btn.innerHTML = '<span class="loading-spinner"></span><span style="margin-left:8px;">Working…</span>';
    } else {
        btn.innerHTML = `<span>✨</span><span>${label}</span>`;
    }
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 120000) {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        return res;
    } finally {
        clearTimeout(t);
    }
}

async function submitQuery(query) {
    if (AppState.isLoading || !query.trim()) return;

    AppState.isLoading = true;
    AppState.currentQuery = query;
    updateUI('loading');

    const useStreaming = elements.streamCheckbox()?.checked ?? true;
    const includeSources = elements.sourcesCheckbox()?.checked ?? true;
    const deepSearch = elements.deepSearchCheckbox()?.checked ?? false;
    const docFilter = elements.docSelect()?.value || '';

    // Ensure user sees that something is happening (some queries can take ~60s)
    showAnswerCard();
    elements.answerText().innerHTML = '<p class="text-muted">Working on it… (this can take up to a minute for deep questions)</p>';

    try {
        if (useStreaming) {
            // If streaming fails (some browsers/proxies), safely fall back to regular request
            try {
                await streamQuery(query, includeSources, deepSearch, docFilter);
            } catch (e) {
                console.warn('Streaming failed, falling back to non-streaming:', e);
                await regularQuery(query, includeSources, deepSearch, docFilter);
            }
        } else {
            await regularQuery(query, includeSources, deepSearch, docFilter);
        }

        // Optional: update retrieval debug overlay after query completes (reflects exact retrieval)
        await maybeUpdateRetrievalDebug(query);
    } catch (error) {
        console.error('Query failed:', error);
        showError('Failed to get response. Please try again.');
    } finally {
        AppState.isLoading = false;
        updateUI('complete');
    }
}

async function fetchRetrievalDebug(query, k = 10, fileFilter = 'all') {
    try {
        const res = await fetch(`${API_BASE}/api/debug/retrieval`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                k,
                file_filter: fileFilter || 'all'
            })
        });
        if (!res.ok) return null;
        return await res.json();
    } catch (e) {
        return null;
    }
}

function ensureRetrievalDebugUI() {
    let box = document.getElementById('retrievalDebugBox');
    if (box) return box;

    box = document.createElement('div');
    box.id = 'retrievalDebugBox';
    box.style.position = 'fixed';
    box.style.right = '16px';
    box.style.bottom = '16px';
    box.style.width = '460px';
    box.style.maxWidth = 'calc(100vw - 32px)';
    box.style.maxHeight = '55vh';
    box.style.overflow = 'auto';
    box.style.zIndex = '10000';
    box.style.display = 'none';
    box.style.background = 'var(--bg-secondary)';
    box.style.border = '1px solid var(--border)';
    box.style.borderRadius = '12px';
    box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.35)';

    document.body.appendChild(box);
    return box;
}

function hideRetrievalDebug() {
    const box = document.getElementById('retrievalDebugBox');
    if (box) box.style.display = 'none';
}

function renderRetrievalDebug(debug) {
    const box = ensureRetrievalDebugUI();
    if (!box) return;

    if (!debug) {
        box.style.display = 'none';
        return;
    }

    const candidates = Array.isArray(debug.candidates) ? debug.candidates : [];
    const top = candidates.slice(0, 10);

    const topFiles = {};
    for (const c of top) {
        const fn = c?.metadata?.file_name || 'Unknown';
        topFiles[fn] = (topFiles[fn] || 0) + 1;
    }

    const routing = debug.routing?.route || debug.routing?.strategy?.name || (debug.routing ? 'routed' : 'none');

    box.innerHTML = `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 12px 8px 12px; border-bottom: 1px solid var(--border);">
            <div style="font-weight:600;">Retrieval Debug</div>
            <div style="display:flex; gap:8px; align-items:center;">
                <span class="text-muted" style="font-size:12px;">k=${escapeHtml(String(debug.k ?? ''))}</span>
                <button class="icon-btn" title="Close" style="width:32px; height:32px;" onclick="window.hideRetrievalDebug()">×</button>
            </div>
        </div>

        <div style="padding:12px;">
            <div class="text-muted" style="font-size:12px; margin-bottom:8px;">Query</div>
            <div style="font-size:13px; line-height:1.4; margin-bottom:10px;">${escapeHtml(String(debug.query || ''))}</div>

            <div class="text-muted" style="font-size:12px; margin-bottom:6px;">Normalized</div>
            <div style="font-size:12px; opacity:0.9; margin-bottom:10px;">${escapeHtml(String(debug.retrieval_query || ''))}</div>

            <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:10px;">
                <div><span class="text-muted" style="font-size:12px;">Filter</span><div style="font-size:12px;">${escapeHtml(String(debug.file_filter || 'all'))}</div></div>
                <div><span class="text-muted" style="font-size:12px;">Routing</span><div style="font-size:12px;">${escapeHtml(String(routing))}</div></div>
                <div><span class="text-muted" style="font-size:12px;">Reranker</span><div style="font-size:12px;">${debug.reranker?.enabled ? (debug.reranker?.used_in_debug ? 'used' : 'enabled') : 'off'}</div></div>
            </div>

            <div class="text-muted" style="font-size:12px; margin-bottom:6px;">Top files (top 10)</div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px;">
                ${Object.entries(topFiles).slice(0, 6).map(([fn, n]) => `
                    <span style="font-size:11px; padding:4px 8px; border:1px solid var(--border); border-radius:999px; background: var(--bg-tertiary);">${escapeHtml(fn)} (${n})</span>
                `).join('')}
            </div>

            <div class="text-muted" style="font-size:12px; margin-bottom:6px;">Candidates</div>
            <div style="display:flex; flex-direction:column; gap:8px;">
                ${top.map((c) => {
                    const meta = c?.metadata || {};
                    const scores = c?.scores || {};
                    const file = meta.file_name || 'Unknown';
                    const page = meta.page ?? '—';
                    const rank = c?.rank ?? '—';
                    const fused = (scores.fused ?? scores.vector ?? 0);
                    const fusedPct = (typeof fused === 'number') ? Math.round(fused * 100) : '—';

                    return `
                        <div style="padding:10px; border: 1px solid var(--border); border-radius:10px; background: var(--bg-tertiary);">
                            <div style="display:flex; justify-content:space-between; gap:12px; margin-bottom:6px;">
                                <div style="font-size:12px; font-weight:600;">#${escapeHtml(String(rank))} • ${escapeHtml(String(file))}</div>
                                <div style="font-size:12px;">${escapeHtml(String(fusedPct))}%</div>
                            </div>
                            <div class="text-muted" style="font-size:11px; margin-bottom:6px;">Page ${escapeHtml(String(page))} • bm25=${escapeHtml(String(scores.bm25 ?? '—'))} • vec=${escapeHtml(String(scores.vector ?? '—'))} • entity=${escapeHtml(String(scores.entity_boost ?? '—'))} • rerank=${escapeHtml(String(scores.reranker ?? '—'))}</div>
                            <div style="font-size:12px; line-height:1.35; white-space:pre-wrap;">${escapeHtml(String(meta.text_preview || ''))}</div>
                        </div>
                    `;
                }).join('')}
            </div>

            <div class="text-muted" style="font-size:11px; margin-top:12px;">Tip: toggle with <code style="font-size:11px;">D</code>. Requires <code style="font-size:11px;">ENABLE_DEBUG_ENDPOINTS=true</code> on the server.</div>
        </div>
    `;

    box.style.display = 'block';
}

let __debugOverlayEnabled = false;
let __lastDebugPayload = null;

async function maybeUpdateRetrievalDebug(query) {
    if (!__debugOverlayEnabled) return;
    const q = (query || '').trim();
    if (!q) return;

    const docFilter = elements.docSelect()?.value || '';
    const debug = await fetchRetrievalDebug(q, 10, docFilter || 'all');
    __lastDebugPayload = debug;
    renderRetrievalDebug(debug);

    if (!debug) {
        showToast('Retrieval debug not available (enable ENABLE_DEBUG_ENDPOINTS=true)', 'info');
    }
}

function toggleRetrievalDebug() {
    __debugOverlayEnabled = !__debugOverlayEnabled;
    if (!__debugOverlayEnabled) {
        hideRetrievalDebug();
        return;
    }

    // If we already have a payload, just show it; otherwise fetch for the current query
    if (__lastDebugPayload) {
        renderRetrievalDebug(__lastDebugPayload);
        return;
    }

    const q = elements.searchInput()?.value || AppState.currentQuery || '';
    maybeUpdateRetrievalDebug(q);
}

// ============================================
// RETRIEVAL DEBUG (optional)
// ============================================

// ============================================
// UI FUNCTIONS
// ============================================
function updateUI(state) {
    const searchBtn = elements.searchBtn();
    
    switch (state) {
        case 'loading':
            searchBtn.disabled = true;
            searchBtn.innerHTML = '<span class="loading-spinner"></span>';
            elements.emptyState()?.classList.add('hidden');
            break;
        case 'complete':
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<span>✨</span><span>Ask</span>';
            break;
    }
}

function showAnswerCard() {
    elements.emptyState()?.classList.add('hidden');
    elements.answerCard()?.classList.remove('hidden');
}

function updateStatusIndicator() {
    const indicator = elements.statusIndicator();
    const text = elements.statusText();
    
    if (indicator && text) {
        if (AppState.llmConnected) {
            indicator.classList.remove('disconnected');
            text.textContent = 'LLM Connected';
        } else {
            indicator.classList.add('disconnected');
            text.textContent = 'LLM Disconnected';
        }
    }
}

function updateStatsDisplay() {
    const formatNumber = (num) => {
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    };
    
    // Update stat items
    const statChunks = document.getElementById('statChunks');
    const statCharacters = document.getElementById('statCharacters');
    const statEvents = document.getElementById('statEvents');
    const statRelations = document.getElementById('statRelations');
    
    if (statChunks) statChunks.textContent = formatNumber(AppState.stats.chunks);
    if (statCharacters) statCharacters.textContent = AppState.stats.characters;
    if (statEvents) statEvents.textContent = AppState.stats.events;
    if (statRelations) statRelations.textContent = AppState.stats.relations;
    
    // Update nav badges
    const navCharacters = document.getElementById('navCharacters');
    const navEvents = document.getElementById('navEvents');
    
    if (navCharacters) navCharacters.textContent = AppState.stats.characters;
    if (navEvents) navEvents.textContent = AppState.stats.events;
}

function updateAnswerMeta(metadata) {
    const meta = elements.answerMeta();
    if (meta) {
        const time = metadata.time || metadata.elapsed || '0';
        const chars = metadata.chars || metadata.character_count || AppState.currentAnswer?.length || 0;
        meta.innerHTML = `<span>⏱️ ${time}s</span><span>📝 ${chars} chars</span>`;
    }
}

function populateDocumentSelect(documents) {
    const select = elements.docSelect();
    if (!select) return;
    
    select.innerHTML = '<option value="">All Documents</option>';
    documents.forEach(doc => {
        const option = document.createElement('option');
        option.value = doc.id || doc.name;
        option.textContent = doc.name;
        select.appendChild(option);
    });
}

function formatAnswer(text) {
    if (!text) return '';
    
    // Convert markdown-like formatting
    let html = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Quotes (lines starting with >)
        .replace(/^> (.+)$/gm, '<div class="quote">$1</div>')
        // Paragraphs
        .split('\n\n').map(p => p.trim() ? `<p>${p}</p>` : '').join('');
    
    // Clean up any remaining single newlines
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

function renderSources(sources) {
    const section = document.getElementById('sourcesSection');
    const grid = elements.sourcesGrid();
    const count = elements.sourcesCount();
    
    if (!grid) return;
    
    if (count) count.textContent = sources.length;
    
    if (sources.length === 0) {
        if (section) section.classList.add('hidden');
        grid.innerHTML = '<p class="text-muted">No sources available</p>';
        return;
    }
    
    if (section) section.classList.remove('hidden');
    
    grid.innerHTML = sources.map((source, index) => `
        <div class="source-card" onclick="showSourceDetail(${index})">
            <div class="source-header">
                <span class="source-index">${index + 1}</span>
                <span class="source-score">${Math.round((source.score || source.relevance || 0.8) * 100)}%</span>
            </div>
            <div class="source-file">${source.document || source.file || source.file_name || 'Unknown'}</div>
            <div class="source-page">Page ${source.page || source.page_number || 'N/A'} ${source.section ? '• ' + source.section : ''}</div>
            <div class="source-preview">${truncateText(source.text || source.content || source.chunk_text || '', 150)}</div>
        </div>
    `).join('');
}

function renderRelatedQuestions(questions) {
    const panel = elements.relatedPanel();
    const list = elements.relatedList();
    
    if (!panel || !list) return;
    
    if (questions.length === 0) {
        panel.classList.add('hidden');
        return;
    }
    
    panel.classList.remove('hidden');
    list.innerHTML = questions.map(q => `
        <div class="related-item" onclick="askQuestion('${escapeHtml(q)}')">${q}</div>
    `).join('');
}

function renderCharacterCard(character) {
    const panel = elements.characterPanel();
    if (!panel) return;

    // Hide tips panel when showing character
    const tipsPanel = document.getElementById('tipsPanel');
    if (tipsPanel) tipsPanel.classList.add('hidden');

    panel.classList.remove('hidden');

    // Normalize relationships to avoid rendering "undefined" pills
    const relationshipsRaw = Array.isArray(character?.relationships) ? character.relationships : [];
    const relationships = relationshipsRaw
        .map((r) => ({
            target: r?.target ?? r?.name,
            relationship_type: r?.relationship_type ?? r?.relation
        }))
        .filter((r) => typeof r.target === 'string' && r.target.trim().length > 0);

    const relationEmojis = {
        'father': '👑', 'mother': '👑', 'parent': '👑',
        'son': '👦', 'daughter': '👧', 'child': '👶',
        'wife': '💕', 'husband': '💕', 'spouse': '💕',
        'brother': '👥', 'sister': '👥', 'sibling': '👥',
        'ally': '🤝', 'friend': '🤝', 'companion': '🤝',
        'enemy': '⚔️', 'rival': '⚔️',
        'servant': '🙏', 'devotee': '🙏',
        'default': '👤'
    };

    const getRelationEmoji = (relation) => {
        const relType = String(relation.relationship_type || '').toLowerCase();
        for (const [key, emoji] of Object.entries(relationEmojis)) {
            if (relType.includes(key)) return emoji;
        }
        return relationEmojis.default;
    };

    panel.innerHTML = `
        <div class="panel-header">
            <div class="panel-title">👤 Character Detected</div>
        </div>
        <div class="panel-body">
            <div class="character-card">
                <div class="character-avatar">${character.name?.charAt(0) || '?'}</div>
                <div class="character-name">${character.name || 'Unknown'}</div>
                <div class="character-title">${character.title || character.description || character.aliases?.join(' • ') || ''}</div>
                ${relationships.length > 0 ? `
                    <div class="character-relations">
                        ${relationships.slice(0, 4).map(r => `
                            <span class="relation-tag" onclick="askQuestion('Who is ${escapeHtml(r.target)}?')">${getRelationEmoji(r)} ${escapeHtml(r.target)}</span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function showSourceDetail(index) {
    const source = AppState.sources[index];
    if (!source) return;
    
    showModal('Source Detail', `
        <div class="source-detail">
            <h3>${source.document || source.file || 'Unknown Document'}</h3>
            <p class="text-muted">Page ${source.page || 'N/A'} ${source.section ? '• ' + source.section : ''}</p>
            <div class="source-full-text" style="margin-top: 16px; padding: 16px; background: var(--bg-tertiary); border-radius: 8px; white-space: pre-wrap;">
                ${source.text || source.content || 'No content available'}
            </div>
        </div>
    `);
}

function showCitationModal(citation) {
    showModal('Citation', `
        <div class="citation-content">
            <pre style="background: var(--bg-tertiary); padding: 16px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap;">${escapeHtml(citation)}</pre>
            <button class="action-btn mt-4" onclick="navigator.clipboard.writeText(\`${escapeHtml(citation)}\`); showToast('Copied!', 'success');">
                📋 Copy Citation
            </button>
        </div>
    `);
}

// ============================================
// AUTOCOMPLETE
// ============================================
let __autocompleteTimer = null;

async function fetchAutocompleteSuggestions(prefix) {
    try {
        const url = new URL(`${window.location.origin}${API_BASE}/api/autocomplete`);
        url.searchParams.set('q', prefix);
        url.searchParams.set('limit', '8');
        const res = await fetch(url.toString());
        if (!res.ok) return [];
        const data = await res.json();
        return Array.isArray(data.suggestions) ? data.suggestions : [];
    } catch (error) {
        return [];
    }
}

function ensureAutocompleteUI() {
    const input = elements.searchInput();
    if (!input) return null;

    let box = document.getElementById('autocompleteBox');
    if (box) return box;

    box = document.createElement('div');
    box.id = 'autocompleteBox';
    box.style.position = 'absolute';
    box.style.zIndex = '9999';
    box.style.background = 'var(--bg-secondary)';
    box.style.border = '1px solid var(--border)';
    box.style.borderRadius = '10px';
    box.style.padding = '6px';
    box.style.display = 'none';
    box.style.maxHeight = '260px';
    box.style.overflowY = 'auto';
    box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.25)';

    document.body.appendChild(box);

    const reposition = () => {
        const r = input.getBoundingClientRect();
        box.style.left = `${r.left + window.scrollX}px`;
        box.style.top = `${r.bottom + window.scrollY + 6}px`;
        box.style.width = `${r.width}px`;
    };

    reposition();
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);

    return box;
}

function hideAutocomplete() {
    const box = document.getElementById('autocompleteBox');
    if (box) box.style.display = 'none';
}

function renderAutocompleteSuggestions(items) {
    const box = ensureAutocompleteUI();
    if (!box) return;

    if (!items || items.length === 0) {
        box.style.display = 'none';
        return;
    }

    box.innerHTML = items.map((s) => {
        const safe = escapeHtml(String(s));
        return `<div class="related-item" data-suggest="${safe}" style="cursor:pointer; padding:10px;">${safe}</div>`;
    }).join('');

    box.querySelectorAll('[data-suggest]').forEach((el) => {
        el.addEventListener('click', () => {
            const input = elements.searchInput();
            const t = el.getAttribute('data-suggest') || '';
            if (input) {
                input.value = t;
                hideAutocomplete();
                input.focus();
            }
        });
    });

    box.style.display = 'block';
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    const resultsArea = elements.resultsArea();
    if (resultsArea) {
        resultsArea.scrollTop = resultsArea.scrollHeight;
    }
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'} ${message}`;
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}

function showError(message) {
    elements.emptyState()?.classList.add('hidden');
    elements.answerCard()?.classList.remove('hidden');
    elements.answerText().innerHTML = `<p style="color: var(--error);">⚠️ ${message}</p>`;
}

function showModal(title, content) {
    let overlay = document.querySelector('.modal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <div class="modal-title"></div>
                    <button class="modal-close" onclick="closeModal()">×</button>
                </div>
                <div class="modal-body"></div>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
    }
    
    overlay.querySelector('.modal-title').textContent = title;
    overlay.querySelector('.modal-body').innerHTML = content;
    overlay.classList.add('active');
}

function closeModal() {
    document.querySelector('.modal-overlay')?.classList.remove('active');
}

// ============================================
// EVENT HANDLERS
// ============================================
function askQuestion(question) {
    const input = elements.searchInput();
    if (input) {
        input.value = question;
        submitQuery(question);
    }
}

function handleRating(rating) {
    document.querySelectorAll('.star').forEach((star, index) => {
        star.classList.toggle('active', index < rating);
    });
    submitFeedback(rating);
}

// Theme functions
function toggleThemeDropdown() {
    const dropdown = elements.themeDropdown();
    dropdown?.classList.toggle('active');
}

function setTheme(themeName, displayName) {
    document.body.className = themeName;
    
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    const nameEl = elements.currentThemeName();
    if (nameEl) nameEl.textContent = displayName;
    
    elements.themeDropdown()?.classList.remove('active');
    
    // Save preference
    localStorage.setItem('epicExplorerTheme', themeName);
    localStorage.setItem('epicExplorerThemeName', displayName);
}

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('epicExplorerTheme');
    const savedName = localStorage.getItem('epicExplorerThemeName');
    
    if (savedTheme !== null) {
        document.body.className = savedTheme;
        const nameEl = elements.currentThemeName();
        if (nameEl && savedName) nameEl.textContent = savedName;
        
        // Update active button
        document.querySelectorAll('.theme-btn').forEach(btn => {
            const btnTheme = btn.getAttribute('onclick')?.match(/setTheme\('([^']*)/)?.[1] || '';
            btn.classList.toggle('active', btnTheme === savedTheme);
        });
    }
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Load saved theme
    loadSavedTheme();
    
    // Check LLM status
    checkLLMStatus();
    setInterval(checkLLMStatus, 30000); // Check every 30 seconds
    
    // Fetch initial data
    fetchStats();
    fetchDocuments();
    
    // Search input handlers + autocomplete
    const searchInput = elements.searchInput();
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                hideAutocomplete();
                submitQuery(searchInput.value);
            } else if (e.key === 'Escape') {
                hideAutocomplete();
            }
        });

        searchInput.addEventListener('input', () => {
            const q = (searchInput.value || '').trim();
            clearTimeout(__autocompleteTimer);

            if (q.length < 2) {
                hideAutocomplete();
                return;
            }

            __autocompleteTimer = setTimeout(async () => {
                const suggestions = await fetchAutocompleteSuggestions(q);
                renderAutocompleteSuggestions(suggestions);
            }, 180);
        });

        searchInput.addEventListener('blur', () => {
            // Small timeout so click on dropdown registers
            setTimeout(() => hideAutocomplete(), 150);
        });
    }

    // Ask button handler
    const searchBtn = elements.searchBtn();
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            hideAutocomplete();
            submitQuery(searchInput.value);
        });
    }

    // Wire top-right icon buttons (settings/history/help)
    document.querySelectorAll('.header-actions .icon-btn').forEach((btn) => {
        const title = (btn.getAttribute('title') || '').toLowerCase();
        if (title.includes('settings')) {
            btn.addEventListener('click', () => {
                showModal('Settings', `
                    <div class="text-muted" style="line-height:1.6;">
                        <div><strong>Stream response</strong>: toggle in the search options</div>
                        <div><strong>Include sources</strong>: toggle in the search options</div>
                        <div><strong>Deep search</strong>: enables multi-hop retrieval</div>
                        <div style="margin-top:12px;"><strong>Theme</strong>: use the palette dropdown in the header</div>
                    </div>
                `);
            });
        } else if (title.includes('history')) {
            btn.addEventListener('click', () => {
                showModal('History', `<div class="text-muted">Query history UI is not enabled yet.</div>`);
            });
        } else if (title.includes('help')) {
            btn.addEventListener('click', () => {
                showModal('Help', `
                    <div style="line-height:1.6;">
                        <div><strong>Autocomplete:</strong> start typing a character name to see suggestions.</div>
                        <div><strong>Sources:</strong> click a source card to view the full text.</div>
                        <div><strong>Related questions:</strong> click to ask follow-ups.</div>
                    </div>
                `);
            });
        }
    });

    // Toggle retrieval debug overlay with keypress: "D"
    document.addEventListener('keydown', (e) => {
        if (e.key === 'd' || e.key === 'D') {
            // Avoid hijacking typing inside inputs/textareas
            const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
            if (tag === 'input' || tag === 'textarea') return;
            toggleRetrievalDebug();
        }
    });
});

// Export functions for HTML onclick handlers
window.askQuestion = askQuestion;
window.submitQuery = submitQuery;
window.copyAnswer = copyAnswer;
window.exportAnswer = exportAnswer;
window.getCitation = getCitation;
window.handleRating = handleRating;
window.toggleThemeDropdown = toggleThemeDropdown;
window.setTheme = setTheme;
window.closeModal = closeModal;
window.showSourceDetail = showSourceDetail;
window.showToast = showToast;
window.toggleRetrievalDebug = toggleRetrievalDebug;
