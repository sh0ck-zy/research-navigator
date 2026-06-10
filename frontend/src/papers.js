import * as THREE from 'three';
import { gsap } from 'gsap';
import { state } from './state.js';
import { updateNavContext } from './nav.js';
import { updateStats } from './stats.js';

let conLines = null;
let selectedOrigSize = 0;
let _niHideTimeout = null;

// === PAPER LINES ===
export function drawLines(ci) {
    if(conLines)state.scene.remove(conLines);
    const allPapers = state.allPapers;
    const ctr=allPapers[ci];
    const nbs=allPapers.map((p,i)=>({p,i,d:Math.sqrt((p._x-ctr._x)**2+(p._y-ctr._y)**2+(p._z-ctr._z)**2)})).filter(o=>o.i!==ci).sort((a,b)=>a.d-b.d).slice(0,6);
    const pos=[],cols=[];
    const cc=new THREE.Color(ctr._cl.color);
    nbs.forEach(({p})=>{const nc=new THREE.Color(p._cl.color);pos.push(ctr._x,ctr._y,ctr._z,p._x,p._y,p._z);cols.push(cc.r,cc.g,cc.b,nc.r,nc.g,nc.b);});
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
    g.setAttribute('color',new THREE.Float32BufferAttribute(cols,3));
    conLines=new THREE.LineSegments(g,new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:0.2,blending:THREE.AdditiveBlending}));
    state.scene.add(conLines);
}

// === NODE INFO (anchored to selected paper) ===
export function selectPaper(p, idx) {
    if (state.selectedIdx >= 0) deselectPaper();

    // Force-reset any lingering pushed papers to their original positions
    if (state.pushedPapers.length > 0) {
        const posArr = state.ptsGeo.attributes.position.array;
        state.pushedPapers.forEach(pp => {
            posArr[pp.index*3] = pp.origX;
            posArr[pp.index*3+1] = pp.origY;
            posArr[pp.index*3+2] = pp.origZ;
        });
        state.ptsGeo.attributes.position.needsUpdate = true;
        state.pushedPapers = [];
        state.pushDirection = 0;
        state.pushProgress = 0;
    }

    state.selectedIdx = idx;
    state.cardPaper = p;

    // Grow the selected point
    const sizeArr = state.ptsGeo.attributes.size.array;
    selectedOrigSize = sizeArr[idx];
    sizeArr[idx] = selectedOrigSize * 4.5;
    state.ptsGeo.attributes.size.needsUpdate = true;

    // Gravitational push: find 12 nearest neighbors and push outward
    const PUSH_DIST = 18;
    const posArr = state.ptsGeo.attributes.position.array;
    const neighbors = state.allPapers
        .map((q, i) => ({ i, d: Math.sqrt((q._x-p._x)**2+(q._y-p._y)**2+(q._z-p._z)**2) }))
        .filter(o => o.i !== idx)
        .sort((a, b) => a.d - b.d)
        .slice(0, 12);
    state.pushedPapers = neighbors.map(({ i: ni }) => {
        // Use the canonical positions from allPapers, not the buffer (which might be stale)
        const ox = state.allPapers[ni]._x, oy = state.allPapers[ni]._y, oz = state.allPapers[ni]._z;
        posArr[ni*3] = ox; posArr[ni*3+1] = oy; posArr[ni*3+2] = oz;
        const dx = ox - p._x, dy = oy - p._y, dz = oz - p._z;
        const len = Math.sqrt(dx*dx+dy*dy+dz*dz) || 1;
        return { index:ni, origX:ox, origY:oy, origZ:oz,
            targetX: ox+(dx/len)*PUSH_DIST, targetY: oy+(dy/len)*PUSH_DIST, targetZ: oz+(dz/len)*PUSH_DIST };
    });
    state.pushProgress = 0;
    state.pushDirection = 1;

    // Centrality percentile
    const clPapers = state.allPapers.filter(q => q._cl.id === p._cl.id);
    const rank = clPapers.filter(q => (q._centrality||0) <= (p._centrality||0)).length;
    const percentile = Math.round((rank / clPapers.length) * 100);

    // Abstract: first 2 sentences
    const rawAbstract = (p.abstract||'').replace(/\n/g,' ').trim();
    const sentences = rawAbstract.match(/[^.!?]+[.!?]+/g) || [];
    let shortAbstract = sentences.slice(0,2).join(' ').trim();
    if(shortAbstract.length > 160) shortAbstract = shortAbstract.slice(0,157) + '...';
    if(!shortAbstract && rawAbstract) shortAbstract = rawAbstract.slice(0,157) + '...';

    const auth = p.authors ? p.authors.split(/,|and/).slice(0,2).map(s=>s.trim()).join(', ') : '';

    const ni = document.getElementById('node-info');
    ni.innerHTML = `
        <div class="ni-header">
            <div style="width:6px;height:6px;border-radius:50%;background:${p._cl.color}"></div>
            <span style="font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:${p._cl.color}">${p._cl.name}</span>
            <button class="ni-close" onclick="deselectPaper()">&times;</button>
        </div>
        <div class="ni-body">
            <div class="ni-title">${p.title}</div>
            <div class="ni-meta">${auth}${p.year ? ' · '+p.year : ''}${p.venue ? ' · '+p.venue : ''}</div>
            <div class="ni-centrality" style="background:${p._cl.color}15;color:${p._cl.color}">Top ${100-percentile}%</div>
            <div class="ni-abstract">${shortAbstract}</div>
            <div class="ni-actions">
                <button class="ni-act${state.savedIds.has(p.id) ? ' saved' : ''}" id="ni-save" data-idx="${idx}" onclick="toggleSave(${idx})">${state.savedIds.has(p.id) ? 'Saved ✓' : 'Save'}</button>
                <button class="ni-act" onclick="copyCite(${idx}, this)">Cite</button>
                <a class="ni-act" href="${p.doi ? 'https://doi.org/'+p.doi : 'https://openalex.org/'+p.id}" target="_blank" rel="noopener">Open ↗</a>
            </div>
        </div>
    `;
    clearTimeout(_niHideTimeout);
    ni.style.display = 'block';
    requestAnimationFrame(() => ni.classList.add('visible'));
    updateNavContext(); updateStats();
}

