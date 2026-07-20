// nav.js — breadcrumb + back button, rendered from machine state.
// Back always pops exactly one level. Esc does the same (wired in main.js).

import { state } from './state.js';
import { machine } from './machine.js';

export function navBack() {
    machine.back();
}

export function renderNavContext() {
    const m = machine.get();
    const ctx = document.getElementById('nav-context');
    const bc = document.getElementById('breadcrumb');

    if (m.mode === 'universe') {
        ctx.style.display = 'none';
        return;
    }
    ctx.style.display = 'flex';

    const parts = [`<span class="bc-link" data-act="reset">All Fields</span>`];
    let cl = m.clusterId !== null ? state.mapData.clusters.find(c => c.id === m.clusterId) : null;
    // Paper reached via search: its cluster is implied by the paper itself.
    if (!cl && m.mode === 'paper' && m.paperIdx >= 0) cl = state.allPapers[m.paperIdx]._cl;

    if (cl) {
        parts.push(`<span class="bc-sep">→</span>`);
        if (m.mode === 'paper' || m.mode === 'intel' || m.mode === 'chart') {
            parts.push(`<span class="bc-link" data-act="cluster" data-cid="${cl.id}" style="color:${cl.color}">${cl.name}</span>`);
        } else {
            parts.push(`<span style="color:${cl.color}">${cl.name}</span>`);
        }
    }
    if (m.mode === 'paper' && m.paperIdx >= 0) {
        const p = state.allPapers[m.paperIdx];
        const title = p.title.length > 42 ? p.title.slice(0, 39) + '…' : p.title;
        parts.push(`<span class="bc-sep">→</span>`);
        parts.push(`<span class="bc-leaf">${title}</span>`);
    }
    if (m.mode === 'intel') {
        parts.push(`<span class="bc-sep">→</span>`);
        parts.push(`<span class="bc-leaf">Intelligence</span>`);
    }
    if (m.mode === 'chart') {
        parts.push(`<span class="bc-sep">→</span>`);
        parts.push(`<span class="bc-leaf">Your expedition</span>`);
    }

    bc.innerHTML = parts.join(' ');
    bc.querySelectorAll('.bc-link').forEach(el => {
        el.addEventListener('click', () => {
            if (el.dataset.act === 'reset') machine.reset();
            else if (el.dataset.act === 'cluster') machine.enterCluster(parseInt(el.dataset.cid));
        });
    });
}
