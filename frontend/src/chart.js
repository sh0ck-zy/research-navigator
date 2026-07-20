// chart.js — chart mode: a claimed territory. The territory ring is glued to
// the cluster in 3D; the reading list lives in the dock; each paper marked
// read lights its star. The full workspace (/app) is one gesture, never a push.

import { state } from './state.js';
import { machine } from './machine.js';
import { dock } from './dock.js';

let chart = null;

function clusterWorld(cl) {
    const pts = state.allPapers.filter(p => p._cl.id === cl.id);
    const cx = pts.reduce((s, p) => s + p._x, 0) / pts.length;
    const cy = pts.reduce((s, p) => s + p._y, 0) / pts.length;
    const cz = pts.reduce((s, p) => s + p._z, 0) / pts.length;
    const r = Math.max(...pts.map(p => Math.hypot(p._x - cx, p._y - cy)), 10);
    return { cx, cy, cz, r };
}

function ensureRing(cl) {
    let el = document.getElementById('territory-ring');
    if (!el) {
        el = document.createElement('div');
        el.id = 'territory-ring';
        el.className = 'territory-ring';
        document.body.appendChild(el);
    }
    el.style.borderColor = cl.color + '90';
    el.style.boxShadow = `0 0 60px ${cl.color}30, inset 0 0 60px ${cl.color}18`;
    el.style.display = 'block';
}

// Called every frame from loop.js — keeps the ring glued to the cluster.
export function updateChartRing(THREE) {
    const el = document.getElementById('territory-ring');
    if (!el || !chart) { if (el) el.style.display = 'none'; return; }
    const { cx, cy, cz, r } = chart.world;
    const c = new THREE.Vector3(cx, cy, cz).project(state.camera);
    const e = new THREE.Vector3(cx + r, cy, cz).project(state.camera);
    const px = (c.x * 0.5 + 0.5) * innerWidth, py = (-c.y * 0.5 + 0.5) * innerHeight;
    const pr = Math.abs((e.x * 0.5 + 0.5) * innerWidth - px);
    el.style.left = px + 'px';
    el.style.top = py + 'px';
    el.style.width = el.style.height = pr * 2.3 + 'px';
    el.style.display = c.z < 1 ? 'block' : 'none';
}

function lightStar(paperId) {
    const i = state.allPapers.findIndex(p => p.id === paperId);
    if (i < 0) return;
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    chart.lit.push({ index: i, origSize: sizeArr[i], origOpacity: opaArr[i] });
    sizeArr[i] = (state.baseSizes ? state.baseSizes[i] : 3) * 2.6;
    opaArr[i] = 1.0;
    state.ptsGeo.attributes.size.needsUpdate = true;
    state.ptsGeo.attributes.opacity.needsUpdate = true;
}

function unlightStars() {
    if (!chart) return;
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    chart.lit.forEach(l => { sizeArr[l.index] = l.origSize; opaArr[l.index] = l.origOpacity; });
    if (chart.lit.length) {
        state.ptsGeo.attributes.size.needsUpdate = true;
        state.ptsGeo.attributes.opacity.needsUpdate = true;
    }
}

async function toggleRead(el, paper) {
    const read = !el.classList.contains('done');
    el.classList.toggle('done', read);
    fetch(`/api/projects/${chart.projectId}/papers/${paper.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read_status: read ? 'read' : 'unread' }),
    }).catch(() => {});
    if (read) lightStar(paper.openalex_id);
    const done = document.getElementById('chart-done');
    if (done) done.textContent = document.querySelectorAll('.chart-rp.done').length;
}

export async function enterChartFx(project, cl) {
    exitChartFx();
    let papers = [];
    try {
        const res = await fetch(`/api/projects/${project.project_id || project.id}/papers`);
        if (res.ok) papers = (await res.json()).papers;
    } catch (e) { /* offline — show the territory without the list */ }

    chart = {
        projectId: project.project_id || project.id,
        boardUrl: project.board_url || `/app/projects/${project.project_id || project.id}/board`,
        clusterId: cl.id,
        world: clusterWorld(cl),
        lit: [],
    };
    ensureRing(cl);

    dock.show('chart', `
        <div class="dock-header">
            <div class="dock-kicker">Your expedition</div>
            <div class="dock-title"><span class="dock-dot" style="background:${cl.color}"></span>${cl.name}</div>
            <div class="dock-desc" style="color:${cl.color}"><span id="chart-done">${papers.filter(p => p.read_status === 'read').length}</span> of ${papers.length} charted</div>
        </div>
        <div class="dock-actions">
            <a class="dock-btn" href="${chart.boardUrl}">Open full workspace →</a>
            <button class="dock-btn" id="dock-chart-intel">Territory intelligence</button>
        </div>
        <div class="dock-section">
            <div class="dock-section-title">Reading list</div>
            ${papers.map(p => `
                <div class="chart-rp ${p.read_status === 'read' ? 'done' : ''}" data-pid="${p.id}">
                    <div class="box"></div>
                    <div><div class="t">${p.title}</div><div class="m">${p.year || ''} · arxiv ${p.openalex_id || ''}</div></div>
                </div>`).join('')}
        </div>
    `);
    document.getElementById('dock-chart-intel')?.addEventListener('click', () => machine.openIntel());
    document.querySelectorAll('.chart-rp').forEach(el => {
        const paper = papers.find(p => String(p.id) === el.dataset.pid);
        if (!paper) return;
        el.onclick = () => toggleRead(el, paper);
        if (paper.read_status === 'read') lightStar(paper.openalex_id);
    });
}

export function exitChartFx() {
    if (!chart) return;
    unlightStars();
    const ring = document.getElementById('territory-ring');
    if (ring) ring.style.display = 'none';
    chart = null;
}

export function isCharting() { return !!chart; }
