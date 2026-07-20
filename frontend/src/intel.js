import { state } from './state.js';
import { enterChartMode } from './chart.js';

let briefs = null;

async function loadBriefs() {
    if (!briefs) {
        briefs = await (await fetch('data/cluster_briefs.json')).json();
    }
    return briefs;
}

const S = {
    section: 'font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.14em;color:rgba(255,255,255,0.28);margin:28px 0 10px',
    card: 'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 16px',
    paperRow: 'font-size:12px;color:rgba(255,255,255,0.6);padding:4px 0;line-height:1.5',
    paperLink: 'color:inherit;text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.25)',
    meta: 'font-size:10px;color:rgba(255,255,255,0.3)',
};

function fmtGrowth(g) {
    if (g === null || g === undefined) return '—';
    const pct = Math.round(g * 100);
    return (pct >= 0 ? '+' : '') + pct + '%';
}

function landscapeHtml(cl, subAreas) {
    if (!subAreas.length) return '';
    const W = 640, H = 380;
    const maxN = Math.max(...subAreas.map(s => s.paper_count));
    const nodes = subAreas.map(s => {
        const r = 26 + 34 * Math.sqrt(s.paper_count / maxN);
        const x = W / 2 + s.cx * (W / 2 - 90);
        const y = H / 2 - s.cy * (H / 2 - 70);
        const hot = s.recent_share >= 0.4;
        return { ...s, r, x, y, hot };
    });
    return `
    <div style="${S.section}">The landscape <span style="text-transform:none;letter-spacing:0;font-weight:400;color:rgba(255,255,255,0.18)">— structural, from embeddings</span></div>
    <div style="position:relative;width:${W}px;height:${H}px;margin:0 auto">
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
    <div style="${S.section}">Sub-areas</div>
    ${subAreas.map(s => `
        <div style="${S.card};margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:baseline">
                <div style="font-size:13px;color:rgba(255,255,255,0.85)">${s.label}</div>
                <div style="${S.meta}">${s.paper_count} papers · ${Math.round(s.recent_share * 100)}% recent</div>
            </div>
            ${s.top_papers.map(p => `
                <div style="${S.paperRow}"><a style="${S.paperLink}" href="https://arxiv.org/abs/${p.id}" target="_blank" rel="noopener">${p.title}</a> <span style="${S.meta}">${p.year || ''}</span></div>
            `).join('')}
        </div>`).join('')}`;
}

function kingsHtml(cl, kings) {
    if (!kings.length) return '';
    return `
    <div style="${S.section}">Foundational papers <span style="text-transform:none;letter-spacing:0;font-weight:400;color:rgba(255,255,255,0.18)">— by network centrality</span></div>
    ${kings.map((p, i) => `
        <div style="${S.paperRow};display:flex;gap:10px">
            <span style="color:${cl.color};flex-shrink:0">${i + 1}.</span>
            <span><a style="${S.paperLink}" href="https://arxiv.org/abs/${p.id}" target="_blank" rel="noopener">${p.title}</a>
            <span style="${S.meta}"> — ${(p.authors || '').split(' and ')[0]}${(p.authors || '').includes(' and ') ? ' et al.' : ''}${p.year ? ', ' + p.year : ''}</span></span>
        </div>`).join('')}`;
}

function trendHtml(cl, brief) {
    const hist = brief.year_histogram || {};
    const years = Object.keys(hist).sort();
    if (years.length < 2) return '';
    const max = Math.max(...years.map(y => hist[y]), 1);
    return `
    <div style="${S.section}">Movement</div>
    <div style="display:flex;align-items:flex-end;gap:3px;height:44px;padding:0 2px">
        ${years.map(y => `<div title="${y}: ${hist[y]}" style="flex:1;border-radius:2px 2px 0 0;height:${Math.max(2, (hist[y] / max) * 42)}px;background:${cl.color}${y >= brief.year_max - 1 ? '' : '55'}"></div>`).join('')}
    </div>
    <div style="display:flex;justify-content:space-between;${S.meta};margin-top:4px"><span>${years[0]}</span><span>${years[years.length - 1]}</span></div>`;
}

