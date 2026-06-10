import * as THREE from 'three';
import { state } from './state.js';
import { updateLabels } from './labels.js';
import { exitCluster } from './clusters.js';

export function loop(){
    requestAnimationFrame(loop);
    state.controls.update();
    updateLabels();
    // Hero only visible at true max zoom-out AND no card open AND after resetView
    const dist = state.camera.position.distanceTo(state.controls.target);
    const heroEl = document.getElementById('hero');
    const showHero = !state.hasInteracted && dist >= 460 && state.activeCluster === null && state.selectedIdx < 0;
    const heroTarget = showHero ? 1 : 0;
    const heroCurrent = parseFloat(heroEl.style.opacity) || 0;
    const heroNew = heroCurrent + (heroTarget - heroCurrent) * 0.12;
    heroEl.style.opacity = heroNew < 0.01 ? 0 : heroNew;
    heroEl.style.pointerEvents = (heroNew > 0.5 && showHero) ? '' : 'none';
    // Hide all interactive children when hero is not showing to unblock canvas
    if (heroNew < 0.01) {
        heroEl.style.visibility = 'hidden';
    } else {
        heroEl.style.visibility = '';
    }
    // Stats: hide when card open or hero showing
    const statsOpacity = state.cardPaper ? 0 : (showHero ? 0 : 1);
    document.getElementById('right-stats').style.opacity = statsOpacity;

    // Progressive edges: fade in when zoomed in
    if (state.edgesMesh) {
        const edgeOpacity = Math.max(0, Math.min(0.08, (250 - dist) / 200));
        state.edgesMesh.material.opacity = edgeOpacity;
    }

    // Auto-exit cluster on zoom-out
    if (state.activeCluster !== null && state.clusterZoomDist > 0) {
        if (dist > state.clusterZoomDist * 2.0) exitCluster();
    }

    // Position king paper labels
    state.kingLabelEls.forEach(({el, index})=>{
        const p=state.allPapers[index];
        const v=new THREE.Vector3(p._x,p._y,p._z).project(state.camera);
        el.style.left=(v.x*0.5+0.5)*innerWidth+'px';
        el.style.top=((-v.y*0.5+0.5)*innerHeight-18)+'px';
        el.style.display=v.z<1?'':'none';
    });

    // Position bridge labels (neighbour-area names on inter-cluster links)
    state.bridgeLabels.forEach(({el, pos})=>{
        const v=pos.clone().project(state.camera);
        el.style.left=(v.x*0.5+0.5)*innerWidth+'px';
        el.style.top=(-v.y*0.5+0.5)*innerHeight+'px';
        el.style.display=v.z<1?'':'none';
    });

    // Gravitational push animation
    if (state.pushedPapers.length > 0) {
        state.pushProgress += (state.pushDirection > 0 ? 0.06 : -0.08);
        state.pushProgress = Math.max(0, Math.min(1, state.pushProgress));
        const posArr = state.ptsGeo.attributes.position.array;
        const et = state.pushDirection > 0 ? (1 - Math.pow(1 - state.pushProgress, 3)) : state.pushProgress;
        state.pushedPapers.forEach(pp => {
            posArr[pp.index*3]   = pp.origX + (pp.targetX - pp.origX) * et;
            posArr[pp.index*3+1] = pp.origY + (pp.targetY - pp.origY) * et;
            posArr[pp.index*3+2] = pp.origZ + (pp.targetZ - pp.origZ) * et;
        });
        state.ptsGeo.attributes.position.needsUpdate = true;
        if (state.pushProgress <= 0 && state.pushDirection < 0) {
            state.pushedPapers.forEach(pp => {
                posArr[pp.index*3]=pp.origX; posArr[pp.index*3+1]=pp.origY; posArr[pp.index*3+2]=pp.origZ;
            });
            state.ptsGeo.attributes.position.needsUpdate = true;
            state.pushedPapers = [];
            state.pushDirection = 0;
        }
    }

    // Position node-info anchored to selected paper
    if (state.selectedIdx >= 0) {
        const sp = state.allPapers[state.selectedIdx];
        const v = new THREE.Vector3(sp._x, sp._y, sp._z).project(state.camera);
        const sx = (v.x * 0.5 + 0.5) * innerWidth;
        const sy = (-v.y * 0.5 + 0.5) * innerHeight;
        const ni = document.getElementById('node-info');
        let left = sx + 24, top = sy - 20;
        if (left + 320 > innerWidth - 20) left = sx - 344;
        if (top + 300 > innerHeight - 20) top = innerHeight - 320;
        if (top < 20) top = 20;
        ni.style.left = left + 'px';
        ni.style.top = top + 'px';
        ni.style.display = v.z > 1 ? 'none' : 'block';
    }

    state.renderer.render(state.scene,state.camera);
}
