import { state } from './state.js';
import { fly } from './scene.js';
import { deselectPaper } from './papers.js';
import { exitCluster, removeClusterConnections, hideClusterInsight } from './clusters.js';
import { updateStats } from './stats.js';

export function navBack() {
    if (state.selectedIdx >= 0) {
        deselectPaper();
        updateNavContext(); updateStats();
    } else if (state.activeCluster !== null) {
        resetView();
    }
}

export function updateNavContext() {
    const ctx = document.getElementById('nav-context');
    const bc = document.getElementById('breadcrumb');
    if (state.activeCluster === null && state.selectedIdx < 0) {
        ctx.style.display = 'none';
        return;
    }
    ctx.style.display = 'flex';
    const parts = ['<span style="cursor:pointer;color:rgba(255,255,255,0.4)" onclick="resetView()">All Fields</span>'];
    if (state.activeCluster !== null) {
        const cl = state.mapData.clusters.find(c => c.id === state.activeCluster);
        if (cl) {
            const clColor = cl.color;
            parts.push(`<span style="color:rgba(255,255,255,0.2)">→</span>`);
            parts.push(`<span style="color:${clColor};cursor:pointer" onclick="deselectPaper();updateNavContext()">${cl.name}</span>`);
        }
    }
    if (state.selectedIdx >= 0 && state.cardPaper) {
        const title = state.cardPaper.title.length > 40 ? state.cardPaper.title.substring(0, 37) + '...' : state.cardPaper.title;
        parts.push(`<span style="color:rgba(255,255,255,0.2)">→</span>`);
        parts.push(`<span style="color:rgba(255,255,255,0.5)">${title}</span>`);
    }
    bc.innerHTML = parts.join(' ');
}

export function resetView() {
    deselectPaper();
    exitCluster();
    removeClusterConnections();
    hideClusterInsight();
    state.hasInteracted = false;
    state.controls.autoRotate = true;
    fly(0, 80, 500);
    updateNavContext(); updateStats();
    document.querySelectorAll('.filter-dd').forEach((f,i) => {
        if(i===0) { f.style.background='rgba(255,255,255,0.9)'; f.style.color='#111'; f.style.borderColor='transparent'; f.classList.add('active'); }
        else { f.style.background='rgba(255,255,255,0.03)'; f.style.color='rgba(255,255,255,0.5)'; f.style.borderColor=''; f.classList.remove('active'); }
    });
}
