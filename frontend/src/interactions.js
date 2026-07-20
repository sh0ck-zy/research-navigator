// interactions.js — mouse picking. Translates raw input into machine
// intents; contains no visual logic of its own.

import * as THREE from 'three';
import { state } from './state.js';
import { machine } from './machine.js';

let hovIdx = -1;

export function onMouse(e) {
    const m2 = new THREE.Vector2((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
    const rc = new THREE.Raycaster();
    rc.setFromCamera(m2, state.camera);
    const camDist = state.camera.position.distanceTo(state.controls.target);
    rc.params.Points.threshold = Math.max(3, camDist * 0.015);

    const hits = rc.intersectObject(state.ptsMesh)
        .filter(h => state.ptsGeo.attributes.opacity.array[h.index] > 0.3);

    const tt = document.getElementById('tooltip');
    const mode = machine.get().mode;

    if (hits.length) {
        hovIdx = hits[0].index;
        const p = state.allPapers[hovIdx];
        // Light hover: dot · title · year. Full detail lives in the dock.
        document.getElementById('tt-dot').style.background = p._cl.color;
        document.getElementById('tt-title').textContent = p.title;
        document.getElementById('tt-year').textContent = p.year || '';
        if (mode !== 'intel') {
            tt.style.display = 'flex';
            const ttW = Math.min(tt.offsetWidth || 320, 380);
            tt.style.left = Math.min(e.clientX + 16, innerWidth - ttW - 16) + 'px';
            tt.style.top = Math.min(e.clientY + 18, innerHeight - 48) + 'px';
        }
        state.renderer.domElement.style.cursor = 'pointer';
    } else {
        hovIdx = -1;
        tt.style.display = 'none';
        state.renderer.domElement.style.cursor = 'default';
    }
}

export function onClk() {
    const m = machine.get();
    if (m.mode === 'intel') return; // intel is a reading mode; map clicks pass over

    if (hovIdx < 0) {
        // Empty space: one step out, like Esc.
        if (m.mode === 'paper') machine.back();
        return;
    }
    document.getElementById('tooltip').style.display = 'none';
    state.hasInteracted = true;
    const from = (m.mode === 'cluster' || m.mode === 'chart') ? 'cluster' : 'map';
    machine.focusPaper(hovIdx, from);
}
