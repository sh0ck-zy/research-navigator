// scene.js — Three.js scene construction and LOD render targets.
// Owns geometry and materials only. Camera motion lives in camera.js;
// experience decisions live in machine.js + effects.js.

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { state, SPREAD } from './state.js';
import { clusterWorldPos } from './camera.js';

// LOD render targets — loop.js lerps the live values toward these.
// t0 (universe): nebulae carry the read; stars are quiet haze.
// t1 (cluster):  stars of the territory full, nebulae recede.
// t2 (paper):    focus — everything else dims hard, edges appear.
export const lodTargets = {
    starAlpha: 0.55,   // global multiplier on star opacity
    starSize: 0.85,    // global multiplier on star size
    nebula: 0.5,       // nebula glow opacity
    edges: 0.0,        // kNN edge mesh opacity
};

export const lodLive = { starAlpha: 1, starSize: 1, nebula: 0, edges: 0 };

export function initScene() {
    state.scene = new THREE.Scene();
    state.scene.fog = new THREE.FogExp2(0x060608, 0.0004);
    state.camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 3000);
    state.camera.position.set(0, 80, 500);
    state.renderer = new THREE.WebGLRenderer({ antialias: true });
    state.renderer.setSize(innerWidth, innerHeight);
    state.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    state.renderer.setClearColor(0x060608);
    document.getElementById('canvas-container').appendChild(state.renderer.domElement);
    state.controls = new OrbitControls(state.camera, state.renderer.domElement);
    state.controls.enableDamping = true;
    state.controls.dampingFactor = 0.04;
    state.controls.autoRotate = true;
    state.controls.autoRotateSpeed = 0.05; // alive but calm
    state.controls.maxPolarAngle = Math.PI * 0.6;
    state.controls.minPolarAngle = Math.PI * 0.4;
    state.controls.minDistance = 28;
    state.controls.maxDistance = 600;
    state.controls.zoomSpeed = 0.6;
    state.controls.target.set(0, -20, 0);
}

export function makePoints() {
    const allPapers = state.allPapers;
    const n = allPapers.length;
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3),
          siz = new Float32Array(n), opa = new Float32Array(n);
    const c = new THREE.Color();

    allPapers.forEach((p, i) => {
        pos[i * 3] = p._x; pos[i * 3 + 1] = p._y; pos[i * 3 + 2] = p._z;
        c.set(p._cl.color);
        col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
        siz[i] = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        opa[i] = 1.0;
    });

    state.ptsGeo = new THREE.BufferGeometry();
    state.ptsGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    state.ptsGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    state.ptsGeo.setAttribute('size', new THREE.BufferAttribute(siz, 1));
    state.ptsGeo.setAttribute('opacity', new THREE.BufferAttribute(opa, 1));

    const mat = new THREE.ShaderMaterial({
        uniforms: {
            uSizeScale: { value: 1.0 },
            uAlphaScale: { value: 1.0 },
        },
        vertexShader: `
            attribute float size;
            attribute vec3 color;
            attribute float opacity;
            uniform float uSizeScale;
            varying vec3 vC;
            varying float vO;
            void main(){
                vC = color; vO = opacity;
                vec4 mv = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = max(size * uSizeScale * (350.0 / -mv.z), 1.6);
                gl_Position = projectionMatrix * mv;
            }`,
        fragmentShader: `
            uniform float uAlphaScale;
            varying vec3 vC;
            varying float vO;
            void main(){
                float d = length(gl_PointCoord - vec2(0.5));
                if (d > 0.5) discard;
                float core = smoothstep(0.5, 0.1, d);
                float glow = smoothstep(0.5, 0.0, d) * 0.2;
                float alpha = (core * 0.9 + glow) * vO * uAlphaScale;
                gl_FragColor = vec4(vC * (0.8 + core * 0.8), alpha);
            }`,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });

    state.ptsMesh = new THREE.Points(state.ptsGeo, mat);
    state.scene.add(state.ptsMesh);

    makeNebulae();
}

// === NEBULAE — one soft glow sprite per cluster, always in the scene.
// They ARE the universe-level read: at t0 you see ~14 glowing regions,
// not 10,000 competing dots.
function makeNebulae() {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 256;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
    grad.addColorStop(0, 'rgba(255,255,255,0.26)');
    grad.addColorStop(0.4, 'rgba(255,255,255,0.11)');
    grad.addColorStop(0.75, 'rgba(255,255,255,0.03)');
    grad.addColorStop(1, 'rgba(255,255,255,0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 256);
    const tex = new THREE.CanvasTexture(canvas);

    state.mapData.clusters.forEach(cl => {
        if (cl.id === -1) return;
        const c = clusterWorldPos(cl);
        const dists = cl.papers.map(p => {
            const px = (p.x - 0.5) * SPREAD, py = (p.y - 0.5) * SPREAD;
            return Math.hypot(px - c.x, py - c.y);
        }).sort((a, b) => a - b);
        const radius = dists[Math.floor(dists.length * 0.85)] || 50;
        const size = radius * 3.0;

        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
            map: tex,
            color: new THREE.Color(cl.color),
            transparent: true,
            opacity: 0.0,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        }));
        sprite.position.set(c.x, c.y, c.z - 4);
        sprite.scale.set(size, size, 1);
        state.scene.add(sprite);
        state.nebulae[cl.id] = sprite;
    });
}

// === kNN edges — built once, only ever visible at paper focus (t2).
export function makeEdges() {
    const pos = [], cols = [];
    const K = 3;
    const byCluster = {};
    state.allPapers.forEach((p, i) => {
        (byCluster[p._cl.id] = byCluster[p._cl.id] || []).push({ p, i });
    });

    Object.values(byCluster).forEach(papers => {
        papers.forEach(({ p: paper, i: idx }) => {
            const dists = papers
                .filter(o => o.i !== idx)
                .map(o => ({ o, d: (o.p._x - paper._x) ** 2 + (o.p._y - paper._y) ** 2 + (o.p._z - paper._z) ** 2 }))
                .sort((a, b) => a.d - b.d)
                .slice(0, K);
            const c1 = new THREE.Color(paper._cl.color);
            dists.forEach(({ o }) => {
                pos.push(paper._x, paper._y, paper._z, o.p._x, o.p._y, o.p._z);
                cols.push(c1.r, c1.g, c1.b, c1.r, c1.g, c1.b);
            });
        });
    });

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    state.edgesMesh = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.0,
        blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    state.scene.add(state.edgesMesh);
}

export function onRsz() {
    state.camera.aspect = innerWidth / innerHeight;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(innerWidth, innerHeight);
}