export async function openClusterIntel(cl) {
    const data = await loadBriefs();
    const brief = data.clusters[String(cl.id)];
    if (!brief) return;
    const el = document.getElementById('cluster-intel');

    el.innerHTML = `
    <div style="padding:56px 40px 120px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <div style="display:flex;align-items:center;gap:10px">
                    <div style="width:12px;height:12px;border-radius:50%;background:${cl.color}"></div>
                    <div style="font-family:'Playfair Display',serif;font-size:32px;font-weight:500;color:#fff">${brief.name}</div>
                </div>
                <div style="font-size:12px;color:rgba(255,255,255,0.35);margin-top:8px">
                    ${brief.paper_count.toLocaleString()} papers · ${brief.year_min}–${brief.year_max} ·
                    <span style="color:${cl.color}">${fmtGrowth(brief.growth_recent)} recent growth</span>
                </div>
            </div>
            <button onclick="closeClusterIntel()" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:14px;flex-shrink:0">✕</button>
        </div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.7;margin-top:16px;max-width:640px">${brief.description}</div>

        ${landscapeHtml(cl, brief.sub_areas)}
        ${trendHtml(cl, brief)}
        ${subAreasHtml(cl, brief.sub_areas)}
        ${kingsHtml(cl, brief.king_papers)}

        <div style="${S.section}">Schools · Debates · Open questions</div>
        <div style="${S.card};font-size:12px;color:rgba(255,255,255,0.3);font-style:italic">
            Analyst pass pending — an LLM brief of schools of thought, live debates and open
            questions lands in v0.1. Everything above is computed directly from the corpus.
        </div>

        <div style="${S.section}">Make it yours</div>
        <div style="${S.card};border-color:${cl.color}40">
            <div style="font-size:14px;color:rgba(255,255,255,0.85);margin-bottom:4px">Create a Research Space</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.4);line-height:1.6;margin-bottom:12px">
                Seed a workspace with the ${Math.min(300, brief.paper_count)} most central papers of
                <b style="color:rgba(255,255,255,0.7)">${brief.name}</b> — semantic search and the Living Board included.
            </div>
            <input id="intel-question" placeholder="Your research question — e.g. Can models know when they are wrong?"
                style="width:100%;box-sizing:border-box;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 12px;font-size:13px;color:#fff;font-family:'Inter',sans-serif;outline:none;margin-bottom:10px">
            <div style="display:flex;align-items:center;gap:12px">
                <button id="intel-create" onclick="createSpaceFromCluster(${cl.id})"
                    style="background:rgba(255,255,255,0.92);border:none;color:#111;padding:9px 18px;border-radius:20px;font-size:13px;font-weight:600;font-family:'Inter',sans-serif;cursor:pointer">
                    Create Research Space →
                </button>
                <span id="intel-status" style="font-size:11px;color:rgba(255,255,255,0.35)"></span>
            </div>
        </div>
    </div>`;
    el.style.display = 'block';
    requestAnimationFrame(() => el.classList.add('visible'));
    state.intelOpen = true;
}

export function openActiveClusterIntel() {
    const cl = state.mapData.clusters.find(c => c.id === state.activeCluster);
    if (cl) openClusterIntel(cl);
}

export function closeClusterIntel() {
    const el = document.getElementById('cluster-intel');
    el.classList.remove('visible');
    setTimeout(() => { el.style.display = 'none'; }, 350);
    state.intelOpen = false;
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
        // Claim happens in the sky: no redirect. The ring, the instrument,
        // the stars that light as you read. /app stays one gesture away.
        const cl = state.mapData.clusters.find(c => c.id === clusterId);
        state.claimedProjects = state.claimedProjects || {};
        state.claimedProjects[clusterId] = { id: data.project_id, board_url: data.board_url };
        setTimeout(() => {
            closeClusterIntel();
            enterChartMode({ project_id: data.project_id, board_url: data.board_url }, cl);
        }, 700);
    } catch (e) {
        btn.disabled = false;
        btn.style.opacity = '1';
        status.textContent = 'Failed to create space — is the API running?';
    }
}
