// lens.js — maps an importance metric to each star's base size.
// Core rule: it HIGHLIGHTS, never hides. Every paper keeps a visible,
// clickable minimum size.

import { state } from './state.js';
import { machine } from './machine.js';
import { dimExcept } from './labels.js';
import { showKingPapers, hideKingPapers, getCluster } from './clusters.js';

const MIN_SIZE = 1.5;

export function computeBaseSizes(metric) {
    const n = state.allPapers.length;
    if (!state.baseSizes || state.baseSizes.length !== n) state.baseSizes = new Float32Array(n);
    const b = state.baseSizes;

    if (metric === 'citations') {
        const vals = state.allPapers.map(p => Math.log1p(p.cited_by_count || 0));
        const mn = Math.min(...vals), mx = Math.max(...vals);
        const range = (mx - mn) || 1;
        state.allPapers.forEach((p, i) => {
            b[i] = MIN_SIZE + ((Math.log1p(p.cited_by_count || 0) - mn) / range) * 8.0;
        });
    } else if (metric === 'recency') {
        const years = state.allPapers.map(p => p.year).filter(Boolean);
        const mn = Math.min(...years), mx = Math.max(...years);
        const range = (mx - mn) || 1;
        state.allPapers.forEach((p, i) => {
            b[i] = MIN_SIZE + (p.year ? (p.year - mn) / range : 0.3) * 7.0;
        });
    } else if (metric === 'central') {
        state.allPapers.forEach((p, i) => { b[i] = MIN_SIZE + (p._centrality || 0) * 8.0; });
    } else {
        state.allPapers.forEach((p, i) => { b[i] = MIN_SIZE + (p._centrality || 0) * 5.0; });
    }
    state.lens = metric;
    return b;
}

export function applyLens(metric) {
    computeBaseSizes(metric);
    const m = machine.get();

    const hadKings = state.kingPapers.length > 0;
    if (hadKings) hideKingPapers();
    dimExcept(m.clusterId !== null && m.mode !== 'universe' ? m.clusterId : null);
    if (hadKings && m.clusterId !== null) {
        const cl = getCluster(m.clusterId);
        if (cl) showKingPapers(cl);
    }
    if (m.paperIdx >= 0) {
        const s = state.ptsGeo.attributes.size.array;
        s[m.paperIdx] = state.baseSizes[m.paperIdx] * 4.5;
        state.ptsGeo.attributes.size.needsUpdate = true;
    }

    document.querySelectorAll('.lens-btn').forEach(el => {
        el.classList.toggle('active', el.dataset.lens === metric);
    });
}
