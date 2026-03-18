/* ═══════════════════════════════════════════════════════════════
   ScholarMind — Frontend Application Logic
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = '';

// ── Initialization ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initUploadZone();
    initParticles();
    initChatInput();
    checkHealth();
});

// ── Tab Navigation ────────────────────────────────────────────────
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;

            // Update buttons
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`content${capitalize(tab)}`).classList.add('active');
        });
    });

    // Enter key for search
    document.getElementById('searchInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
    });
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Health Check ──────────────────────────────────────────────────
async function checkHealth() {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');

    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();

        if (data.endee === 'connected') {
            dot.className = 'status-dot connected';
            text.textContent = data.llm === 'configured' ? 'Endee + LLM Ready' : 'Endee Connected';
        } else {
            dot.className = 'status-dot error';
            text.textContent = 'Endee Disconnected';
        }
    } catch {
        dot.className = 'status-dot error';
        text.textContent = 'Server Offline';
    }
}

// ── Semantic Search ───────────────────────────────────────────────
async function performSearch() {
    const input = document.getElementById('searchInput');
    const query = input.value.trim();
    if (!query) return;

    const results = document.getElementById('searchResults');
    const meta = document.getElementById('searchMeta');

    results.innerHTML = `
        <div class="empty-state">
            <div class="spinner" style="width:32px;height:32px;border-width:3px;margin:0 auto"></div>
            <h3 style="margin-top:16px">Searching...</h3>
            <p>Finding semantically similar passages</p>
        </div>`;

    try {
        const res = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: 10 }),
        });

        const data = await res.json();

        if (data.error) {
            results.innerHTML = errorState(data.error);
            meta.textContent = '';
            return;
        }

        if (!data.results || data.results.length === 0) {
            results.innerHTML = `
                <div class="empty-state">
                    <h3>No results found</h3>
                    <p>Try uploading some documents first, or use a different search query.</p>
                </div>`;
            meta.textContent = '';
            return;
        }

        meta.textContent = `${data.total} results for "${query}"`;
        results.innerHTML = data.results.map((r, i) => resultCard(r, i)).join('');

    } catch (err) {
        results.innerHTML = errorState('Could not connect to the server. Is it running?');
        meta.textContent = '';
    }
}

function resultCard(result, index) {
    const sim = (result.similarity * 100).toFixed(1);
    const delay = index * 50;

    return `
        <div class="result-card" style="animation-delay:${delay}ms">
            <div class="result-header">
                <span class="result-source">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
                    </svg>
                    ${escapeHtml(result.source)}
                </span>
                <span class="result-similarity">
                    ${sim}%
                    <span class="similarity-bar">
                        <span class="similarity-fill" style="width:${sim}%"></span>
                    </span>
                </span>
            </div>
            <div class="result-text">${escapeHtml(result.text)}</div>
            ${result.category !== 'general' ? `<span class="result-badge">${escapeHtml(result.category)}</span>` : ''}
        </div>`;
}

function errorState(msg) {
    return `
        <div class="empty-state">
            <h3 style="color:var(--accent-rose)">Error</h3>
            <p>${escapeHtml(msg)}</p>
        </div>`;
}

// ── RAG Chat ──────────────────────────────────────────────────────
function initChatInput() {
    const input = document.getElementById('chatInput');

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // Enter to send (Shift+Enter for newline)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            askQuestion();
        }
    });
}

async function askQuestion() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    if (!query) return;

    const messages = document.getElementById('chatMessages');
    const sendBtn = document.getElementById('chatSendBtn');

    // Remove welcome state
    const welcome = messages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user message
    messages.innerHTML += userBubble(query);

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add typing indicator
    const typingId = 'typing-' + Date.now();
    messages.innerHTML += assistantTyping(typingId);
    scrollToBottom(messages);

    sendBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, top_k: 5 }),
        });

        const data = await res.json();

        // Remove typing indicator
        const typing = document.getElementById(typingId);
        if (typing) typing.remove();

        if (data.error) {
            messages.innerHTML += assistantBubble(data.error, [], []);
        } else {
            messages.innerHTML += assistantBubble(
                data.answer,
                data.sources || [],
                data.context_chunks || []
            );
        }

    } catch (err) {
        const typing = document.getElementById(typingId);
        if (typing) typing.remove();
        messages.innerHTML += assistantBubble(
            'Could not connect to the server. Please make sure it is running.',
            [], []
        );
    }

    sendBtn.disabled = false;
    scrollToBottom(messages);
}

function userBubble(text) {
    return `
        <div class="chat-message user">
            <div class="chat-avatar">U</div>
            <div class="chat-bubble">${escapeHtml(text)}</div>
        </div>`;
}

function assistantTyping(id) {
    return `
        <div class="chat-message assistant" id="${id}">
            <div class="chat-avatar">AI</div>
            <div class="chat-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>`;
}

function assistantBubble(text, sources, contextChunks) {
    const chunkId = 'ctx-' + Date.now();
    let sourcesHtml = '';
    let contextHtml = '';

    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="chat-sources">
                <div class="chat-sources-title">Sources</div>
                ${sources.map(s => `<span class="source-tag">📄 ${escapeHtml(s.name)} (${(s.similarity * 100).toFixed(0)}%)</span>`).join('')}
            </div>`;
    }

    if (contextChunks && contextChunks.length > 0) {
        contextHtml = `
            <div class="context-chunks">
                <button class="context-toggle" onclick="toggleContext('${chunkId}', this)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                    Show retrieved passages (${contextChunks.length})
                </button>
                <div class="context-list" id="${chunkId}">
                    ${contextChunks.map(c => `
                        <div class="context-item">
                            <div class="context-item-header">
                                <span>📄 ${escapeHtml(c.source)}</span>
                                <span>${(c.similarity * 100).toFixed(1)}% match</span>
                            </div>
                            ${escapeHtml(c.text)}
                        </div>`).join('')}
                </div>
            </div>`;
    }

    // Format markdown-like content
    const formattedText = formatAnswer(text);

    return `
        <div class="chat-message assistant">
            <div class="chat-avatar">AI</div>
            <div class="chat-bubble">
                ${formattedText}
                ${sourcesHtml}
                ${contextHtml}
            </div>
        </div>`;
}

function toggleContext(id, btn) {
    const el = document.getElementById(id);
    el.classList.toggle('visible');
    btn.classList.toggle('open');
}

function formatAnswer(text) {
    // Simple markdown-like formatting
    let html = escapeHtml(text);

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    // Bullet points
    html = html.replace(/^- (.*?)(<br>|$)/gm, '• $1$2');

    return html;
}

function scrollToBottom(el) {
    setTimeout(() => {
        el.scrollTop = el.scrollHeight;
    }, 50);
}

// ── File Upload ───────────────────────────────────────────────────
function initUploadZone() {
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
            fileInput.value = '';
        }
    });
}

async function uploadFile(file) {
    const status = document.getElementById('uploadStatus');
    const category = document.getElementById('categorySelect').value;

    status.className = 'upload-status visible';
    status.innerHTML = `
        <div class="status-message loading">
            <div class="spinner"></div>
            Uploading and indexing "${escapeHtml(file.name)}"...
        </div>`;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await res.json();

        if (data.error) {
            status.innerHTML = `<div class="status-message error">✕ ${escapeHtml(data.error)}</div>`;
        } else {
            status.innerHTML = `<div class="status-message success">✓ ${escapeHtml(data.message)} (${data.chunks} chunks indexed)</div>`;
            checkHealth();
        }

    } catch (err) {
        status.innerHTML = `<div class="status-message error">✕ Upload failed. Is the server running?</div>`;
    }
}

// ── Sample Documents ──────────────────────────────────────────────
async function loadSampleDocs() {
    const btn = document.getElementById('loadSamplesBtn');
    const status = document.getElementById('uploadStatus');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Loading samples...';

    status.className = 'upload-status visible';
    status.innerHTML = `
        <div class="status-message loading">
            <div class="spinner"></div>
            Loading and indexing sample documents...
        </div>`;

    const sampleFiles = [
        { path: 'sample_docs/artificial_intelligence_overview.md', name: 'artificial_intelligence_overview.md', category: 'technology' },
        { path: 'sample_docs/vector_databases_guide.md', name: 'vector_databases_guide.md', category: 'technology' },
    ];

    let successCount = 0;
    let totalChunks = 0;

    for (const sample of sampleFiles) {
        try {
            // Fetch the sample file
            const fileRes = await fetch(`/${sample.path}`);
            if (!fileRes.ok) continue;

            const blob = await fileRes.blob();
            const file = new File([blob], sample.name, { type: 'text/markdown' });

            const formData = new FormData();
            formData.append('file', file);
            formData.append('category', sample.category);

            const res = await fetch(`${API_BASE}/api/upload`, {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();
            if (!data.error) {
                successCount++;
                totalChunks += data.chunks || 0;
            }
        } catch (err) {
            console.error('Failed to load sample:', sample.name, err);
        }
    }

    if (successCount > 0) {
        status.innerHTML = `<div class="status-message success">✓ Loaded ${successCount} sample documents (${totalChunks} chunks indexed). Try searching!</div>`;
    } else {
        status.innerHTML = `<div class="status-message error">✕ Failed to load sample documents. Make sure the server is running.</div>`;
    }

    btn.disabled = false;
    btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        Load Sample Documents`;

    checkHealth();
}

// ── Background Particles ──────────────────────────────────────────
function initParticles() {
    const container = document.getElementById('bgParticles');
    const colors = ['rgba(167, 139, 250, 0.3)', 'rgba(6, 182, 212, 0.3)', 'rgba(52, 211, 153, 0.25)'];

    for (let i = 0; i < 15; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        const size = Math.random() * 3 + 1;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];
        particle.style.animationDuration = (Math.random() * 15 + 10) + 's';
        particle.style.animationDelay = (Math.random() * 10) + 's';
        container.appendChild(particle);
    }
}

// ── Utilities ─────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
