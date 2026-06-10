import { state } from './state.js';
import { dimExcept } from './labels.js';
import { showKingPapers, hideKingPapers } from './clusters.js';

// The lens maps an importance metric to each star's base size.
// Core rule: it HIGHLIGHTS, it never hides. Every paper keeps a visible,
// clickable minimum size — under-cited / new / peripheral work stays explorable.
const MIN_SIZE = 1.5;

export function computeBaseSizes(metric) {
    const n = state.allPapers.length;
    if (!state.baseSizes || state.baseSizes.length !== n) state.baseSizes = new Float32Array(n);
    const b = state.baseSizes;

    if (metric === 'citations') {
        // Log scale — citations are heavy-tailed; otherwise a few giants flatten the rest.
        const vals = state.allPapers.map(p => Math.log1p(p.cited_by_count || 0));
        const mn = Math.min(...vals), mx = Math.max(...vals);
        const range = (mx - mn) || 1;
        state.allPapers.forEach((p, i) => {
            const nrm = (Math.log1p(p.cited_by_count || 0) - mn) / range;
            b[i] = MIN_SIZE + nrm * 8.0;
        });
    } else if (metric === 'recency') {
        const years = state.allPapers.map(p => p.year).filter(Boolean);
        const mn = Math.min(...years), mx = Math.max(...years);
        const range = (mx - mn) || 1;
        state.allPapers.forEach((p, i) => {
            const nrm = p.year ? (p.year - mn) / range : 0.3;
            b[i] = MIN_SIZE + nrm * 7.0;
        });
    } else if (metric === 'central') {
        state.allPapers.forEach((p, i) => { b[i] = MIN_SIZE + (p._centrality || 0) * 8.0; });
    } else {
        // 'off' — neutral: the natural structure (cluster cores read slightly larger),
        // nothing emphasized by any single metric.
        state.allPapers.forEach((p, i) => { b[i] = MIN_SIZE + (p._centrality || 0) * 5.0; });
    }
    state.lens = metric;
    return b;
}

export function applyLens(metric) {
    computeBaseSizes(metric);

    // Repaint sizes from the new base, preserving the current interaction state.
    const hadKings = state.kingPapers.length > 0;
    if (hadKings) hideKingPapers();
    dimExcept(state.activeCluster); // recomputes every point's size from baseSizes
    if (state.activeCluster !== null) {
        const cl = state.mapData.clusters.find(c => c.id === state.activeCluster);
        if (cl) showKingPapers(cl);
    }
    if (state.selectedIdx >= 0) {
        const s = state.ptsGeo.attributes.size.array;
        s[state.selectedIdx] = state.baseSizes[state.selectedIdx] * 4.5;
        state.ptsGeo.attributes.size.needsUpdate = true;
    }

    document.querySelectorAll('.lens-btn').forEach(el => {
        el.classList.toggle('active', el.dataset.lens === metric);
    });
}
