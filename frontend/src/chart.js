import { state } from './state.js';

// Chart mode: a claimed territory. The cluster gets a territory ring, the
// reading list docks left as an instrument, and each paper marked read
// lights its star on the map. The full workspace (/app) is one gesture,
// never a push.
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

function lightStar(paperId, cl) {
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

async function toggleRead(el, paper, cl) {
    const read = !el.classList.contains('done');
    el.classList.toggle('done', read);
    fetch(`/api/projects/${chart.projectId}/papers/${paper.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read_status: read ? 'read' : 'unread' }),
    });
    if (read) lightStar(paper.openalex_id, cl);
    document.getElementById('chart-done').textContent = document.querySelectorAll('.chart-rp.done').length;
}

export async function enterChartMode(project, cl) {
    exitChartMode();
    const res = await fetch(`/api/projects/${project.project_id || project.id}/papers`);
    const data = await res.json();
    const papers = data.papers;
    chart = {
        projectId: project.project_id || project.id,
        boardUrl: project.board_url || `/app/projects/${project.project_id || project.id}/board`,
        clusterId: cl.id,
        world: clusterWorld(cl),
        lit: [],
    };
    ensureRing(cl);

    const panel = document.getElementById('chart-panel');
    panel.style.setProperty('--chart-cl', cl.color);
    panel.innerHTML = `
        <div style="padding:22px 22px 14px">
            <div style="font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.16em;color:rgba(255,255,255,0.28);margin-bottom:8px">Your expedition</div>
            <div style="font-family:'Playfair Display',serif;font-size:17px;line-height:1.4;color:#fff;margin-bottom:4px">${cl.name}</div>
            <div style="font-size:11px;color:${cl.color};margin-bottom:16px"><span id="chart-done">${papers.filter(p => p.read_status === 'read').length}</span> of ${papers.length} charted</div>
            <a href="${chart.boardUrl}" style="font-size:11px;color:rgba(255,255,255,0.4);text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.25)">Open full workspace →</a>
        </div>
        <div style="padding:0 22px 22px">
            ${papers.map(p => `
                <div class="chart-rp ${p.read_status === 'read' ? 'done' : ''}" data-pid="${p.id}" data-oid="${p.openalex_id || ''}">
                    <div class="box"></div>
                    <div><div class="t">${p.title}</div><div style="font-size:10px;color:rgba(255,255,255,0.25);margin-top:2px">${p.year || ''} · arxiv ${p.openalex_id || ''}</div></div>
                </div>`).join('')}
        </div>`;
    panel.style.display = 'block';
    requestAnimationFrame(() => panel.classList.add('visible'));

    panel.querySelectorAll('.chart-rp').forEach(el => {
        const paper = papers.find(p => p.id === el.dataset.pid);
        el.onclick = () => toggleRead(el, paper, cl);
        if (paper && paper.read_status === 'read') lightStar(paper.openalex_id, cl);
    });

    state.chartMode = true;
}

export function exitChartMode() {
    if (!chart) return;
    unlightStars();
    const panel = document.getElementById('chart-panel');
    if (panel) {
        panel.classList.remove('visible');
        setTimeout(() => { panel.style.display = 'none'; }, 450);
    }
    const ring = document.getElementById('territory-ring');
    if (ring) ring.style.display = 'none';
    chart = null;
    state.chartMode = false;
}

export function isCharting() {
    return !!chart;
}
