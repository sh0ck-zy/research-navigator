// machine.js — the experience state machine. The ONLY owner of "what the
// user is doing right now". Modules express intent by calling transitions;
// they never set mode flags themselves. Visual consequences of a transition
// are applied by effects.js, which subscribes here.
//
//   UNIVERSE ──click cluster──▶ CLUSTER ──click paper──▶ PAPER
//     ▲                          │  ▲                      │
//     │                          ▼  │                      │
//     │                         INTEL (overlay)            │
//     │                          │                         │
//     │                          ▼                         │
//     │                         CHART (claimed territory)  │
//     └────────────── back() pops exactly one level ───────┘
//
// back() semantics: intel→(chart|cluster), chart→cluster, paper→(cluster|
// universe, depending on how the paper was reached), cluster→universe.

import { state } from './state.js';

const ctx = {
    mode: 'universe',   // universe | cluster | paper | intel | chart
    clusterId: null,
    paperIdx: -1,
    paperFrom: null,    // 'cluster' | 'search' | 'library' | 'map'
    underlying: null,   // mode hidden beneath intel ('cluster' | 'chart')
    project: null,      // active chart-mode project
};

const subs = [];

function emit(prev) {
    const next = { ...ctx };
    document.body.dataset.mode = next.mode;
    subs.forEach(fn => fn(next, prev));
}

export const machine = {
    get() { return { ...ctx }; },

    on(fn) { subs.push(fn); },

    enterCluster(cid) {
        if (ctx.mode === 'cluster' && ctx.clusterId === cid) return;
        const prev = { ...ctx };
        ctx.mode = 'cluster';
        ctx.clusterId = cid;
        ctx.paperIdx = -1;
        ctx.paperFrom = null;
        ctx.underlying = null;
        // Return dance: entering a claimed territory re-enters chart mode.
        const claimed = state.claimedProjects && state.claimedProjects[cid];
        if (claimed) {
            ctx.mode = 'chart';
            ctx.project = claimed;
        }
        emit(prev);
    },

    focusPaper(idx, from = 'cluster') {
        const prev = { ...ctx };
        ctx.paperIdx = idx;
        ctx.paperFrom = from;
        if (from === 'search' || from === 'library') {
            ctx.mode = 'paper';
            ctx.clusterId = null;
            ctx.underlying = null;
        } else {
            ctx.mode = 'paper';
        }
        emit(prev);
    },

    openIntel() {
        if (ctx.mode !== 'cluster' && ctx.mode !== 'chart') return;
        const prev = { ...ctx };
        ctx.underlying = ctx.mode;
        ctx.mode = 'intel';
        emit(prev);
    },

    enterChart(project) {
        const prev = { ...ctx };
        ctx.mode = 'chart';
        ctx.project = project;
        ctx.underlying = null;
        emit(prev);
    },

    back() {
        const prev = { ...ctx };
        switch (ctx.mode) {
            case 'intel':
                ctx.mode = ctx.underlying || 'cluster';
                ctx.underlying = null;
                break;
            case 'chart':
                ctx.mode = 'cluster';
                ctx.project = null;
                break;
            case 'paper':
                if (ctx.paperFrom === 'cluster' && ctx.clusterId !== null) {
                    ctx.mode = state.claimedProjects[ctx.clusterId] ? 'chart' : 'cluster';
                    if (ctx.mode === 'chart') ctx.project = state.claimedProjects[ctx.clusterId];
                } else {
                    ctx.mode = 'universe';
                    ctx.clusterId = null;
                }
                ctx.paperIdx = -1;
                ctx.paperFrom = null;
                break;
            case 'cluster':
                ctx.mode = 'universe';
                ctx.clusterId = null;
                break;
            default:
                return; // universe: nowhere to go back to
        }
        emit(prev);
    },

    reset() {
        const prev = { ...ctx };
        ctx.mode = 'universe';
        ctx.clusterId = null;
        ctx.paperIdx = -1;
        ctx.paperFrom = null;
        ctx.underlying = null;
        ctx.project = null;
        emit(prev);
    },
};
