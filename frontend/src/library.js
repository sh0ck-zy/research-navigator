import * as THREE from 'three';
import { state } from './state.js';
import { bibtex } from './bibtex.js';

// Library: save papers (SQLite via /api/library), mark them on the map with
// additive gold rings (never hides other papers), and a Library panel.

let idIndex = null;
function getIdIndex() {
    if (!idIndex) {
        idIndex = new Map();
        state.allPapers.forEach((p, i) => idIndex.set(p.id, i));
    }
    return idIndex;
}

let ringTex = null;
function ringTexture() {
    if (ringTex) return ringTex;
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const ctx = c.getContext('2d');
    ctx.strokeStyle = 'rgba(255,255,255,1)';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(32, 32, 24, 0, Math.PI * 2);
    ctx.stroke();
    ringTex = new THREE.CanvasTexture(c);
    return ringTex;
}

export async function loadSaved() {
    try {
        const res = await fetch('/api/library');
        if (res.ok) {
            const data = await res.json();
            state.savedIds = new Set(data.papers.map(p => p.paper_id));
        }
    } catch (e) {
        // offline / no backend — keep empty, app still works
    }
    markSavedOnMap();
    updateLibCount();
}

export async function toggleSave(idx) {
    const p = state.allPapers[idx];
    if (!p) return;
    const saving = !state.savedIds.has(p.id);

    // optimistic update
    if (saving) state.savedIds.add(p.id); else state.savedIds.delete(p.id);
    refreshSaveButton(idx);
    markSavedOnMap();
    updateLibCount();
    if (isLibraryOpen()) renderLibraryPanel();

    try {
        if (saving) {
            await fetch('/api/library', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: p.id, title: p.title, authors: p.authors,
                    year: p.year, cited_by_count: p.cited_by_count,
                    doi: p.doi, venue: p.venue, cluster_name: p._cl.name,
                }),
            });
        } else {
            await fetch(`/api/library/${encodeURIComponent(p.id)}`, { method: 'DELETE' });
        }
    } catch (e) {
        // revert on failure
        if (saving) state.savedIds.delete(p.id); else state.savedIds.add(p.id);
        refreshSaveButton(idx);
        markSavedOnMap();
        updateLibCount();
        if (isLibraryOpen()) renderLibraryPanel();
    }
}

export function copyCite(idx, btn) {
    const p = state.allPapers[idx];
    if (!p) return;
    navigator.clipboard.writeText(bibtex(p)).then(() => {
        if (btn) {
            const old = btn.textContent;
            btn.textContent = 'Copied ✓';
            setTimeout(() => { btn.textContent = old; }, 1200);
        }
    }).catch(() => {});
}

function refreshSaveButton(idx) {
    const btn = document.getElementById('ni-save');
    if (btn && Number(btn.dataset.idx) === idx) {
        const p = state.allPapers[idx];
        const saved = state.savedIds.has(p.id);
        btn.textContent = saved ? 'Saved ✓' : 'Save';
        btn.classList.toggle('saved', saved);
    }
}

export function markSavedOnMap() {
    if (state.savedRings) { state.scene.remove(state.savedRings); state.savedRings = null; }
    if (!state.savedIds.size || !state.scene) return;
    const group = new THREE.Group();
    const tex = ringTexture();
    const lut = getIdIndex();
    state.savedIds.forEach(id => {
        const i = lut.get(id);
        if (i === undefined) return;
        const p = state.allPapers[i];
        const mat = new THREE.SpriteMaterial({
            map: tex, color: 0xffd479, transparent: true, opacity: 0.9,
            depthWrite: false, blending: THREE.AdditiveBlending,
        });
        const s = new THREE.Sprite(mat);
        s.position.set(p._x, p._y, p._z);
        s.scale.set(16, 16, 1);
        group.add(s);
    });
    state.scene.add(group);
    state.savedRings = group;
}

function updateLibCount() {
    const el = document.getElementById('lib-count');
    if (el) el.textContent = state.savedIds.size ? `(${state.savedIds.size})` : '';
}

// === Library panel ===
function isLibraryOpen() {
    const panel = document.getElementById('library-panel');
    return panel && panel.classList.contains('visible');
}

export function openLibrary() {
    renderLibraryPanel();
    const panel = document.getElementById('library-panel');
    panel.style.display = 'block';
    requestAnimationFrame(() => panel.classList.add('visible'));
    document.getElementById('nav-library').classList.add('active');
    document.getElementById('nav-explore').classList.remove('active');
}

export function closeLibrary() {
    const panel = document.getElementById('library-panel');
    panel.classList.remove('visible');
    setTimeout(() => { panel.style.display = 'none'; }, 300);
    document.getElementById('nav-library').classList.remove('active');
    document.getElementById('nav-explore').classList.add('active');
}

export function renderLibraryPanel() {
    const panel = document.getElementById('library-panel');
    const lut = getIdIndex();
    const items = [...state.savedIds]
        .map(id => lut.get(id))
        .filter(i => i !== undefined)
        .map(i => ({ p: state.allPapers[i], i }));

    const header = `
        <div class="lib-header">
            <div class="lib-title">Library <span class="lib-sub">${items.length}</span></div>
            <div class="lib-head-actions">
                ${items.length ? `<a class="lib-export" href="/api/library/export.bib" download="observatory-library.bib">Export .bib</a>` : ''}
                <button class="lib-close" onclick="closeLibrary()">&times;</button>
            </div>
        </div>`;

    let body;
    if (!items.length) {
        body = `<div class="lib-empty">No saved papers yet.<br>Click a paper, then <b>Save</b>.</div>`;
    } else {
        body = items.map(({ p, i }) => `
            <div class="lib-item">
                <div class="lib-dot" style="background:${p._cl.color}"></div>
                <div class="lib-info" onclick="closeLibrary();searchNavigate(${i})">
                    <div class="lib-item-title">${p.title}</div>
                    <div class="lib-item-meta">${p._cl.name} · ${p.year || ''}</div>
                </div>
                <button class="lib-remove" title="Remove" onclick="toggleSave(${i})">&times;</button>
            </div>`).join('');
    }
    panel.innerHTML = header + `<div class="lib-body">${body}</div>`;
}