export function deselectPaper() {
    if (state.selectedIdx >= 0) {
        state.ptsGeo.attributes.size.array[state.selectedIdx] = selectedOrigSize;
        state.ptsGeo.attributes.size.needsUpdate = true;
    }
    state.selectedIdx = -1;
    state.cardPaper = null;
    // Trigger push retraction (loop will lerp back)
    state.pushDirection = -1;
    const ni = document.getElementById('node-info');
    ni.classList.remove('visible');
    clearTimeout(_niHideTimeout);
    _niHideTimeout = setTimeout(() => { ni.style.display = 'none'; }, 250);
    if(conLines) { state.scene.remove(conLines); conLines = null; }
    updateNavContext(); updateStats();
}

// Legacy aliases
export function openPaperCard(p, idx) { selectPaper(p, idx); }
export function closeCard() { deselectPaper(); }

export function flyToNeighborhood(p, idx) {
    const nbs = state.allPapers
        .map((q,i) => ({q,i,d:Math.sqrt((q._x-p._x)**2+(q._y-p._y)**2+(q._z-p._z)**2)}))
        .filter(o => o.i !== idx)
        .sort((a,b) => a.d - b.d)
        .slice(0, 6);

    let sumX=p._x, sumY=p._y, sumZ=p._z;
    nbs.forEach(({q}) => { sumX+=q._x; sumY+=q._y; sumZ+=q._z; });
    const count = nbs.length + 1;
    const cx=sumX/count, cy=sumY/count, cz=sumZ/count;

    let maxR = 0;
    [p, ...nbs.map(n=>n.q)].forEach(q => {
        const d = Math.sqrt((q._x-cx)**2+(q._y-cy)**2+(q._z-cz)**2);
        if(d > maxR) maxR = d;
    });

    const fovRad = (state.camera.fov/2) * Math.PI / 180;
    const camDist = Math.max(80, (maxR / Math.tan(fovRad)) * 1.8);

    gsap.to(state.camera.position, { x:cx, y:cy+camDist*0.25, z:cz+camDist, duration:1.8, ease:'expo.out' });
    gsap.to(state.controls.target, { x:cx, y:cy, z:cz, duration:1.8, ease:'expo.out' });
}
