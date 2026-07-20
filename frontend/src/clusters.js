import * as THREE from 'three';
import { gsap } from 'gsap';
import { state, SPREAD } from './state.js';
import { showBubble, hideBubbles } from './scene.js';
import { dimExcept } from './labels.js';
import { deselectPaper } from './papers.js';
import { updateNavContext } from './nav.js';
import { updateStats } from './stats.js';
import { closeClusterIntel } from './intel.js';
import { enterChartMode, exitChartMode, isCharting } from './chart.js';

// === CLUSTER INSIGHT CARD ===
export function showClusterInsight(cl, e) {
    const card = document.getElementById('cluster-insight');
    const totalPapers = state.mapData.metadata.paper_count;
    const share = (cl.paper_count / totalPapers * 100).toFixed(1);

    // King papers (top 3 by centrality)
    const clPapers = state.allPapers.filter(p => p._cl.id === cl.id);
    const kings = clPapers.slice().sort((a,b) => (b._centrality||0) - (a._centrality||0)).slice(0, 3);

    // Trend: last 6 years
    const yearCounts = {};
    cl.papers.forEach(p => { if (p.year) yearCounts[p.year] = (yearCounts[p.year]||0) + 1; });
    const years = Object.keys(yearCounts).sort().slice(-6);
    const maxYearCount = Math.max(...years.map(y => yearCounts[y]), 1);

    // Connections
    const conns = (state.mapData.connections || [])
        .filter(c => c.from === cl.id || c.to === cl.id)
        .map(c => {
            const otherId = c.from === cl.id ? c.to : c.from;
            const other = state.mapData.clusters.find(x => x.id === otherId);
            return other ? { cluster: other, strength: c.strength } : null;
        })
        .filter(Boolean)
        .sort((a, b) => b.strength - a.strength)
        .slice(0, 3);

    // Year range
    const allYears = cl.papers.map(p => p.year).filter(Boolean);
    const minYear = Math.min(...allYears);
    const maxYear = Math.max(...allYears);

    card.innerHTML = `
        <div class="ci-header">
            <div style="width:10px;height:10px;border-radius:50%;background:${cl.color};flex-shrink:0"></div>
            <div class="ci-name">${cl.name}</div>
        </div>
        <div class="ci-desc">${cl.description ? cl.description.split('.').slice(0,2).join('.')+'.':''}</div>
        <div class="ci-stats">
            <div class="ci-stat">
                <div class="ci-stat-val">${cl.paper_count.toLocaleString()}</div>
                <div class="ci-stat-lbl">Papers</div>
            </div>
            <div class="ci-stat">
                <div class="ci-stat-val" style="color:${cl.color}">${share}%</div>
                <div class="ci-stat-lbl">Share</div>
            </div>
            <div class="ci-stat">
                <div class="ci-stat-val">${minYear}–${maxYear}</div>
                <div class="ci-stat-lbl">Span</div>
            </div>
        </div>
        ${years.length > 1 ? `
        <div class="ci-section" style="padding-bottom:8px">
            <div class="ci-section-title">Trend</div>
            <div class="ci-trend">
                ${years.map(y => `<div class="ci-trend-bar" style="height:${Math.max(2,(yearCounts[y]/maxYearCount)*28)}px;background:${cl.color}60"></div>`).join('')}
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:3px">
                <span style="font-size:8px;color:rgba(255,255,255,0.2)">${years[0]}</span>
                <span style="font-size:8px;color:rgba(255,255,255,0.2)">${years[years.length-1]}</span>
            </div>
        </div>` : ''}
        <div class="ci-section">
            <div class="ci-section-title">Key Papers</div>
            ${kings.map(p => `<div class="ci-king"><div class="ci-king-dot" style="background:${cl.color}"></div><div class="ci-king-title">${p.title}</div></div>`).join('')}
        </div>
        ${conns.length ? `
        <div class="ci-section" style="padding-bottom:16px">
            <div class="ci-section-title">Connected Areas</div>
            ${conns.map(c => `<span class="ci-conn" style="color:${c.cluster.color};border:1px solid ${c.cluster.color}30;background:${c.cluster.color}08"><span style="width:5px;height:5px;border-radius:50%;background:${c.cluster.color}"></span>${c.cluster.name}</span>`).join('')}
        </div>` : ''}
    `;

    // Position near the label
    const labelEl = document.querySelector(`.cl-label[data-cid="${cl.id}"]`);
    if (labelEl) {
        const rect = labelEl.getBoundingClientRect();
        const cardW = 340;
        let left = rect.right + 12;
        let top = rect.top - 40;
        // Keep on screen
        if (left + cardW > innerWidth - 20) left = rect.left - cardW - 12;
        if (top + 400 > innerHeight - 20) top = innerHeight - 420;
        if (top < 20) top = 20;
        card.style.left = left + 'px';
        card.style.top = top + 'px';
    }
    card.style.display = 'block';
}

