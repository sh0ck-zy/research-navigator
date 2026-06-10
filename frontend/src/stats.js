import { state } from './state.js';

export function makeStats() {
    const el=document.getElementById('right-stats');
    const validClusters = state.mapData.clusters.filter(c => c.id !== -1);
    const largest = validClusters.reduce((a, b) => a.paper_count > b.paper_count ? a : b);
    const smallest = validClusters.reduce((a, b) => a.paper_count < b.paper_count ? a : b);

    // Find years range
    const allYears = state.allPapers.map(p => p.year).filter(Boolean);
    const minYear = Math.min(...allYears);
    const maxYear = Math.max(...allYears);

    // Find "hottest" cluster (most papers in the most recent year)
    const recentYear = maxYear;
    const hotCounts = {};
    validClusters.forEach(cl => {
        hotCounts[cl.id] = cl.papers.filter(p => p.year === recentYear).length;
    });
    const hottestId = Object.entries(hotCounts).sort((a,b) => b[1] - a[1])[0][0];
    const hottest = validClusters.find(c => c.id === parseInt(hottestId));

    el.innerHTML = `
        <div class="rs-item">
            <div class="rs-label">Papers mapped</div>
            <div class="rs-value">${state.mapData.metadata.paper_count.toLocaleString()}</div>
        </div>
        <div class="rs-item">
            <div class="rs-label">Research areas</div>
            <div class="rs-value">${validClusters.length}</div>
        </div>
        <div class="rs-item">
            <div class="rs-label">Largest area</div>
            <div class="rs-value-sm">${largest.name}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.25)">${largest.paper_count.toLocaleString()} papers</div>
        </div>
        <div class="rs-item">
            <div class="rs-label">Trending in ${recentYear}</div>
            <div class="rs-value-sm">${hottest.name}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.25)">${hotCounts[hottestId]} new papers</div>
        </div>
        <div class="rs-item">
            <div class="rs-label">Time span</div>
            <div class="rs-value">${minYear}–${maxYear}</div>
        </div>
    `;
}

export function updateStats() {
    const el = document.getElementById('right-stats');
    if (state.selectedIdx >= 0 && state.cardPaper) {
        // Paper-level stats
        const p = state.cardPaper;
        const clPapers = state.allPapers.filter(q => q._cl.id === p._cl.id);
        const rank = clPapers.filter(q => (q._centrality||0) <= (p._centrality||0)).length;
        const percentile = Math.round((rank / clPapers.length) * 100);
        el.innerHTML = `
            <div class="rs-item">
                <div class="rs-label">Cluster</div>
                <div class="rs-value-sm" style="color:${p._cl.color}">${p._cl.name}</div>
            </div>
            <div class="rs-item">
                <div class="rs-label">Year</div>
                <div class="rs-value">${p.year || '—'}</div>
            </div>
            <div class="rs-item">
                <div class="rs-label">Centrality</div>
                <div class="rs-value">Top ${100-percentile}%</div>
            </div>
            <div class="rs-item">
                <div class="rs-label">Cluster size</div>
                <div class="rs-value">${p._cl.paper_count.toLocaleString()}</div>
            </div>
        `;
    } else if (state.activeCluster !== null) {
        // Cluster-level stats
        const cl = state.mapData.clusters.find(c => c.id === state.activeCluster);
        if (!cl) return;
        const total = state.mapData.metadata.paper_count;
        const share = (cl.paper_count / total * 100).toFixed(1);
        const years = cl.papers.map(p => p.year).filter(Boolean);
        const minY = Math.min(...years), maxY = Math.max(...years);
        const clPapers = state.allPapers.filter(p => p._cl.id === cl.id);
        const kings = clPapers.slice().sort((a,b) => (b._centrality||0) - (a._centrality||0)).slice(0, 3);
        el.innerHTML = `
            <div class="rs-item">
                <div class="rs-label">Papers in cluster</div>
                <div class="rs-value">${cl.paper_count.toLocaleString()}</div>
            </div>
            <div class="rs-item">
                <div class="rs-label">Share of total</div>
                <div class="rs-value">${share}%</div>
            </div>
            <div class="rs-item">
                <div class="rs-label">Time span</div>
                <div class="rs-value">${minY}–${maxY}</div>
            </div>
            ${kings.map(k => `
            <div class="rs-item">
                <div class="rs-label">Key paper</div>
                <div class="rs-value-sm">${k.title.length > 35 ? k.title.substring(0, 32) + '...' : k.title}</div>
            </div>
            `).join('')}
        `;
    } else {
        // Global stats (default)
        makeStats();
    }
}
