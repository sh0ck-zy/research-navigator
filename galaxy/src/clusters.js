// clusters.js — cluster render effects (connection lines, bridge labels,
// king papers) + the cluster dock card. All navigation intent goes through
// the machine; this module never moves the camera.

import * as THREE from 'three';
import { state, SPREAD } from './state.js';
import { machine } from './machine.js';
import { clusterWorldPos } from './camera.js';

export function getCluster(cid) {
    return state.mapData.clusters.find(c => c.id === cid);
}

// === CLUSTER DOCK CARD ===
export function clusterCardHtml(cl) {
    const totalPapers = state.mapData.metadata.paper_count;
    const share = (cl.paper_count / totalPapers * 100).toFixed(1);
    const desc = cl.description ? cl.description.split('.').slice(0, 2).join('.') + '.' : '';
    const kings = state.allPapers.filter(p => p._cl.id === cl.id)
        .sort((a, b) => (b._centrality || 0) - (a._centrality || 0)).slice(0, 3);

    const yearCounts = {};
    cl.papers.forEach(p => { if (p.year) yearCounts[p.year] = (yearCounts[p.year] || 0) + 1; });
    const years = Object.keys(yearCounts).sort().slice(-8);
    const maxYC = Math.max(...years.map(y => yearCounts[y]), 1);

    const conns = (state.mapData.connections || [])
        .filter(c => c.from === cl.id || c.to === cl.id)
        .map(c => {
            const other = getCluster(c.from === cl.id ? c.to : c.from);
            return other ? { cluster: other, strength: c.strength } : null;
        })
        .filter(Boolean).sort((a, b) => b.strength - a.strength).slice(0, 3);

    return `
        <div class="dock-header">
            <div class="dock-kicker">Territory</div>
            <div class="dock-title"><span class="dock-dot" style="background:${cl.color}"></span>${cl.name}</div>
            <div class="dock-desc">${desc}</div>
        </div>
        <div class="dock-stats">
            <div class="dock-stat"><div class="dock-stat-val">${cl.paper_count.toLocaleString()}</div><div class="dock-stat-lbl">Papers</div></div>
            <div class="dock-stat"><div class="dock-stat-val" style="color:${cl.color}">${share}%</div><div class="dock-stat-lbl">Share</div></div>
            <div class="dock-stat"><div class="dock-stat-val">${years[0] || ''}–${years[years.length - 1] || ''}</div><div class="dock-stat-lbl">Span</div></div>
        </div>
        ${years.length > 1 ? `
        <div class="dock-section">
            <div class="dock-section-title">Trend</div>
            <div class="dock-trend">
                ${years.map(y => `<div class="dock-trend-bar" title="${y}" style="height:${Math.max(2, (yearCounts[y] / maxYC) * 26)}px;background:${cl.color}60"></div>`).join('')}
            </div>
            <div class="dock-trend-years"><span>${years[0]}</span><span>${years[years.length - 1]}</span></div>
        </div>` : ''}
        <div class="dock-section">
            <div class="dock-section-title">Key papers</div>
            ${kings.map(p => `<div class="dock-king"><div class="dock-king-dot" style="background:${cl.color}"></div><div class="dock-king-title">${p.title}</div></div>`).join('')}
        </div>
        ${conns.length ? `
        <div class="dock-section">
            <div class="dock-section-title">Connected areas</div>
            <div class="dock-conns">${conns.map(c => `<span class="dock-conn" data-cid="${c.cluster.id}" style="color:${c.cluster.color};border-color:${c.cluster.color}30;background:${c.cluster.color}08"><span class="dock-conn-dot" style="background:${c.cluster.color}"></span>${c.cluster.name}</span>`).join('')}</div>
        </div>` : ''}
        <div class="dock-actions">
            <button class="dock-btn-primary" id="dock-intel-btn">Cluster intelligence →</button>
        </div>
    `;
}

