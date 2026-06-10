import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { gsap } from 'gsap';
import { state, SPREAD } from './state.js';

export function initScene() {
    state.scene = new THREE.Scene();
    state.scene.fog = new THREE.FogExp2(0x0a0a0a, 0.0004);
    state.camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, 0.1, 3000);
    state.camera.position.set(0, 80, 500);
    state.renderer = new THREE.WebGLRenderer({ antialias:true });
    state.renderer.setSize(innerWidth, innerHeight);
    state.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    state.renderer.setClearColor(0x0a0a0a);
    document.getElementById('canvas-container').appendChild(state.renderer.domElement);
    state.controls = new OrbitControls(state.camera, state.renderer.domElement);
    state.controls.enableDamping = true;
    state.controls.dampingFactor = 0.04;
    state.controls.autoRotate = true;
    state.controls.autoRotateSpeed = 0.06; // calmer ambient drift, less disorienting
    state.controls.maxPolarAngle = Math.PI*0.6;
    state.controls.minPolarAngle = Math.PI*0.4;
    state.controls.minDistance = 28; // get close enough to reach small clusters
    state.controls.maxDistance = 600;
    state.controls.zoomSpeed = 0.6;
    state.controls.target.set(0, 0, 0);
}

export function makePoints() {
    const allPapers = state.allPapers;
    const n = allPapers.length;
    const pos=new Float32Array(n*3), col=new Float32Array(n*3), siz=new Float32Array(n), opa=new Float32Array(n);
    const c = new THREE.Color();

    allPapers.forEach((p,i) => {
        pos[i*3]=p._x; pos[i*3+1]=p._y; pos[i*3+2]=p._z;
        c.set(p._cl.color);
        col[i*3]=c.r; col[i*3+1]=c.g; col[i*3+2]=c.b;
        // Base size comes from the active lens (state.baseSizes, computed in boot)
        siz[i] = state.baseSizes ? state.baseSizes[i] : (1.5 + p._centrality * 5.0);
        opa[i] = 1.0;
    });

    state.ptsGeo = new THREE.BufferGeometry();
    state.ptsGeo.setAttribute('position', new THREE.BufferAttribute(pos,3));
    state.ptsGeo.setAttribute('color', new THREE.BufferAttribute(col,3));
    state.ptsGeo.setAttribute('size', new THREE.BufferAttribute(siz,1));
    state.ptsGeo.setAttribute('opacity', new THREE.BufferAttribute(opa,1));

    const mat = new THREE.ShaderMaterial({
        vertexShader:`
            attribute float size;
            attribute vec3 color;
            attribute float opacity;
            varying vec3 vC;
            varying float vO;
            void main(){
                vC=color; vO=opacity;
                vec4 mv=modelViewMatrix*vec4(position,1.0);
                // Floor at 2px so no paper ever shrinks into nothing when zoomed out
                gl_PointSize=max(size*(350.0/-mv.z), 2.0);
                gl_Position=projectionMatrix*mv;
            }`,
        fragmentShader:`
            varying vec3 vC;
            varying float vO;
            void main(){
                float d=length(gl_PointCoord-vec2(0.5));
                if(d>0.5)discard;
                float core=smoothstep(0.5,0.1,d);
                float glow=smoothstep(0.5,0.0,d)*0.2;
                float alpha=(core*0.9+glow)*vO;
                gl_FragColor=vec4(vC*(0.8+core*0.8), alpha);
            }`,
        transparent:true, depthWrite:false, blending:THREE.AdditiveBlending
    });

    state.ptsMesh = new THREE.Points(state.ptsGeo, mat);
    state.scene.add(state.ptsMesh);

    // === CLUSTER BUBBLES (shown on hover) ===
    makeBubbles();
}

const clusterBubbles = {}; // id -> THREE.Sprite

function makeBubbles() {
    // Create soft radial gradient texture for bubbles
    const bubbleCanvas = document.createElement('canvas');
    bubbleCanvas.width = 128;
    bubbleCanvas.height = 128;
    const bctx = bubbleCanvas.getContext('2d');
    const grad = bctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255,255,255,0.12)');
    grad.addColorStop(0.5, 'rgba(255,255,255,0.06)');
    grad.addColorStop(0.8, 'rgba(255,255,255,0.03)');
    grad.addColorStop(1, 'rgba(255,255,255,0.0)');
    bctx.fillStyle = grad;
    bctx.fillRect(0, 0, 128, 128);
    const bubbleTex = new THREE.CanvasTexture(bubbleCanvas);

    state.mapData.clusters.forEach(cl => {
        if (cl.id === -1) return;

        const zIdx = state.mapData.clusters.indexOf(cl);
        const cz = (Math.sin(zIdx * 1.3) * 40) + (Math.cos(zIdx * 0.7) * 30);
        const cx = (cl.center_x - 0.5) * SPREAD;
        const cy = (cl.center_y - 0.5) * SPREAD;

        // Compute radius from p80 of points
        const dists = cl.papers.map(p => {
            const px = (p.x - 0.5) * SPREAD, py = (p.y - 0.5) * SPREAD;
            return Math.sqrt((px-cx)**2 + (py-cy)**2);
        }).sort((a, b) => a - b);
        const radius = dists[Math.floor(dists.length * 0.80)] || 50;
        const size = radius * 2.8;

        const spriteMat = new THREE.SpriteMaterial({
            map: bubbleTex,
            color: new THREE.Color(cl.color),
            transparent: true,
            opacity: 0.0,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.set(cx, cy, cz - 2);
        sprite.scale.set(size, size, 1);
        state.scene.add(sprite);
        clusterBubbles[cl.id] = sprite;
    });
}

export function showBubble(cid) {
    Object.entries(clusterBubbles).forEach(([id, sprite]) => {
        const show = parseInt(id) === cid;
        gsap.killTweensOf(sprite.material);
        gsap.to(sprite.material, { opacity: show ? 0.8 : 0.0, duration: 0.35, ease: 'power2.out' });
    });
}

export function hideBubbles() {
    Object.values(clusterBubbles).forEach(sprite => {
        gsap.killTweensOf(sprite.material);
        gsap.to(sprite.material, { opacity: 0.0, duration: 0.35, ease: 'power2.out' });
    });
}

// === PROGRESSIVE EDGES (appear on zoom) ===
export function makeEdges() {
    const pos = [], cols = [];
    const K = 3; // edges per paper to K nearest neighbors in same cluster

    // Group papers by cluster for efficiency
    const byCluster = {};
    state.allPapers.forEach((p, i) => {
        if (!byCluster[p._cl.id]) byCluster[p._cl.id] = [];
        byCluster[p._cl.id].push({ p, i });
    });

    Object.values(byCluster).forEach(papers => {
        papers.forEach(({ p: paper, i: idx }) => {
            // Find K nearest in same cluster
            const dists = papers
                .filter(o => o.i !== idx)
                .map(o => ({ o, d: (o.p._x-paper._x)**2 + (o.p._y-paper._y)**2 + (o.p._z-paper._z)**2 }))
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
        vertexColors: true,
        transparent: true,
        opacity: 0.0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
    }));
    state.scene.add(state.edgesMesh);
}

export function fly(x,y,z){
    gsap.to(state.camera.position,{x,y,z,duration:1.8,ease:'expo.out'});
    gsap.to(state.controls.target,{x:z>350?0:x, y:z>350?0:y-20, z:0, duration:1.8,ease:'expo.out'});
}

export function onRsz(){
    state.camera.aspect=innerWidth/innerHeight;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(innerWidth,innerHeight);
}
