// loop.js — the render loop. Per-frame it: updates controls, lerps LOD
// values toward the machine's targets, positions DOM labels anchored to 3D
// points, runs the push animation, renders. It contains NO experience
// decisions except the zoom-out auto-exit (a navigation gesture).

import * as THREE from 'three';
import { state } from './state.js';
import { machine } from './machine.js';
import { lodTargets, lodLive } from './scene.js';
import { updateLabels } from './labels.js';
import { updateChartRing } from './chart.js';
import { distanceToTarget } from './camera.js';

const LERP = 0.09;

export function loop() {
    requestAnimationFrame(loop);
    state.controls.update();

    // --- LOD lerp ---
    const mat = state.ptsMesh && state.ptsMesh.material;
    if (mat) {
        lodLive.starAlpha += (lodTargets.starAlpha - lodLive.starAlpha) * LERP;
        lodLive.starSize += (lodTargets.starSize - lodLive.starSize) * LERP;
        mat.uniforms.uAlphaScale.value = lodLive.starAlpha;
        mat.uniforms.uSizeScale.value = lodLive.starSize;
    }
    lodLive.nebula += (lodTargets.nebula - lodLive.nebula) * LERP;
    const { clusterId } = machine.get();
    Object.entries(state.nebulae).forEach(([cid, sprite]) => {
        const isActive = parseInt(cid) === clusterId;
        const target = lodLive.nebula * (isActive ? 1.5 : 1.0);
        sprite.material.opacity += (target - sprite.material.opacity) * LERP;
    });
    if (state.edgesMesh) {
        lodLive.edges += (lodTargets.edges - lodLive.edges) * LERP;
        state.edgesMesh.material.opacity = lodLive.edges;
    }

    updateLabels();
    updateHero();

    // Auto-exit: zooming far out of a territory pops back to the universe.
    const m = machine.get();
    const dist = distanceToTarget();
    if ((m.mode === 'cluster' || m.mode === 'chart') && state.clusterZoomDist > 0) {
        if (dist > state.clusterZoomDist * 2.2) machine.back();
    }

    updateChartRing(THREE);

    // King paper labels
    state.kingLabelEls.forEach(({ el, index }) => {
        const p = state.allPapers[index];
        const v = new THREE.Vector3(p._x, p._y, p._z).project(state.camera);
        el.style.left = (v.x * 0.5 + 0.5) * innerWidth + 'px';
        el.style.top = ((-v.y * 0.5 + 0.5) * innerHeight - 18) + 'px';
        el.style.display = v.z < 1 ? '' : 'none';
    });

    // Bridge labels
    state.bridgeLabels.forEach(({ el, pos }) => {
        const v = pos.clone().project(state.camera);
        el.style.left = (v.x * 0.5 + 0.5) * innerWidth + 'px';
        el.style.top = (-v.y * 0.5 + 0.5) * innerHeight + 'px';
        el.style.display = v.z < 1 ? '' : 'none';
    });

    // Gravitational push animation
    if (state.pushedPapers.length > 0) {
        state.pushProgress += (state.pushDirection > 0 ? 0.06 : -0.08);
        state.pushProgress = Math.max(0, Math.min(1, state.pushProgress));
        const posArr = state.ptsGeo.attributes.position.array;
        const et = state.pushDirection > 0 ? (1 - Math.pow(1 - state.pushProgress, 3)) : state.pushProgress;
        state.pushedPapers.forEach(pp => {
            posArr[pp.index * 3] = pp.origX + (pp.targetX - pp.origX) * et;
            posArr[pp.index * 3 + 1] = pp.origY + (pp.targetY - pp.origY) * et;
            posArr[pp.index * 3 + 2] = pp.origZ + (pp.targetZ - pp.origZ) * et;
        });
        state.ptsGeo.attributes.position.needsUpdate = true;
        if (state.pushProgress <= 0 && state.pushDirection < 0) {
            state.pushedPapers.forEach(pp => {
                posArr[pp.index * 3] = pp.origX; posArr[pp.index * 3 + 1] = pp.origY; posArr[pp.index * 3 + 2] = pp.origZ;
            });
            state.ptsGeo.attributes.position.needsUpdate = true;
            state.pushedPapers = [];
            state.pushDirection = 0;
        }
    }

    state.renderer.render(state.scene, state.camera);
}

// Hero: only in universe mode, at the establishing distance, before the
// user has grabbed the map. Outside universe mode it vanishes immediately.
function updateHero() {
    const heroEl = document.getElementById('hero');
    const m = machine.get();
    if (m.mode !== 'universe') {
        if (heroEl.style.visibility !== 'hidden') {
            heroEl.style.opacity = '0';
            heroEl.style.visibility = 'hidden';
            heroEl.style.pointerEvents = 'none';
        }
        return;
    }
    const show = !state.hasInteracted && distanceToTarget() >= 440;
    const cur = parseFloat(heroEl.style.opacity) || 0;
    const next = cur + ((show ? 1 : 0) - cur) * 0.12;
    heroEl.style.opacity = next < 0.01 ? 0 : next;
    heroEl.style.pointerEvents = (next > 0.5 && show) ? '' : 'none';
    heroEl.style.visibility = next < 0.01 ? 'hidden' : '';
}