export function wireClusterCard(cl) {
    document.getElementById('dock-intel-btn')?.addEventListener('click', () => machine.openIntel());
    document.querySelectorAll('.dock-conn').forEach(el => {
        el.addEventListener('click', () => machine.enterCluster(parseInt(el.dataset.cid)));
    });
}

// === INTER-CLUSTER CONNECTION LINES ===
let clusterConLines = null;

export function drawClusterConnections(clId) {
    removeClusterConnections();
    const conns = (state.mapData.connections || []).filter(c => c.from === clId || c.to === clId);
    if (!conns.length) return;
    const cl = getCluster(clId);
    if (!cl) return;
    const from = clusterWorldPos(cl);
    const pos = [], cols = [];
    const fc = new THREE.Color(cl.color);
    conns.forEach(c => {
        const other = getCluster(c.from === clId ? c.to : c.from);
        if (!other) return;
        const to = clusterWorldPos(other);
        const tc = new THREE.Color(other.color);
        pos.push(from.x, from.y, from.z, to.x, to.y, to.z);
        cols.push(fc.r, fc.g, fc.b, tc.r, tc.g, tc.b);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    clusterConLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.35,
        blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    state.scene.add(clusterConLines);
}

export function removeClusterConnections() {
    if (clusterConLines) { state.scene.remove(clusterConLines); clusterConLines = null; }
}

// === BRIDGE LABELS ===
export function buildBridgeLabels(clId) {
    clearBridgeLabels();
    const cl = getCluster(clId);
    if (!cl) return;
    const from = clusterWorldPos(cl);
    const fromV = new THREE.Vector3(from.x, from.y, from.z);
    (state.mapData.connections || [])
        .filter(c => c.from === clId || c.to === clId)
        .sort((a, b) => b.strength - a.strength)
        .slice(0, 3)
        .forEach(c => {
            const other = getCluster(c.from === clId ? c.to : c.from);
            if (!other) return;
            const t = clusterWorldPos(other);
            const mid = fromV.clone().lerp(new THREE.Vector3(t.x, t.y, t.z), 0.5);
            const el = document.createElement('div');
            el.className = 'bridge-label';
            el.textContent = other.name;
            el.style.color = other.color;
            document.body.appendChild(el);
            requestAnimationFrame(() => el.classList.add('visible'));
            state.bridgeLabels.push({ el, pos: mid });
        });
}

export function clearBridgeLabels() {
    state.bridgeLabels.forEach(({ el }) => el.remove());
    state.bridgeLabels = [];
}

// === KING PAPERS ===
export function showKingPapers(cl) {
    hideKingPapers();
    const clPapers = state.allPapers.map((p, i) => ({ p, i }))
        .filter(o => o.p._cl.id === cl.id)
        .sort((a, b) => b.p._centrality - a.p._centrality).slice(0, 3);
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    clPapers.forEach(({ p, i }) => {
        state.kingPapers.push({ index: i, origSize: sizeArr[i], origOpacity: opaArr[i] });
        const base = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        sizeArr[i] = base * 1.4 * 3;
        opaArr[i] = 1.0;
        const el = document.createElement('div');
        el.className = 'king-label';
        el.textContent = p.title.length > 45 ? p.title.slice(0, 42) + '…' : p.title;
        el.style.borderLeft = '2px solid ' + cl.color;
        document.body.appendChild(el);
        requestAnimationFrame(() => el.classList.add('visible'));
        state.kingLabelEls.push({ el, index: i });
    });
    state.ptsGeo.attributes.size.needsUpdate = true;
    state.ptsGeo.attributes.opacity.needsUpdate = true;
}

export function hideKingPapers() {
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    state.kingPapers.forEach(kp => {
        sizeArr[kp.index] = kp.origSize;
        opaArr[kp.index] = kp.origOpacity;
    });
    if (state.kingPapers.length) {
        state.ptsGeo.attributes.size.needsUpdate = true;
        state.ptsGeo.attributes.opacity.needsUpdate = true;
    }
    state.kingPapers = [];
    state.kingLabelEls.forEach(({ el }) => el.remove());
    state.kingLabelEls = [];
}
