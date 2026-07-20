// intel.js — the Cluster Intelligence Page, rendered as the dock's wide
// content. The map stays alive behind it (dimmed) — intelligence is read
// WITH the territory in view, not instead of it.

import { state } from './state.js';
import { machine } from './machine.js';
import { dock } from './dock.js';

let briefs = null;

async function loadBriefs() {
    if (!briefs) {
        briefs = await (await fetch('data/cluster_briefs.json')).json();
    }
    return briefs;
}

function fmtGrowth(g) {
    if (g === null || g === undefined) return '—';
    const pct = Math.round(g * 100);
    return (pct >= 0 ? '+' : '') + pct + '%';
}

function landscapeHtml(cl, subAreas) {
    if (!subAreas.length) return '';
    const W = 560, H = 330;
    const maxN = Math.max(...subAreas.map(s => s.paper_count));
    const nodes = subAreas.map(s => {
        const r = 24 + 30 * Math.sqrt(s.paper_count / maxN);
        const x = W / 2 + s.cx * (W / 2 - 80);
        const y = H / 2 - s.cy * (H / 2 - 60);
        const hot = s.recent_share >= 0.4;
        return { ...s, r, x, y, hot };
    });
    return `
    <div class="intel-section">The landscape <span class="intel-note">— structural, from embeddings</span></div>
    <div class="intel-landscape" style="width:${W}px;height:${H}px">
        <svg width="${W}" height="${H}" style="position:absolute;inset:0">
            ${nodes.map(n => `<line x1="${W / 2}" y1="${H / 2}" x2="${n.x}" y2="${n.y}" stroke="${cl.color}30" stroke-width="1"/>`).join('')}
        </svg>
        <div style="position:absolute;left:${W / 2 - 5}px;top:${H / 2 - 5}px;width:10px;height:10px;border-radius:50%;background:${cl.color}"></div>
        ${nodes.map(n => `
            <div style="position:absolute;left:${n.x - n.r}px;top:${n.y - n.r}px;width:${n.r * 2}px;height:${n.r * 2}px;border-radius:50%;background:${cl.color}14;border:1px solid ${cl.color}${n.hot ? '90' : '40'};display:flex;align-items:center;justify-content:center;text-align:center;padding:6px">
                <div>
                    <div style="font-size:10px;color:rgba(255,255,255,0.75);line-height:1.3">${n.label}</div>
                    <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:2px">${n.paper_count}${n.hot ? ' · <span style="color:' + cl.color + '">▲ active</span>' : ''}</div>
                </div>
            </div>`).join('')}
    </div>`;
}

function subAreasHtml(cl, subAreas) {
    if (!subAreas.length) return '';
    return `
    <div class="intel-section">Sub-areas</div>
    ${subAreas.map(s => `
        <div class="intel-card">
            <div class="intel-card-head">
                <div class="intel-card-title">${s.label}</div>
                <div class="intel-meta">${s.paper_count} papers · ${Math.round(s.recent_share * 100)}% recent</div>
            </div>
            ${s.top_papers.map(p => `
                <div class="intel-paper"><a href="https://arxiv.org/abs/${p.id}" target="_blank" rel="noopener">${p.title}</a> <span class="intel-meta">${p.year || ''}</span></div>
            `).join('')}
        </div>`).join('')}`;
}

function kingsHtml(cl, kings) {
    if (!kings.length) return '';
    return `
    <div class="intel-section">Foundational papers <span class="intel-note">— by network centrality</span></div>
    ${kings.map((p, i) => `
        <div class="intel-paper king">
            <span style="color:${cl.color};flex-shrink:0">${i + 1}.</span>
            <span><a href="https://arxiv.org/abs/${p.id}" target="_blank" rel="noopener">${p.title}</a>
            <span class="intel-meta"> — ${(p.authors || '').split(',')[0]}${(p.authors || '').includes(',') ? ' et al.' : ''}${p.year ? ', ' + p.year : ''}</span></span>
        </div>`).join('')}`;
}

