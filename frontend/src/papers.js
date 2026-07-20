// papers.js — paper focus render effects (star growth, gravitational push,
// citation lines) + the paper dock card. Selection state lives in machine.js.

import * as THREE from 'three';
import { state } from './state.js';
import { toggleSave, copyCite } from './library.js';

let conLines = null;
const grownStars = new Map(); // idx -> original size, so any grown star can be restored

// === CITATION LINES (focused node only) ===
export function drawLines(ci) {
    removeLines();
    const allPapers = state.allPapers;
    const ctr = allPapers[ci];
    const nbs = allPapers
        .map((p, i) => ({ p, i, d: Math.hypot(p._x - ctr._x, p._y - ctr._y, p._z - ctr._z) }))
        .filter(o => o.i !== ci).sort((a, b) => a.d - b.d).slice(0, 6);
    const pos = [], cols = [];
    const cc = new THREE.Color(ctr._cl.color);
    nbs.forEach(({ p }) => {
        const nc = new THREE.Color(p._cl.color);
        pos.push(ctr._x, ctr._y, ctr._z, p._x, p._y, p._z);
        cols.push(cc.r, cc.g, cc.b, nc.r, nc.g, nc.b);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    conLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    state.scene.add(conLines);
}

export function removeLines() {
    if (conLines) { state.scene.remove(conLines); conLines = null; }
}

// === PAPER DOCK CARD ===
export function paperCardHtml(p, idx) {
    const clPapers = state.allPapers.filter(q => q._cl.id === p._cl.id);
    const rank = clPapers.filter(q => (q._centrality || 0) <= (p._centrality || 0)).length;
    const percentile = Math.round((rank / clPapers.length) * 100);

    const rawAbstract = (p.abstract || '').replace(/\n/g, ' ').trim();
    const sentences = rawAbstract.match(/[^.!?]+[.!?]+/g) || [];
    let shortAbstract = sentences.slice(0, 3).join(' ').trim();
    if (shortAbstract.length > 320) shortAbstract = shortAbstract.slice(0, 317) + '…';
    if (!shortAbstract && rawAbstract) shortAbstract = rawAbstract.slice(0, 317) + '…';

    const auth = p.authors ? p.authors.split(/,| and /).slice(0, 3).map(s => s.trim()).join(', ') : '';
    const saved = state.savedIds.has(p.id);

    return `
        <div class="dock-header">
            <div class="dock-kicker" style="color:${p._cl.color}"><span class="dock-dot" style="background:${p._cl.color}"></span>${p._cl.name}</div>
            <div class="dock-title paper">${p.title}</div>
            <div class="dock-desc">${auth}${p.year ? ' · ' + p.year : ''}${p.venue ? ' · ' + p.venue : ''}</div>
            <div class="dock-chip" style="background:${p._cl.color}15;color:${p._cl.color}">Top ${100 - percentile}% of its territory</div>
        </div>
        <div class="dock-section">
            <div class="dock-abstract">${shortAbstract}</div>
        </div>
        <div class="dock-actions row">
            <button class="dock-btn${saved ? ' saved' : ''}" id="dock-save">${saved ? 'Saved ✓' : 'Save'}</button>
            <button class="dock-btn" id="dock-cite">Cite</button>
            <a class="dock-btn" href="${p.doi ? 'https://doi.org/' + p.doi : 'https://arxiv.org/abs/' + p.id}" target="_blank" rel="noopener">Open ↗</a>
        </div>
    `;
}

export function wirePaperCard(p, idx) {
    document.getElementById('dock-save')?.addEventListener('click', () => toggleSave(idx));
    document.getElementById('dock-cite')?.addEventListener('click', ev => copyCite(idx, ev.target));
}

// === FOCUS EFFECTS ===
// prevIdx: the paper that was focused before this one (-1 if none). Its
// star size is restored before the new selection grows.
export function selectPaperFx(p, idx, prevIdx = -1) {
    if (prevIdx >= 0) restoreStar(prevIdx); // safe no-op if it wasn't grown

    // Force-reset any lingering pushed papers
    if (state.pushedPapers.length > 0) {
        const posArr = state.ptsGeo.attributes.position.array;
        state.pushedPapers.forEach(pp => {
            posArr[pp.index * 3] = pp.origX; posArr[pp.index * 3 + 1] = pp.origY; posArr[pp.index * 3 + 2] = pp.origZ;
        });
        state.ptsGeo.attributes.position.needsUpdate = true;
        state.pushedPapers = [];
        state.pushDirection = 0;
        state.pushProgress = 0;
    }

    const sizeArr = state.ptsGeo.attributes.size.array;
    if (!grownStars.has(idx)) grownStars.set(idx, sizeArr[idx]);
    sizeArr[idx] = sizeArr[idx] * 4.5;
    state.ptsGeo.attributes.size.needsUpdate = true;

    // Gravitational push: 12 nearest neighbors move aside
    const PUSH_DIST = 18;
    const posArr = state.ptsGeo.attributes.position.array;
    const neighbors = state.allPapers
        .map((q, i) => ({ i, d: Math.hypot(q._x - p._x, q._y - p._y, q._z - p._z) }))
        .filter(o => o.i !== idx).sort((a, b) => a.d - b.d).slice(0, 12);
    state.pushedPapers = neighbors.map(({ i: ni }) => {
        const ox = state.allPapers[ni]._x, oy = state.allPapers[ni]._y, oz = state.allPapers[ni]._z;
        posArr[ni * 3] = ox; posArr[ni * 3 + 1] = oy; posArr[ni * 3 + 2] = oz;
        const dx = ox - p._x, dy = oy - p._y, dz = oz - p._z;
        const len = Math.hypot(dx, dy, dz) || 1;
        return { index: ni, origX: ox, origY: oy, origZ: oz,
            targetX: ox + (dx / len) * PUSH_DIST, targetY: oy + (dy / len) * PUSH_DIST, targetZ: oz + (dz / len) * PUSH_DIST };
    });
    state.pushProgress = 0;
    state.pushDirection = 1;

    drawLines(idx);
}

function restoreStar(idx) {
    if (!grownStars.has(idx)) return;
    state.ptsGeo.attributes.size.array[idx] = grownStars.get(idx);
    grownStars.delete(idx);
    state.ptsGeo.attributes.size.needsUpdate = true;
}

export function deselectPaperFx(idx = -1) {
    if (idx >= 0) restoreStar(idx);
    state.pushDirection = -1; // loop lerps back
    removeLines();
}
