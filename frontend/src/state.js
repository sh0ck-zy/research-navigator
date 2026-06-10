// Shared mutable state for the Observatory frontend.
// Modules read and write these fields directly; nothing here owns behavior.

export const SPREAD = 600;

export const state = {
    mapData: null,
    allPapers: [],

    // Three.js core objects (set by initScene/makePoints/makeEdges)
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    ptsMesh: null,
    ptsGeo: null,
    edgesMesh: null,

    // Interaction state
    activeCluster: null,
    cardPaper: null,
    selectedIdx: -1,
    hasInteracted: false,
    clusterZoomDist: 0,

    // Gravitational push animation (selected paper's neighbors)
    pushedPapers: [],
    pushProgress: 0,
    pushDirection: 0,

    // King papers (enlarged + labeled inside a cluster)
    kingPapers: [],
    kingLabelEls: [],

    // Lens: per-paper base point size driven by the active metric.
    // Highlights importance WITHOUT hiding anything — all papers stay visible.
    lens: 'off',
    baseSizes: null,
};