function trendHtml(cl, brief) {
    const hist = brief.year_histogram || {};
    const years = Object.keys(hist).sort();
    if (years.length < 2) return '';
    const max = Math.max(...years.map(y => hist[y]), 1);
    return `
    <div class="intel-section">Movement</div>
    <div class="intel-trend">
        ${years.map(y => `<div title="${y}: ${hist[y]}" style="height:${Math.max(2, (hist[y] / max) * 42)}px;background:${cl.color}${y >= brief.year_max - 1 ? '' : '55'}"></div>`).join('')}
    </div>
    <div class="intel-trend-years"><span>${years[0]}</span><span>${years[years.length - 1]}</span></div>`;
}

export async function openIntelFx(cl) {
    const data = await loadBriefs();
    const brief = data.clusters[String(cl.id)];
    if (!brief) { machine.back(); return; }
    const claimed = state.claimedProjects && state.claimedProjects[cl.id];

    dock.show('intel', `
    <div class="intel-page">
        <div class="dock-header">
            <div class="dock-kicker">Territory intelligence</div>
            <div class="dock-title intel"><span class="dock-dot" style="background:${cl.color}"></span>${brief.name}</div>
            <div class="dock-desc">
                ${brief.paper_count.toLocaleString()} papers · ${brief.year_min}–${brief.year_max} ·
                <span style="color:${cl.color}">${fmtGrowth(brief.growth_recent)} recent growth</span>
            </div>
            <div class="dock-abstract">${brief.description}</div>
        </div>

        ${landscapeHtml(cl, brief.sub_areas)}
        ${trendHtml(cl, brief)}
        ${subAreasHtml(cl, brief.sub_areas)}
        ${kingsHtml(cl, brief.king_papers)}

        <div class="intel-section">Schools · Debates · Open questions</div>
        <div class="intel-card" style="font-style:italic;color:rgba(255,255,255,0.3);font-size:12px">
            Analyst pass pending — an LLM brief of schools of thought, live debates and open
            questions lands in v0.1. Everything above is computed directly from the corpus.
        </div>

        ${claimed ? '' : `
        <div class="intel-section">Make it yours</div>
        <div class="intel-card" style="border-color:${cl.color}40">
            <div class="intel-claim-title">Create a Research Space</div>
            <div class="intel-claim-sub">
                Seed a workspace with the ${Math.min(300, brief.paper_count)} most central papers of
                <b>${brief.name}</b> — semantic search and the Living Board included.
            </div>
            <input id="intel-question" class="intel-input" placeholder="Your research question — e.g. Can models know when they are wrong?">
            <div class="intel-claim-row">
                <button id="intel-create" class="dock-btn-primary">Create Research Space →</button>
                <span id="intel-status" class="intel-meta"></span>
            </div>
        </div>`}
    </div>`, { wide: true });

    document.getElementById('intel-create')?.addEventListener('click', () => createSpaceFromCluster(cl.id));
}

export async function createSpaceFromCluster(clusterId) {
    const input = document.getElementById('intel-question');
    const btn = document.getElementById('intel-create');
    const status = document.getElementById('intel-status');
    const q = input.value.trim();
    if (!q) {
        input.style.borderColor = 'rgba(255,107,138,0.7)';
        input.focus();
        return;
    }
    btn.disabled = true;
    btn.style.opacity = '0.5';
    status.textContent = 'Seeding papers…';
    try {
        const res = await fetch('/api/projects/from-cluster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cluster_id: clusterId, research_question: q }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        status.textContent = `${data.paper_count} papers seeded — the territory is yours.`;
        state.claimedProjects[clusterId] = { id: data.project_id, board_url: data.board_url };
        setTimeout(() => {
            machine.enterChart({ project_id: data.project_id, board_url: data.board_url });
        }, 700);
    } catch (e) {
        btn.disabled = false;
        btn.style.opacity = '1';
        status.textContent = 'Failed to create space — is the API running?';
    }
}
