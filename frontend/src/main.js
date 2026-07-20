// main.js — boot + wiring. Builds the scene, subscribes the effects layer
// to the machine, connects raw input to intents.

import './styles.css';
import './nav.css';
import { gsap } from 'gsap';
import { state, SPREAD } from './state.js';
import { machine } from './machine.js';
import { initEffects, refreshDock } from './effects.js';
import { initScene, makePoints, makeEdges, onRsz } from './scene.js';
import { makeLabels } from './labels.js';
import { makeFilters } from './filters.js';
import { buildPaperIndex, handleSearch, clearSearch, onSearchFocus } from './search.js';
import { computeBaseSizes, applyLens } from './lens.js';
import { loadSaved, openLibrary } from './library.js';
import { navBack } from './nav.js';
import { dock } from './dock.js';
import { onMouse, onClk } from './interactions.js';
import { loop } from './loop.js';

async function boot() {
    state.mapData = await (await fetch('data/map_data.json?t=' + Date.now())).json();
    const mapData = state.mapData;

    const meta = mapData.metadata;
    if (meta?.field && meta?.paper_count) {
        document.getElementById('hero-sub').textContent =
            `${meta.paper_count.toLocaleString('en-US')} papers · ${meta.field}, charted`;
    }

    // Z offsets per cluster for depth separation
    const zOffsets = {};
    mapData.clusters.forEach((cl, i) => { zOffsets[cl.id] = (Math.sin(i * 1.3) * 40) + (Math.cos(i * 0.7) * 30); });

    mapData.clusters.forEach(cl => {
        const cx = cl.center_x, cy = cl.center_y;
        const dists = cl.papers.map(p => Math.hypot(p.x - cx, p.y - cy));
        const maxDist = Math.max(...dists, 0.001);
        cl.papers.forEach((p, j) => {
            state.allPapers.push({
                ...p, _cl: cl, _centrality: 1 - (dists[j] / maxDist),
                _x: (p.x - 0.5) * SPREAD,
                _y: (p.y - 0.5) * SPREAD,
                _z: (zOffsets[cl.id] || 0) + (Math.random() - 0.5) * 35,
            });
        });
    });

    buildPaperIndex();
    computeBaseSizes('off');

    // Claimed territories (projects seeded from clusters, matched by name)
    try {
        const res = await fetch('/api/projects');
        if (res.ok) {
            const { projects } = await res.json();
            projects.forEach(pr => {
                const cl = mapData.clusters.find(c => c.name === pr.name);
                if (cl) state.claimedProjects[cl.id] = pr;
            });
        }
    } catch (e) { /* no backend — explore-only mode */ }

    initScene();
    makePoints();
    makeEdges();
    makeLabels();
    makeFilters();
    initEffects();
    document.body.dataset.mode = 'universe';
    loop();
    loadSaved();

    // --- input → intents ---
    state.renderer.domElement.addEventListener('mousemove', onMouse);
    state.renderer.domElement.addEventListener('click', onClk);
    state.renderer.domElement.addEventListener('wheel', () => { state.hasInteracted = true; state.controls.autoRotate = false; });
    state.renderer.domElement.addEventListener('mousedown', () => { state.hasInteracted = true; state.controls.autoRotate = false; });
    window.addEventListener('resize', onRsz);

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            if (dock.current() === 'library') refreshDock();
            else machine.back();
        }
        if (e.key === '/' && document.activeElement.id !== 'search') {
            e.preventDefault();
            document.getElementById('search').focus();
        }
    });

    const searchEl = document.getElementById('search');
    searchEl.addEventListener('focus', onSearchFocus);
    searchEl.addEventListener('input', e => handleSearch(e.target.value));
    document.getElementById('search-x').addEventListener('click', clearSearch);
    document.getElementById('back-btn').addEventListener('click', navBack);
    document.getElementById('nav-library').addEventListener('click', e => {
        e.preventDefault();
        openLibrary();
    });
    document.querySelectorAll('.lens-btn').forEach(btn => {
        btn.addEventListener('click', () => applyLens(btn.dataset.lens));
    });

    // --- entrance ---
    const opa = state.ptsGeo.attributes.opacity;
    for (let i = 0; i < opa.array.length; i++) opa.array[i] = 0;
    opa.needsUpdate = true;

    const loadingEl = document.getElementById('loading');
    loadingEl.style.opacity = '0';
    setTimeout(() => loadingEl.style.display = 'none', 800);

    setTimeout(() => {
        const startTime = performance.now();
        (function fadeIn() {
            const t = Math.min(1, (performance.now() - startTime) / 1500);
            for (let i = 0; i < opa.array.length; i++) opa.array[i] = t;
            opa.needsUpdate = true;
            if (t < 1) requestAnimationFrame(fadeIn);
        })();
    }, 400);

    gsap.to(document.getElementById('ui'), { opacity: 1, duration: 1.2, delay: 0.6 });
    document.querySelectorAll('.cl-label').forEach((el, i) => {
        el.style.opacity = '0';
        gsap.to(el, { opacity: 1, duration: 0.8, delay: 1.0 + i * 0.05, clearProps: 'opacity' });
    });
}

boot();
