// filters.js — quick-jump territory pills on the landing hero.
// They express intent; the machine does the rest.

import { state } from './state.js';
import { machine } from './machine.js';

export function makeFilters() {
    const c = document.getElementById('filters');
    const top = state.mapData.clusters.filter(x => x.id !== -1).slice(0, 6);
    c.innerHTML = `<div class="filter-dd active" data-cid="">All Fields</div>` +
        top.map(cl => `<div class="filter-dd" data-cid="${cl.id}">${cl.name}</div>`).join('');
    c.querySelectorAll('.filter-dd').forEach(el => {
        el.addEventListener('click', () => {
            state.hasInteracted = true;
            c.querySelectorAll('.filter-dd').forEach(f => f.classList.remove('active'));
            el.classList.add('active');
            if (el.dataset.cid === '') machine.reset();
            else machine.enterCluster(parseInt(el.dataset.cid));
        });
    });
}

export function resetFilters() {
    document.querySelectorAll('.filter-dd').forEach((f, i) => f.classList.toggle('active', i === 0));
}
