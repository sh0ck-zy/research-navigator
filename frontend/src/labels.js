// labels.js — cluster labels on the map + star dimming (dimExcept).
// Labels emit intents to the machine; they never navigate themselves.

import * as THREE from 'three';
import { state, SPREAD } from './state.js';
import { machine } from './machine.js';
import { clusterWorldPos } from './camera.js';

export function makeLabels() {
    const el = document.getElementById('labels');
    el.innerHTML = '';
    const counts = state.mapData.clusters.filter(c => c.id !== -1).map(c => c.paper_count);
    const minC = Math.min(...counts), maxC = Math.max(...counts);
    state.mapData.clusters.forEach(cl => {
        if (cl.id === -1) return;
        const d = document.createElement('div');
        d.className = 'cl-label';
        d.dataset.cid = cl.id;
        const t = maxC > minC ? (cl.paper_count - minC) / (maxC - minC) : 0.5;
        const fontSize = Math.round(14 + t * 12); // 14px → 26px
        d.innerHTML = `<div class="cl-dot" style="background:${cl.color};box-shadow:0 0 12px ${cl.color}"></div><div class="cl-name" style="font-size:${fontSize}px">${cl.name}</div><div class="cl-count">${cl.paper_count.toLocaleString()} papers</div>`;
        d.onclick = e => { e.stopPropagation(); state.hasInteracted = true; machine.enterCluster(cl.id); };
        el.appendChild(d);
    });
}

export function updateLabels() {
    const m = machine.get();
    // Labels are the map's interface — "she navigates by recognition".
    // They are always readable; mode only decides emphasis.
    const baseOpacity = 0.85;

    document.querySelectorAll('.cl-label').forEach(el => {
        const cl = state.mapData.clusters.find(c => c.id == el.dataset.cid);
        if (!cl) return;
        const c = clusterWorldPos(cl);
        const v = new THREE.Vector3(c.x, c.y, c.z).project(state.camera);
        el.style.left = (v.x * 0.5 + 0.5) * innerWidth + 'px';
        el.style.top = (-v.y * 0.5 + 0.5) * innerHeight + 'px';

        const isActive = m.clusterId === cl.id;
        let opacity = baseOpacity;
        if (m.mode !== 'universe') opacity = isActive ? 1 : (m.mode === 'paper' || m.mode === 'intel') ? 0.15 : 0.3;
        el.style.display = (v.z < 1 && opacity > 0.02) ? '' : 'none';
        el.style.opacity = opacity;
        el.classList.toggle('active', isActive);
    });
}

// dimExcept — the "only one thing glows" primitive. cid null = restore all.
export function dimExcept(cid) {
    const o = state.ptsGeo.attributes.opacity, s = state.ptsGeo.attributes.size;
    state.allPapers.forEach((p, i) => {
        const baseSize = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        if (cid === null) { o.array[i] = 1.0; s.array[i] = baseSize; }
        else if (p._cl.id === cid) { o.array[i] = 1.0; s.array[i] = baseSize * 1.4; }
        else { o.array[i] = 0.35; s.array[i] = baseSize * 0.85; }
    });
    o.needsUpdate = true; s.needsUpdate = true;
}
