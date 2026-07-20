// camera.js — the single camera director. NO other module tweens the camera
// or controls.target. Hard rule: the camera never cuts — every transition is
// a flight. One flight at a time; starting a new flight kills the old one.

import { gsap } from 'gsap';
import { state, SPREAD } from './state.js';

let flight = null; // active gsap timeline/tween

function killFlight() {
    if (flight) { flight.kill(); flight = null; }
    gsap.killTweensOf(state.camera.position);
    gsap.killTweensOf(state.controls.target);
}

export function clusterWorldPos(cl) {
    const idx = state.mapData.clusters.indexOf(cl);
    return {
        x: (cl.center_x - 0.5) * SPREAD,
        y: (cl.center_y - 0.5) * SPREAD,
        z: (Math.sin(idx * 1.3) * 40) + (Math.cos(idx * 0.7) * 30),
    };
}

function clusterRadius(cl) {
    const { x, y } = clusterWorldPos(cl);
    const dists = cl.papers.map(p => {
        const px = (p.x - 0.5) * SPREAD, py = (p.y - 0.5) * SPREAD;
        return Math.hypot(px - x, py - y);
    }).sort((a, b) => a - b);
    return dists[Math.floor(dists.length * 0.80)] || 50;
}

// Generic flight. Returns the timeline so callers can chain onComplete.
function flyTo(pos, target, { duration = 1.7, ease = 'expo.out', onComplete } = {}) {
    killFlight();
    flight = gsap.timeline({ onComplete });
    flight.to(state.camera.position, { x: pos.x, y: pos.y, z: pos.z, duration, ease }, 0);
    flight.to(state.controls.target, { x: target.x, y: target.y, z: target.z, duration, ease }, 0);
    return flight;
}

// When the dock is open, the visual center of the free map area shifts left.
// Aim the camera slightly right of the subject so the subject lands there.
function dockShift(camDist) {
    const dockW = document.body.classList.contains('dock-wide') ? 620 : 372;
    if (!document.body.classList.contains('dock-open')) return 0;
    const fovRad = (state.camera.fov / 2) * Math.PI / 180;
    const halfW = Math.tan(fovRad) * camDist * state.camera.aspect;
    return halfW * (dockW / innerWidth);
}

// --- Shots ---------------------------------------------------------------

// Universe: the establishing shot.
export function establish(onComplete) {
    return flyTo({ x: 0, y: 80, z: 500 }, { x: 0, y: -20, z: 0 }, { duration: 1.9, onComplete });
}

// Cluster: frame the whole territory, slightly above its plane.
export function approachCluster(cl, onComplete) {
    const c = clusterWorldPos(cl);
    const radius = clusterRadius(cl);
    const fovRad = (state.camera.fov / 2) * Math.PI / 180;
    const camDist = Math.max(120, (radius / Math.tan(fovRad)) * 1.8);
    const sh = dockShift(camDist);
    return flyTo(
        { x: c.x + sh, y: c.y + camDist * 0.3, z: c.z + camDist },
        { x: c.x + sh, y: c.y, z: c.z },
        {
            duration: 1.8,
            onComplete: () => { state.clusterZoomDist = camDist; if (onComplete) onComplete(); },
        }
    );
}

// Paper: frame the paper and its immediate neighborhood.
export function focusPaper(p, onComplete) {
    const nbs = state.allPapers
        .map(q => ({ q, d: Math.hypot(q._x - p._x, q._y - p._y, q._z - p._z) }))
        .filter(o => o.q !== p)
        .sort((a, b) => a.d - b.d)
        .slice(0, 6);

    let sx = p._x, sy = p._y, sz = p._z;
    nbs.forEach(({ q }) => { sx += q._x; sy += q._y; sz += q._z; });
    const n = nbs.length + 1;
    const cx = sx / n, cy = sy / n, cz = sz / n;

    let maxR = 0;
    [p, ...nbs.map(o => o.q)].forEach(q => {
        maxR = Math.max(maxR, Math.hypot(q._x - cx, q._y - cy, q._z - cz));
    });
    const fovRad = (state.camera.fov / 2) * Math.PI / 180;
    const camDist = Math.max(80, (maxR / Math.tan(fovRad)) * 1.8);
    const sh = dockShift(camDist);

    return flyTo(
        { x: cx + sh, y: cy + camDist * 0.25, z: cz + camDist },
        { x: cx + sh, y: cy, z: cz },
        { duration: 1.7, onComplete }
    );
}

// Paper Zero / search: the user must SEE the journey — pull back, travel
// across the map, descend. Never teleport.
export function jumpToPaper(p, onComplete) {
    killFlight();
    const cam = state.camera.position;
    const tgt = { x: p._x, y: p._y, z: p._z };

    // Stage 1: pull back toward a midpoint high above the map
    const mid = {
        x: (cam.x + tgt.x) / 2,
        y: Math.max(cam.y, 160) + 60,
        z: Math.max(cam.z, 260) + 60,
    };

    flight = gsap.timeline({ onComplete });
    flight.to(state.camera.position, { x: mid.x, y: mid.y, z: mid.z, duration: 0.9, ease: 'power2.in' }, 0);
    flight.to(state.controls.target, { x: mid.x, y: 0, z: 0, duration: 0.9, ease: 'power2.in' }, 0);
    // Stage 2: travel to above the destination
    flight.to(state.camera.position, { x: tgt.x, y: tgt.y + 120, z: tgt.z + 160, duration: 1.0, ease: 'power1.inOut' });
    flight.to(state.controls.target, { x: tgt.x, y: tgt.y, z: tgt.z, duration: 1.0, ease: 'power1.inOut' }, '<');
    // Stage 3: descend into the neighborhood
    flight.add(() => {
        killFlightSoft();
        focusPaper(p, onComplete);
    });
    return flight;
}

function killFlightSoft() {
    gsap.killTweensOf(state.camera.position);
    gsap.killTweensOf(state.controls.target);
}

export function stopAutorotate() { state.controls.autoRotate = false; }
export function startAutorotate() { state.controls.autoRotate = true; }

export function distanceToTarget() {
    return state.camera.position.distanceTo(state.controls.target);
}
