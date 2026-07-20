// search.js — keyword + semantic search and Paper Zero. Search is a
// teleport: it never builds anything, it flies you to a place in the one
// universe. All navigation goes through the machine.

import { state } from './state.js';
import { machine } from './machine.js';
import { dimExcept } from './labels.js';

export function onSearchFocus() {}

const paperIdIndex = {};
export function buildPaperIndex() {
    state.allPapers.forEach((p, i) => { paperIdIndex[p.id] = i; });
}

let _debounce = null;
let _lastQuery = '';
let _lastKw = [];

export function handleSearch(t) {
    t = t.trim();
    const xBtn = document.getElementById('search-x');
    if (xBtn) xBtn.style.display = t ? 'block' : 'none';

    if (!t) {
        restoreAfterSearch();
        document.getElementById('search-results').style.display = 'none';
        _lastQuery = '';
        _lastKw = [];
        return;
    }

    // Paper Zero: paste an arXiv id (or abs URL) and fly straight to the star.
    const arxivMatch = t.match(/(\d{4}\.\d{4,5})(v\d+)?$/) || t.match(/arxiv\.org\/abs\/(\d{4}\.\d{4,5})/);
    const arxivId = arxivMatch && (arxivMatch[1] || arxivMatch[0]);
    if (arxivId && paperIdIndex[arxivId] !== undefined) {
        searchNavigate(paperIdIndex[arxivId]);
        return;
    }

    // Keyword search (instant)
    const tl = t.toLowerCase();
    const o = state.ptsGeo.attributes.opacity, s = state.ptsGeo.attributes.size;
    const kw = [];
    state.allPapers.forEach((p, i) => {
        const m = p.title.toLowerCase().includes(tl) || p._cl.name.toLowerCase().includes(tl)
            || (p.categories || '').toLowerCase().includes(tl) || (p.authors || '').toLowerCase().includes(tl);
        o.array[i] = m ? 1.0 : 0.03;
        s.array[i] = m ? 4.0 : 0.6;
        if (m && kw.length < 5) kw.push({ paper: p, index: i });
    });
    o.needsUpdate = true; s.needsUpdate = true;
    _lastKw = kw;
    renderDropdown(kw, []);

    // Semantic search (debounced)
    if (t.length >= 3) {
        _lastQuery = t;
        clearTimeout(_debounce);
        _debounce = setTimeout(() => {
            if (t === _lastQuery) semanticSearch(t);
        }, 300);
    }
}

async function semanticSearch(q) {
    try {
        const res = await fetch(`/api/galaxy/search?q=${encodeURIComponent(q)}&k=15`);
        if (!res.ok) return;
        const data = await res.json();
        if (q !== _lastQuery) return;

        const kwSet = new Set(_lastKw.map(m => m.index));
        const sem = [];
        const all = new Set(kwSet);
        data.results.forEach(r => {
            const idx = paperIdIndex[r.id];
            if (idx !== undefined && !kwSet.has(idx)) {
                sem.push({ paper: state.allPapers[idx], index: idx, score: r.score });
                all.add(idx);
            }
        });

        const o = state.ptsGeo.attributes.opacity, s = state.ptsGeo.attributes.size;
        state.allPapers.forEach((p, i) => {
            o.array[i] = all.has(i) ? 1.0 : 0.03;
            s.array[i] = all.has(i) ? 4.0 : 0.6;
        });
        o.needsUpdate = true; s.needsUpdate = true;
        renderDropdown(_lastKw, sem);
    } catch (e) { /* keep keyword results */ }
}

function renderDropdown(kw, sem) {
    const box = document.getElementById('search-results');
    if (kw.length + sem.length === 0) {
        const clusters = state.mapData.clusters.filter(c => c.id !== -1).slice(0, 4);
        box.innerHTML = `
            <div class="sr-empty">
                <div>No results in this universe</div>
                <div class="sr-empty-sub">Try a territory:</div>
                ${clusters.map(c => `<span class="sr-suggest" data-name="${c.name}">${c.name}</span>`).join('')}
            </div>`;
        box.querySelectorAll('.sr-suggest').forEach(el => {
            el.addEventListener('mousedown', () => {
                const input = document.getElementById('search');
                input.value = el.dataset.name;
                handleSearch(el.dataset.name);
            });
        });
    } else {
        let html = '';
        if (kw.length) {
            html += `<div class="sr-header">Direct matches</div>` + kw.map(({ paper: p, index: i }) => srItem(p, i)).join('');
        }
        if (sem.length) {
            html += `<div class="sr-header" style="${kw.length ? 'border-top:1px solid rgba(255,255,255,0.06);' : ''}">Related papers</div>`
                + sem.slice(0, 10).map(({ paper: p, index: i, score }) => srItem(p, i, score)).join('');
        }
        box.innerHTML = html;
        box.querySelectorAll('.sr-item').forEach(el => {
            el.addEventListener('mousedown', () => searchNavigate(parseInt(el.dataset.idx)));
        });
    }
    box.style.display = 'block';
}

function srItem(p, i, score) {
    return `
        <div class="sr-item" data-idx="${i}">
            <div class="sr-dot" style="background:${p._cl.color}"></div>
            <div class="sr-info">
                <div class="sr-title">${p.title}</div>
                <div class="sr-meta">${p._cl.name} · ${p.year || ''}${score ? ' · ' + Math.round(score * 100) + '%' : ''}</div>
            </div>
        </div>`;
}

export function searchNavigate(i) {
    state.hasInteracted = true;
    document.getElementById('search-results').style.display = 'none';
    machine.focusPaper(i, 'search');
}

export function clearSearch() {
    const input = document.getElementById('search');
    if (input) input.value = '';
    const xBtn = document.getElementById('search-x');
    if (xBtn) xBtn.style.display = 'none';
    const box = document.getElementById('search-results');
    if (box) box.style.display = 'none';
    restoreAfterSearch();
}

// After a search highlight, restore the dimming the current mode wants.
function restoreAfterSearch() {
    const m = machine.get();
    dimExcept(m.clusterId !== null && m.mode !== 'universe' ? m.clusterId : null);
}