export function hideClusterInsight() {
    document.getElementById('cluster-insight').style.display = 'none';
}

// === CLUSTER CONNECTION LINES ===
let clusterConLines = null;

export function drawClusterConnections(clId) {
    if (clusterConLines) state.scene.remove(clusterConLines);
    const conns = (state.mapData.connections || []).filter(c => c.from === clId || c.to === clId);
    if (!conns.length) return;

    const cl = state.mapData.clusters.find(c => c.id === clId);
    if (!cl) return;
    const zIdx = state.mapData.clusters.indexOf(cl);
    const fromX = (cl.center_x - 0.5) * SPREAD;
    const fromY = (cl.center_y - 0.5) * SPREAD;
    const fromZ = (Math.sin(zIdx * 1.3) * 40) + (Math.cos(zIdx * 0.7) * 30);

    const pos = [], cols = [];
    const fc = new THREE.Color(cl.color);

    conns.forEach(c => {
        const otherId = c.from === clId ? c.to : c.from;
        const other = state.mapData.clusters.find(x => x.id === otherId);
        if (!other) return;
        const oIdx = state.mapData.clusters.indexOf(other);
        const toX = (other.center_x - 0.5) * SPREAD;
        const toY = (other.center_y - 0.5) * SPREAD;
        const toZ = (Math.sin(oIdx * 1.3) * 40) + (Math.cos(oIdx * 0.7) * 30);
        const tc = new THREE.Color(other.color);
        pos.push(fromX, fromY, fromZ, toX, toY, toZ);
        cols.push(fc.r, fc.g, fc.b, tc.r, tc.g, tc.b);
    });

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    clusterConLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.35,
        blending: THREE.AdditiveBlending, depthWrite: false
    }));
    state.scene.add(clusterConLines);
}

export function removeClusterConnections() {
    if (clusterConLines) { state.scene.remove(clusterConLines); clusterConLines = null; }
}

// === BRIDGE LABELS (neighbour-area names at the midpoint of the strongest links) ===
function clusterPos(cl) {
    const zIdx = state.mapData.clusters.indexOf(cl);
    return new THREE.Vector3(
        (cl.center_x - 0.5) * SPREAD,
        (cl.center_y - 0.5) * SPREAD,
        (Math.sin(zIdx * 1.3) * 40) + (Math.cos(zIdx * 0.7) * 30),
    );
}

export function buildBridgeLabels(clId) {
    clearBridgeLabels();
    const cl = state.mapData.clusters.find(c => c.id === clId);
    if (!cl) return;
    const from = clusterPos(cl);
    const conns = (state.mapData.connections || [])
        .filter(c => c.from === clId || c.to === clId)
        .sort((a, b) => b.strength - a.strength)
        .slice(0, 3);
    conns.forEach(c => {
        const otherId = c.from === clId ? c.to : c.from;
        const other = state.mapData.clusters.find(x => x.id === otherId);
        if (!other) return;
        const to = clusterPos(other);
        const mid = from.clone().lerp(to, 0.5);
        const el = document.createElement('div');
        el.className = 'bridge-label';
        el.textContent = other.name;
        el.style.color = other.color;
        document.body.appendChild(el);
        requestAnimationFrame(() => el.classList.add('visible'));
        state.bridgeLabels.push({ el, pos: mid });
    });
}

