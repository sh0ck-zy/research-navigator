import * as THREE from 'three';
import { state, SPREAD } from './state.js';
import { showBubble, hideBubbles } from './scene.js';
import { zoomToCluster, showClusterInsight, hideClusterInsight } from './clusters.js';

export function makeLabels() {
    const el=document.getElementById('labels');
    el.innerHTML='';
    const counts = state.mapData.clusters.filter(c=>c.id!==-1).map(c=>c.paper_count);
    const minC = Math.min(...counts), maxC = Math.max(...counts);
    state.mapData.clusters.forEach(cl=>{
        if(cl.id===-1)return;
        const d=document.createElement('div');
        d.className='cl-label';
        d.dataset.cid=cl.id;
        d.style.pointerEvents='auto';
        const t = maxC > minC ? (cl.paper_count - minC) / (maxC - minC) : 0.5;
        const fontSize = Math.round(10 + t * 8); // 10px → 18px
        d.innerHTML=`<div class="cl-name" style="font-size:${fontSize}px">${cl.name}</div><div class="cl-count">${cl.paper_count.toLocaleString()} papers</div>`;
        d.onclick=e=>{e.stopPropagation();state.hasInteracted=true;zoomToCluster(cl);};
        d.onmouseenter=(e)=>{dimExcept(cl.id);showBubble(cl.id);showClusterInsight(cl,e);};
        d.onmouseleave=()=>{if(!state.activeCluster){dimExcept(null);hideBubbles();}hideClusterInsight();};
        el.appendChild(d);
    });
}

export function updateLabels() {
    const camDist = state.camera.position.distanceTo(state.controls.target);
    const isLanding = camDist >= 420;
    // Labels hidden during landing, fade in as we zoom in
    const baseLabelOpacity = isLanding ? 0 : Math.max(0.5, Math.min(1, (420 - camDist) / 100));

    document.querySelectorAll('.cl-label').forEach(el=>{
        const cl=state.mapData.clusters.find(c=>c.id==el.dataset.cid);
        if(!cl)return;
        const v=new THREE.Vector3(
            (cl.center_x-0.5)*SPREAD,
            (cl.center_y-0.5)*SPREAD,
            (Math.sin(state.mapData.clusters.indexOf(cl)*1.3)*40)+(Math.cos(state.mapData.clusters.indexOf(cl)*0.7)*30)
        ).project(state.camera);
        const x=(v.x*0.5+0.5)*innerWidth;
        const y=(-v.y*0.5+0.5)*innerHeight;
        el.style.left=x+'px';
        el.style.top=y+'px';
        el.style.display = (v.z < 1 && baseLabelOpacity > 0) ? '' : 'none';
        // Only set opacity if not overridden by dimExcept
        if(!state.activeCluster) el.style.opacity = baseLabelOpacity;
    });
}

export function dimExcept(cid) {
    const o=state.ptsGeo.attributes.opacity, s=state.ptsGeo.attributes.size;
    state.allPapers.forEach((p,i)=>{
        const baseSize = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        if(cid===null) { o.array[i]=1.0; s.array[i]=baseSize; }
        else if(p._cl.id===cid) { o.array[i]=1.0; s.array[i]=baseSize*1.4; }
        else { o.array[i]=0.3; s.array[i]=baseSize*0.7; }
    });
    o.needsUpdate=true; s.needsUpdate=true;

    document.querySelectorAll('.cl-label').forEach(el=>{
        if(cid===null) { el.style.opacity=''; el.classList.remove('dim'); }
        else {
            const isTarget = parseInt(el.dataset.cid)===cid;
            el.classList.remove('dim');
            el.style.opacity = isTarget ? '1' : '0.4';
        }
    });
}
