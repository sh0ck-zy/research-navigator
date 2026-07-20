// library.js — saved papers: gold ring markers on the map + a dock panel.
// The library is an overlay on the current mode, not a mode itself.

import * as THREE from 'three';
import { state } from './state.js';
import { machine } from './machine.js';
import { dock } from './dock.js';
import { bibtex } from './bibtex.js';

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
    } catch (e) { /* offline — explore-only mode */ }
    markSavedOnMap();
    updateLibCount();
}

export async function toggleSave(idx) {
    const p = state.allPapers[idx];
    if (!p) return;
    const saving = !state.savedIds.has(p.id);

    if (saving) state.savedIds.add(p.id); else state.savedIds.delete(p.id);
    markSavedOnMap();
    updateLibCount();
    refreshSaveUI(idx);

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
        if (saving) state.savedIds.delete(p.id); else state.savedIds.add(p.id);
        markSavedOnMap();
        updateLibCount();
        refreshSaveUI(idx);
    }
}

function refreshSaveUI(idx) {
    // Paper dock card save button
    const btn = document.getElementById('dock-save');
    if (btn && machine.get().paperIdx === idx) {
        const p = state.allPapers[idx];
        const saved = state.savedIds.has(p.id);
        btn.textContent = saved ? 'Saved ✓' : 'Save';
        btn.classList.toggle('saved', saved);
    }
    // Library panel, if open
    if (dock.current() === 'library') openLibrary();
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
        const s = new THREE.Sprite(new THREE.SpriteMaterial({
            map: tex, color: 0xffd479, transparent: true, opacity: 0.9,
            depthWrite: false, blending: THREE.AdditiveBlending,
        }));
        s.position.set(p._x, p._y, p._z);
        s.scale.set(16, 16, 1);
        group.add(s);
    });
    state.scene.add(group);
    state.savedRings = group;
}

function updateLibCount() {
    const el = document.getElementById('lib-count');
    if (el) el.textContent = state.savedIds.size ? ` (${state.savedIds.size})` : '';
}

// === Library dock panel ===
export function openLibrary() {
    const lut = getIdIndex();
    const items = [...state.savedIds]
        .map(id => lut.get(id))
        .filter(i => i !== undefined)
        .map(i => ({ p: state.allPapers[i], i }));

    dock.show('library', `
        <div class="dock-header">
            <div class="dock-kicker">Saved</div>
            <div class="dock-title">Library <span class="dock-desc">${items.length}</span></div>
        </div>
        ${items.length ? `<div class="dock-actions"><a class="dock-btn" href="/api/library/export.bib" download="nav-library.bib">Export .bib</a></div>` : ''}
        <div class="dock-section">
            ${items.length === 0 ? `<div class="dock-desc">No saved papers yet.<br>Click a star, then <b>Save</b>.</div>` : ''}
            ${items.map(({ p, i }) => `
                <div class="lib-item" data-idx="${i}">
                    <div class="lib-dot" style="background:${p._cl.color}"></div>
                    <div class="lib-info">
                        <div class="lib-item-title">${p.title}</div>
                        <div class="lib-item-meta">${p._cl.name} · ${p.year || ''}</div>
                    </div>
                    <button class="lib-remove" data-idx="${i}" title="Remove">&times;</button>
                </div>`).join('')}
        </div>
    `);

    document.querySelectorAll('.lib-item .lib-info').forEach(el => {
        el.addEventListener('click', () => {
            const idx = parseInt(el.parentElement.dataset.idx);
            machine.focusPaper(idx, 'library');
        });
    });
    document.querySelectorAll('.lib-remove').forEach(el => {
        el.addEventListener('click', ev => {
            ev.stopPropagation();
            toggleSave(parseInt(el.dataset.idx));
        });
    });
}
