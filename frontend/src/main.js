import './styles.css';
import { gsap } from 'gsap';
import { state, SPREAD } from './state.js';
import { initScene, makePoints, makeEdges, onRsz } from './scene.js';
import { makeLabels } from './labels.js';
import { makeFilters, applyFilter } from './filters.js';
import { makeStats } from './stats.js';
import { buildPaperIndex, handleSearch, searchNavigate, clearSearch, onSearchFocus } from './search.js';
import { computeBaseSizes, applyLens } from './lens.js';
import { loadSaved, toggleSave, copyCite, openLibrary, closeLibrary } from './library.js';
import { deselectPaper, closeCard } from './papers.js';
import { navBack, resetView, updateNavContext } from './nav.js';
import { onMouse, onClk } from './interactions.js';
import { loop } from './loop.js';

// Dynamically generated HTML (search dropdown, filters, node-info, breadcrumb)
// uses inline on* attributes, which resolve against window.
Object.assign(window, {
    searchNavigate, handleSearch, applyFilter,
    deselectPaper, resetView, updateNavContext,
    toggleSave, copyCite, openLibrary, closeLibrary,
});

async function boot() {
    state.mapData = await (await fetch('data/map_data.json?t=' + Date.now())).json();
    const mapData = state.mapData;

    const meta = mapData.metadata;
    if (meta?.field && meta?.paper_count) {
        document.getElementById('hero-sub').textContent =
            `${meta.paper_count.toLocaleString('en-US')} ${meta.field} papers, mapped by AI`;
    }

    // Assign Z offsets per cluster for depth separation
    const zOffsets = {};
    mapData.clusters.forEach((cl,i) => { zOffsets[cl.id] = (Math.sin(i*1.3)*40) + (Math.cos(i*0.7)*30); });

    mapData.clusters.forEach(cl => {
        // Compute centrality for each paper (distance to cluster center)
        const cx = cl.center_x, cy = cl.center_y;
        const dists = cl.papers.map(p => Math.sqrt((p.x-cx)**2 + (p.y-cy)**2));
        const maxDist = Math.max(...dists, 0.001);

        cl.papers.forEach((p, j) => {
            const centrality = 1 - (dists[j] / maxDist); // 1 = center, 0 = edge
            state.allPapers.push({
                ...p, _cl:cl, _centrality: centrality,
                _x: (p.x - 0.5) * SPREAD,
                _y: (p.y - 0.5) * SPREAD,
                _z: (zOffsets[cl.id]||0) + (Math.random()-0.5)*35
            });
        });
    });

    buildPaperIndex();
    computeBaseSizes('off'); // seed base star sizes before geometry is built
    initScene();
    makePoints();
    makeEdges();
    makeLabels();
    makeFilters();
    makeStats();
    loop();
    loadSaved(); // fetch saved library + draw ring markers (scene is ready)

    state.renderer.domElement.addEventListener('mousemove', onMouse);
    state.renderer.domElement.addEventListener('click', onClk);
    state.renderer.domElement.addEventListener('wheel', () => { state.hasInteracted = true; });
    state.renderer.domElement.addEventListener('mousedown', () => { state.hasInteracted = true; });
    window.addEventListener('resize', onRsz);
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            if (state.cardPaper) { closeCard(); }
            else { resetView(); clearSearch(); }
        }
        if (e.key === '/') { e.preventDefault(); document.getElementById('search').focus(); }
    });

    const searchEl = document.getElementById('search');
    searchEl.addEventListener('focus', onSearchFocus);
    searchEl.addEventListener('input', e => handleSearch(e.target.value));
    document.getElementById('search-x').addEventListener('click', clearSearch);
    document.getElementById('back-btn').addEventListener('click', navBack);
    document.querySelectorAll('.lens-btn').forEach(btn => {
        btn.addEventListener('click', () => applyLens(btn.dataset.lens));
    });

    // Entrance animation
    // Start with all points invisible
    const opa = state.ptsGeo.attributes.opacity;
    for (let i = 0; i < opa.array.length; i++) opa.array[i] = 0;
    opa.needsUpdate = true;

    // Fade out loading screen
    const loadingEl = document.getElementById('loading');
    loadingEl.style.opacity = '0';
    setTimeout(() => loadingEl.style.display = 'none', 800);

    // Fade in points over 1.5s
    const startTime = performance.now();
    function fadeInPoints() {
        const elapsed = (performance.now() - startTime) / 1500;
        const t = Math.min(1, elapsed);
        for (let i = 0; i < opa.array.length; i++) opa.array[i] = t;
        opa.needsUpdate = true;
        if (t < 1) requestAnimationFrame(fadeInPoints);
    }
    setTimeout(fadeInPoints, 400);

    // Fade in UI
    gsap.to(document.getElementById('ui'), { opacity: 1, duration: 1.2, delay: 0.6 });
    // Fade in labels
    document.querySelectorAll('.cl-label').forEach((el, i) => {
        el.style.opacity = '0';
        gsap.to(el, { opacity: 1, duration: 0.8, delay: 1.0 + i * 0.05 });
    });
}

boot();
