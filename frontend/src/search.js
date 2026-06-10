import { state } from './state.js';
import { dimExcept } from './labels.js';
import { openPaperCard, drawLines, flyToNeighborhood } from './papers.js';

export function onSearchFocus() {}

// Paper ID → allPapers index lookup (built once after data loads)
const paperIdIndex = {};
export function buildPaperIndex() {
    state.allPapers.forEach((p, i) => { paperIdIndex[p.id] = i; });
}

let _searchDebounce = null;
let _lastSearchQuery = '';
let _lastKeywordMatches = [];

export function handleSearch(t) {
    t = t.trim();
    document.getElementById('search-x').style.display = t ? 'block' : 'none';

    if (!t) {
        dimExcept(null);
        document.getElementById('search-results').style.display = 'none';
        _lastSearchQuery = '';
        _lastKeywordMatches = [];
        return;
    }

    // Local keyword search (always runs instantly)
    const tl = t.toLowerCase();
    const o = state.ptsGeo.attributes.opacity, s = state.ptsGeo.attributes.size;
    const kwMatches = [];
    state.allPapers.forEach((p, i) => {
        const m = p.title.toLowerCase().includes(tl) || p._cl.name.toLowerCase().includes(tl) || (p.categories||'').toLowerCase().includes(tl) || (p.authors||'').toLowerCase().includes(tl);
        o.array[i] = m ? 1.0 : 0.03;
        s.array[i] = m ? 4.0 : 0.6;
        if (m && kwMatches.length < 5) kwMatches.push({paper: p, index: i});
    });
    o.needsUpdate = true; s.needsUpdate = true;
    _lastKeywordMatches = kwMatches;
    renderSearchDropdown(kwMatches, []);

    // Semantic search with debounce (>= 3 chars)
    if (t.length >= 3) {
        _lastSearchQuery = t;
        clearTimeout(_searchDebounce);
        _searchDebounce = setTimeout(() => {
            if (t !== _lastSearchQuery) return;
            semanticSearch(t);
        }, 300);
    }
}

async function semanticSearch(q) {
    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&k=15`);
        if (!res.ok) return;
        const data = await res.json();
        if (q !== _lastSearchQuery) return; // stale

        // Map API results to allPapers indices
        const kwIndexSet = new Set(_lastKeywordMatches.map(m => m.index));
        const semMatches = [];
        const allMatchSet = new Set(kwIndexSet);
        data.results.forEach(r => {
            const idx = paperIdIndex[r.id];
            if (idx !== undefined && !kwIndexSet.has(idx)) {
                semMatches.push({paper: state.allPapers[idx], index: idx, score: r.score});
                allMatchSet.add(idx);
            }
        });

        // Dim: highlight both keyword + semantic matches
        const o = state.ptsGeo.attributes.opacity, s = state.ptsGeo.attributes.size;
        state.allPapers.forEach((p, i) => {
            o.array[i] = allMatchSet.has(i) ? 1.0 : 0.03;
            s.array[i] = allMatchSet.has(i) ? 4.0 : 0.6;
        });
        o.needsUpdate = true; s.needsUpdate = true;

        renderSearchDropdown(_lastKeywordMatches, semMatches);
    } catch (e) {
        // Semantic search failed, keep keyword results
    }
}

function renderSearchDropdown(kwMatches, semMatches) {
    const container = document.getElementById('search-results');
    const total = kwMatches.length + semMatches.length;

    if (total === 0) {
        const clusters = state.mapData.clusters.filter(c => c.id !== -1).slice(0, 4);
        container.innerHTML = `
            <div style="padding:20px;text-align:center">
                <div style="font-size:13px;color:rgba(255,255,255,0.25);margin-bottom:12px">No results found</div>
                <div style="font-size:11px;color:rgba(255,255,255,0.2);margin-bottom:8px">Try exploring a research area:</div>
                ${clusters.map(c => `
                    <span onmousedown="document.getElementById('search').value='${c.name}';handleSearch('${c.name}')"
                        style="display:inline-block;padding:4px 10px;margin:3px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);font-size:11px;color:rgba(255,255,255,0.4);cursor:pointer">${c.name}</span>
                `).join('')}
            </div>
        `;
    } else {
        let html = '';
        if (kwMatches.length > 0) {
            html += `<div class="sr-header">Direct matches</div>`;
            html += kwMatches.map(({paper: p, index: i}) => `
                <div class="sr-item" onmousedown="searchNavigate(${i})">
                    <div class="sr-dot" style="background:${p._cl.color}"></div>
                    <div class="sr-info">
                        <div class="sr-title">${p.title}</div>
                        <div class="sr-meta">${p._cl.name} &middot; ${p.year||''}</div>
                    </div>
                </div>
            `).join('');
        }
        if (semMatches.length > 0) {
            html += `<div class="sr-header" style="${kwMatches.length ? 'border-top:1px solid rgba(255,255,255,0.06);' : ''}">Related papers</div>`;
            html += semMatches.slice(0, 10).map(({paper: p, index: i, score}) => `
                <div class="sr-item" onmousedown="searchNavigate(${i})">
                    <div class="sr-dot" style="background:${p._cl.color}"></div>
                    <div class="sr-info">
                        <div class="sr-title">${p.title}</div>
                        <div class="sr-meta">${p._cl.name} &middot; ${p.year||''} &middot; ${Math.round(score*100)}% match</div>
                    </div>
                </div>
            `).join('');
        }
        container.innerHTML = html;
    }
    container.style.display = 'block';
}

export function searchNavigate(i) {
    state.hasInteracted = true;
    const p = state.allPapers[i];
    openPaperCard(p, i);
    drawLines(i);
    flyToNeighborhood(p, i);
    state.controls.autoRotate = false;
    document.getElementById('search-results').style.display = 'none';
}

export function clearSearch(){
    document.getElementById('search').value='';
    document.getElementById('search-x').style.display='none';
    document.getElementById('search-results').style.display='none';
    dimExcept(null);
}
