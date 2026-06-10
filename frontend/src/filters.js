import { state, SPREAD } from './state.js';
import { fly, hideBubbles } from './scene.js';
import { dimExcept } from './labels.js';
import { updateNavContext } from './nav.js';
import { updateStats } from './stats.js';

export function makeFilters() {
    const c=document.getElementById('filters');
    const top = state.mapData.clusters.filter(x=>x.id!==-1).slice(0,6);
    c.innerHTML = `<div class="filter-dd active" onclick="applyFilter(null,this)" style="background:rgba(255,255,255,0.9);color:#111;border-color:transparent">All Fields</div>` +
        top.map(cl => `<div class="filter-dd" onclick="applyFilter(${cl.id},this)">${cl.name}</div>`).join('');
}

export function applyFilter(cid, el) {
    state.hasInteracted = true;
    state.clusterZoomDist = 0; // Prevent auto-exit from zoom-out check
    document.querySelectorAll('.filter-dd').forEach(f => {
        f.classList.remove('active');
        f.style.background = 'rgba(255,255,255,0.03)';
        f.style.color = 'rgba(255,255,255,0.5)';
        f.style.borderColor = '';
    });
    el.classList.add('active');
    el.style.background = 'rgba(255,255,255,0.9)';
    el.style.color = '#111';
    el.style.borderColor = 'transparent';

    state.activeCluster = cid;
    dimExcept(cid);
    hideBubbles();

    if (cid !== null) {
        const cl = state.mapData.clusters.find(c => c.id === cid);
        if (cl) {
            const cx = (cl.center_x - 0.5) * SPREAD;
            const cy = (cl.center_y - 0.5) * SPREAD;
            fly(cx, cy + 40, 200);
            state.controls.autoRotate = false;
        }
    } else {
        fly(0, 80, 500);
        state.controls.autoRotate = true;
    }
    updateNavContext(); updateStats();
}