export function clearBridgeLabels() {
    state.bridgeLabels.forEach(({ el }) => el.remove());
    state.bridgeLabels = [];
}

// === CLUSTER CONTEXT ===
export function showClusterContext(cl) {
    const cc = document.getElementById('cluster-context');
    const totalPapers = state.mapData.metadata.paper_count;
    const share = (cl.paper_count / totalPapers * 100).toFixed(1);
    const desc = cl.description ? cl.description.split('.').slice(0,2).join('.')+'.' : '';
    const kings = state.allPapers.filter(p=>p._cl.id===cl.id).sort((a,b)=>(b._centrality||0)-(a._centrality||0)).slice(0,3);

    // Trend
    const yearCounts = {};
    cl.papers.forEach(p => { if(p.year) yearCounts[p.year]=(yearCounts[p.year]||0)+1; });
    const years = Object.keys(yearCounts).sort().slice(-6);
    const maxYC = Math.max(...years.map(y=>yearCounts[y]),1);

    cc.innerHTML = `
        <div style="padding:16px 20px 12px;display:flex;align-items:center;gap:10px">
            <div style="width:10px;height:10px;border-radius:50%;background:${cl.color}"></div>
            <div style="font-family:'Playfair Display',serif;font-size:18px;font-weight:500;color:#fff">${cl.name}</div>
        </div>
        <div style="padding:0 20px 12px;font-size:11px;color:rgba(255,255,255,0.35);line-height:1.5">${desc}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:rgba(255,255,255,0.04)">
            <div style="padding:10px 14px;background:rgba(12,12,16,0.97);text-align:center">
                <div style="font-size:16px;font-weight:600;color:rgba(255,255,255,0.85)">${cl.paper_count.toLocaleString()}</div>
                <div style="font-size:8px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-top:2px">Papers</div>
            </div>
            <div style="padding:10px 14px;background:rgba(12,12,16,0.97);text-align:center">
                <div style="font-size:16px;font-weight:600;color:${cl.color}">${share}%</div>
                <div style="font-size:8px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-top:2px">Share</div>
            </div>
            <div style="padding:10px 14px;background:rgba(12,12,16,0.97);text-align:center">
                <div style="font-size:16px;font-weight:600;color:rgba(255,255,255,0.85)">${years[0]||''}–${years[years.length-1]||''}</div>
                <div style="font-size:8px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-top:2px">Span</div>
            </div>
        </div>
        ${years.length>1?`<div style="padding:12px 20px 8px">
            <div style="font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:rgba(255,255,255,0.25);margin-bottom:6px">Trend</div>
            <div style="display:flex;align-items:flex-end;gap:2px;height:28px">
                ${years.map(y=>`<div style="flex:1;border-radius:1px 1px 0 0;height:${Math.max(2,(yearCounts[y]/maxYC)*26)}px;background:${cl.color}60"></div>`).join('')}
            </div>
        </div>`:''}
        <div style="padding:12px 20px 16px">
            <div style="font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:rgba(255,255,255,0.25);margin-bottom:6px">Key Papers</div>
            ${kings.map(p=>`<div style="font-size:11px;color:rgba(255,255,255,0.6);padding:3px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.title}</div>`).join('')}
        </div>
        <div style="padding:0 20px 16px">
            <button onclick="openActiveClusterIntel()" style="width:100%;background:rgba(255,255,255,0.92);border:none;color:#111;padding:8px 0;border-radius:16px;font-size:12px;font-weight:600;font-family:'Inter',sans-serif;cursor:pointer">Cluster intelligence →</button>
        </div>
    `;
    cc.style.display = 'block';
    requestAnimationFrame(() => cc.classList.add('visible'));
}

export function hideClusterContext() {
    const cc = document.getElementById('cluster-context');
    cc.classList.remove('visible');
    setTimeout(() => { cc.style.display = 'none'; }, 350);
}

export function showKingPapers(cl) {
    hideKingPapers();
    const clPapers = state.allPapers.map((p,i)=>({p,i})).filter(o=>o.p._cl.id===cl.id)
        .sort((a,b)=>b.p._centrality-a.p._centrality).slice(0,3);
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    clPapers.forEach(({p,i})=>{
        state.kingPapers.push({index:i, origSize:sizeArr[i], origOpacity:opaArr[i]});
        const base = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        sizeArr[i] = base * 1.4 * 3;
        opaArr[i] = 1.0;
        const el = document.createElement('div');
        el.className = 'king-label';
        el.textContent = p.title.length > 45 ? p.title.slice(0,42)+'...' : p.title;
        el.style.borderLeft = '2px solid '+cl.color;
        document.body.appendChild(el);
        requestAnimationFrame(()=>el.classList.add('visible'));
        state.kingLabelEls.push({el, index:i});
    });
    state.ptsGeo.attributes.size.needsUpdate = true;
    state.ptsGeo.attributes.opacity.needsUpdate = true;
}

export function hideKingPapers() {
    const sizeArr = state.ptsGeo.attributes.size.array;
    const opaArr = state.ptsGeo.attributes.opacity.array;
    state.kingPapers.forEach(kp=>{
        sizeArr[kp.index]=kp.origSize;
        opaArr[kp.index]=kp.origOpacity;
    });
    if(state.kingPapers.length){
        state.ptsGeo.attributes.size.needsUpdate=true;
        state.ptsGeo.attributes.opacity.needsUpdate=true;
    }
    state.kingPapers=[];
    state.kingLabelEls.forEach(({el})=>el.remove());
    state.kingLabelEls=[];
}

export function exitCluster() {
    state.activeCluster = null;
    state.clusterZoomDist = 0;
    dimExcept(null);
    hideBubbles();
    removeClusterConnections();
    clearBridgeLabels();
    hideClusterContext();
    hideKingPapers();
    closeClusterIntel();
    exitChartMode();
}

export function zoomToCluster(cl) {
    deselectPaper();
    state.activeCluster = cl.id;
    dimExcept(cl.id);
    showBubble(cl.id);
    hideClusterInsight();
    drawClusterConnections(cl.id);
    buildBridgeLabels(cl.id);
    showClusterContext(cl);
    state.controls.autoRotate = false;
    updateNavContext(); updateStats();

    const cx = (cl.center_x - 0.5) * SPREAD;
    const cy = (cl.center_y - 0.5) * SPREAD;
    const zIdx = state.mapData.clusters.indexOf(cl);
    const cz = (Math.sin(zIdx * 1.3) * 40) + (Math.cos(zIdx * 0.7) * 30);

    const dists = cl.papers.map(p => {
        const px = (p.x - 0.5) * SPREAD, py = (p.y - 0.5) * SPREAD;
        return Math.sqrt((px-cx)**2 + (py-cy)**2);
    }).sort((a,b) => a-b);
    const radius = dists[Math.floor(dists.length * 0.80)] || 50;
    const fovRad = (state.camera.fov/2) * Math.PI / 180;
    const camDist = Math.max(120, (radius / Math.tan(fovRad)) * 1.8);

    gsap.to(state.camera.position, { x:cx, y:cy+camDist*0.3, z:cz+camDist, duration:1.8, ease:'expo.out', onComplete:()=>{ state.clusterZoomDist=camDist; } });
    gsap.to(state.controls.target, { x:cx, y:cy, z:cz, duration:1.8, ease:'expo.out' });

    // Return dance: entering a claimed territory re-enters chart mode.
    const claimed = state.claimedProjects && state.claimedProjects[cl.id];
    if (claimed && !isCharting()) enterChartMode(claimed, cl);
}
