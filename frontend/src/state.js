// Shared DATA for the NAV galaxy frontend.
// This module holds data and Three.js object handles only — no behavior.
// All experience state (mode, active cluster, selected paper) lives in
// machine.js. Modules read state freely; they never decide WHAT the
// experience is doing — that is the machine's job.

export const SPREAD = 600;

export const state = {
    mapData: null,
    allPapers: [],

    // Three.js core objects (set by scene.js)
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    ptsMesh: null,
    ptsGeo: null,
    edgesMesh: null,
    nebulae: {},        // clusterId -> THREE.Sprite (LOD glow, always present)

    // Interaction helpers (render-level, not experience-level)
    hasInteracted: false,
    clusterZoomDist: 0, // camera distance at which the active cluster was framed

    // Gravitational push animation (selected paper's neighbors)
    pushedPapers: [],
    pushProgress: 0,
    pushDirection: 0,

    // King papers (enlarged + labeled inside a cluster)
    kingPapers: [],
    kingLabelEls: [],

    // Bridge labels: neighbour-area names on inter-cluster links
    bridgeLabels: [],

    // Lens: per-paper base point size driven by the active metric
    lens: 'off',
    baseSizes: null,

    // Library: set of saved paper ids; gold ring markers on the map
    savedIds: new Set(),
    savedRings: null,

    // Claimed territories: clusterId -> project (from the API)
    claimedProjects: {},
};
