// effects.js — the ONLY place where experience modes become visuals.
// Subscribes to the machine; every transition's consequences (camera shot,
// dimming, dock content, labels, rings) are decided here. If the app feels
// wrong, this is the file to read.

import { state } from './state.js';
import { machine } from './machine.js';
import * as cam from './camera.js';
import { dock } from './dock.js';
import { lodTargets } from './scene.js';
import { dimExcept } from './labels.js';
import {
    getCluster, clusterCardHtml, wireClusterCard,
    drawClusterConnections, removeClusterConnections,
    buildBridgeLabels, clearBridgeLabels,
    showKingPapers, hideKingPapers,
} from './clusters.js';
import { selectPaperFx, deselectPaperFx, paperCardHtml, wirePaperCard } from './papers.js';
import { enterChartFx, exitChartFx } from './chart.js';
import { openIntelFx } from './intel.js';
import { renderNavContext } from './nav.js';
import { resetFilters } from './filters.js';

const LOD = {
    universe: { starAlpha: 0.7,  starSize: 0.85, nebula: 0.55, edges: 0.0 },
    cluster:  { starAlpha: 1.0,  starSize: 1.0,  nebula: 0.16, edges: 0.0 },
    paper:    { starAlpha: 1.0,  starSize: 1.0,  nebula: 0.10, edges: 0.06 },
    intel:    { starAlpha: 0.4,  starSize: 0.9,  nebula: 0.25, edges: 0.0 },
    chart:    { starAlpha: 1.0,  starSize: 1.0,  nebula: 0.18, edges: 0.0 },
};

function setLod(mode) {
    Object.assign(lodTargets, LOD[mode] || LOD.universe);
}

export function initEffects() {
    machine.on((next, prev) => {
        apply(next, prev);
        renderNavContext();
    });
}

// Re-render the dock for the current mode (used after closing an overlay
// like the library).
export function refreshDock() {
    const m = machine.get();
    switch (m.mode) {
        case 'cluster': {
            const cl = getCluster(m.clusterId);
            dock.show('cluster', clusterCardHtml(cl));
            wireClusterCard(cl);
            break;
        }
        case 'paper': {
            const p = state.allPapers[m.paperIdx];
            dock.show('paper', paperCardHtml(p, m.paperIdx));
            wirePaperCard(p, m.paperIdx);
            break;
        }
        case 'intel': openIntelFx(getCluster(m.clusterId)); break;
        case 'chart': enterChartFx(m.project, getCluster(m.clusterId)); break;
        default: dock.hide();
    }
}

function apply(next, prev) {
    setLod(next.mode);

    // --- leaving paper focus: restore the star, retract the push ---
    if (prev.mode === 'paper' && next.mode !== 'paper') deselectPaperFx(prev.paperIdx);

    // --- cluster visuals: enter / switch / exit ---
    const prevCid = prev.clusterId;
    const nextCid = next.clusterId;

    if (next.mode === 'universe') {
        dimExcept(null);
        removeClusterConnections();
        clearBridgeLabels();
        hideKingPapers();
        exitChartFx();
        dock.hide();
        if (prev.mode !== 'universe') {
            cam.establish();
            // Home resets the landing: hero and search return, drift resumes.
            state.hasInteracted = false;
            cam.startAutorotate();
        }
        resetFilters();
        return;
    }

    // Every non-universe mode stops the drift.
    cam.stopAutorotate();

    // Territory visuals on entering or switching a cluster.
    const enteredTerritory = nextCid !== null && (nextCid !== prevCid || prev.mode === 'universe');
    if (enteredTerritory) {
        const cl = getCluster(nextCid);
        if (!cl) return;
        dimExcept(nextCid);
        drawClusterConnections(nextCid);
        buildBridgeLabels(nextCid);
        showKingPapers(cl);
    }

    // --- per-mode content + camera (dock opens first so flights can
    // compensate for the space it occupies) ---
    switch (next.mode) {
        case 'cluster': {
            if (prev.mode === 'chart') exitChartFx();
            const cl = getCluster(nextCid);
            dock.show('cluster', clusterCardHtml(cl));
            wireClusterCard(cl);
            if (enteredTerritory || prev.mode === 'paper' || prev.mode === 'intel') {
                cam.approachCluster(cl);
            }
            break;
        }
        case 'paper': {
            const p = state.allPapers[next.paperIdx];
            // Reached from outside a territory: reveal where the paper lives
            // by highlighting its cluster as the paper's home.
            if (next.clusterId === null) dimExcept(p._cl.id);
            dock.show('paper', paperCardHtml(p, next.paperIdx));
            wirePaperCard(p, next.paperIdx);
            selectPaperFx(p, next.paperIdx, prev.paperIdx);
            // From search/library: the three-stage journey. From the map: a
            // short neighborhood flight. Switching papers: no flight at all.
            if (next.paperFrom === 'search' || next.paperFrom === 'library') {
                cam.jumpToPaper(p);
            } else if (prev.mode !== 'paper') {
                cam.focusPaper(p);
            }
            break;
        }
        case 'intel': {
            const cl = getCluster(nextCid);
            openIntelFx(cl); // async; renders wide dock content
            if (enteredTerritory) cam.approachCluster(cl);
            break;
        }
        case 'chart': {
            const cl = getCluster(nextCid);
            enterChartFx(next.project, cl); // ring + reading-list dock
            if (enteredTerritory) cam.approachCluster(cl);
            break;
        }
    }
}
