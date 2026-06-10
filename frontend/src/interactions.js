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
        // Light hover: dot · title · year. The full card (abstract, actions) is on click.
        document.getElementById('tt-dot').style.background=p._cl.color;
        document.getElementById('tt-title').textContent=p.title;
        document.getElementById('tt-year').textContent=p.year || '';
        // A cluster card and a paper tooltip never co-show
        document.getElementById('cluster-insight').style.display='none';
        tt.style.display='flex';
        const ttW = Math.min(tt.offsetWidth || 320, 380);
        tt.style.left = Math.min(e.clientX + 16, innerWidth - ttW - 16) + 'px';
        tt.style.top = Math.min(e.clientY + 18, innerHeight - 48) + 'px';
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
