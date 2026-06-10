import * as THREE from 'three';
import { state } from './state.js';
import { showBubble, hideBubbles } from './scene.js';
import { selectPaper, closeCard, drawLines, flyToNeighborhood } from './papers.js';

let hovIdx = -1;
let hoveredClusterId = null;

export function onMouse(e) {
    const m=new THREE.Vector2((e.clientX/innerWidth)*2-1,-(e.clientY/innerHeight)*2+1);
    const rc=new THREE.Raycaster();
    rc.setFromCamera(m,state.camera);
    // Scale threshold based on camera distance for consistent picking
    const camDist = state.camera.position.distanceTo(state.controls.target);
    rc.params.Points.threshold = Math.max(3, camDist * 0.015);

    // When a paper is selected, still detect hover for clicking other papers
    if (state.selectedIdx >= 0) {
        const hits=rc.intersectObject(state.ptsMesh).filter(h=>state.ptsGeo.attributes.opacity.array[h.index]>0.3);
        hovIdx = hits.length ? hits[0].index : -1;
        state.renderer.domElement.style.cursor = hovIdx >= 0 ? 'pointer' : 'default';
        document.getElementById('tooltip').style.display = 'none';
        return;
    }
    const hits=rc.intersectObject(state.ptsMesh).filter(h=>state.ptsGeo.attributes.opacity.array[h.index]>0.3);
    const tt=document.getElementById('tooltip');
    if(hits.length){
        hovIdx=hits[0].index;
        const p=state.allPapers[hovIdx];
        document.getElementById('tt-dot').style.background=p._cl.color;
        const ttCluster = document.getElementById('tt-cluster');
        ttCluster.textContent=p._cl.name;
        ttCluster.style.color=p._cl.color;
        document.getElementById('tt-cluster-desc').textContent=p._cl.description ? p._cl.description.split('.').slice(0,1).join('.')+'.':'';
        document.getElementById('tt-title').textContent=p.title;
        // Simplified abstract: first 2 sentences, max ~180 chars
        const rawAbstract = (p.abstract||'').replace(/\n/g,' ').trim();
        const sentences = rawAbstract.match(/[^.!?]+[.!?]+/g) || [];
        let shortAbstract = sentences.slice(0,2).join(' ').trim();
        if(shortAbstract.length > 180) shortAbstract = shortAbstract.slice(0,177) + '...';
        if(!shortAbstract && rawAbstract) shortAbstract = rawAbstract.slice(0,177) + '...';
        document.getElementById('tt-abstract').textContent=shortAbstract;
        const auth=p.authors?p.authors.split(/,|and/).slice(0,2).map(s=>s.trim()).join(', '):'';
        document.getElementById('tt-meta').textContent=auth+(p.year?' · '+p.year:'')+(p.categories?' · '+p.categories:'');
        tt.style.display='block';
        // Position tooltip on opposite side of card to avoid overlap
        const cardOpen = !!state.cardPaper;
        const ttWidth = 380;
        if (cardOpen) {
            // Card is on the right — force tooltip to the left side
            tt.style.left = Math.min(e.clientX + 20, innerWidth - ttWidth - 600) + 'px';
        } else {
            tt.style.left = Math.min(e.clientX + 20, innerWidth - ttWidth - 20) + 'px';
        }
        tt.style.top = Math.min(e.clientY + 20, innerHeight - 280) + 'px';
        state.renderer.domElement.style.cursor='pointer';

        // Show bubble for this point's cluster
        if(p._cl.id !== hoveredClusterId && !state.activeCluster) {
            hoveredClusterId = p._cl.id;
            showBubble(hoveredClusterId);
        }
    } else {
        hovIdx=-1; tt.style.display='none';
        state.renderer.domElement.style.cursor='default';

        // Hide bubble when not hovering any point
        if(hoveredClusterId !== null && !state.activeCluster) {
            hoveredClusterId = null;
            hideBubbles();
        }
    }
}

export function onClk() {
    if(hovIdx < 0) {
        // Clicked empty space — close card
        closeCard();
        return;
    }
    const p=state.allPapers[hovIdx];
    document.getElementById('tooltip').style.display='none';
    selectPaper(p,hovIdx);
    drawLines(hovIdx);
    flyToNeighborhood(p, hovIdx);
    state.controls.autoRotate=false;
}
