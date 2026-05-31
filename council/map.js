// branchscape/council/map.js  (browser-only)
// Mirrors the proven deck.gl init from index.html: online = maplibre base map
// + interleaved MapboxOverlay; offline = standalone DeckGL canvas, no basemap.
const CENTER = { longitude: -112.07, latitude: 33.45, zoom: 9.2, pitch: 55, bearing: -17 };
const OFFLINE = new URLSearchParams(location.search).has('offline');

const CouncilMap = (function () {
  const { DeckGL, MapboxOverlay, ColumnLayer, ScatterplotLayer } = deck;
  let deckOverlay, map;
  const BR = window.BRANCH_DATA.branches;
  const depOf = b => (b.dep && (b.dep['2024'] || 0)) || 0;
  const overlays = { gap: false, saturation: false, community: false };
  let candidatePins = [];
  let zones = [];

  function towerLayer() {
    return new ColumnLayer({
      id: 'towers', data: BR, diskResolution: 6, radius: 90, extruded: true,
      getPosition: b => [b.lon, b.lat],
      getElevation: b => Math.min(depOf(b), 4000000) / 1500,
      getFillColor: () => [127, 211, 255, 180],
      elevationScale: 1, pickable: false,
    });
  }
  function heatLayer(id, signal, rgb) {
    if (!overlays[id]) return null;
    return new ScatterplotLayer({
      id, data: zones, radiusUnits: 'meters', getRadius: 700,
      getPosition: z => [z.lon, z.lat],
      getFillColor: z => [rgb[0], rgb[1], rgb[2], Math.round(40 + 170 * (z.norm ? z.norm[signal] : 0))],
    });
  }
  function pinLayer() {
    return new ScatterplotLayer({
      id: 'pins', data: candidatePins, radiusUnits: 'pixels', getRadius: 14,
      getPosition: z => [z.lon, z.lat],
      getFillColor: [255, 216, 107, 230], stroked: true,
      getLineColor: [255, 216, 107], lineWidthUnits: 'pixels', getLineWidth: 2,
    });
  }
  function layers() {
    return [
      towerLayer(),
      heatLayer('gap', 'depositGap', [127, 211, 255]),
      heatLayer('saturation', 'saturation', [255, 184, 107]),
      heatLayer('community', 'communityNeed', [106, 214, 176]),
      pinLayer(),
    ].filter(Boolean);
  }
  function render() {
    const ls = layers();
    if (map) {
      if (!deckOverlay) { deckOverlay = new MapboxOverlay({ interleaved: true, layers: ls }); map.addControl(deckOverlay); }
      else deckOverlay.setProps({ layers: ls });
    } else if (deckOverlay) {
      deckOverlay.setProps({ layers: ls });
    }
  }
  function initMap() {
    if (!OFFLINE) {
      map = new maplibregl.Map({
        container: 'map',
        style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        center: [CENTER.longitude, CENTER.latitude],
        zoom: CENTER.zoom, pitch: CENTER.pitch, bearing: CENTER.bearing,
        attributionControl: false, interactive: true,
      });
      map.on('load', render);
    } else {
      deckOverlay = new DeckGL({ container: 'map', initialViewState: CENTER, controller: true, layers: layers() });
    }
  }
  function setZones(z) { zones = z; render(); }
  function dropPins(z) { candidatePins = z; render(); }
  function setOverlay(name, on) { overlays[name] = on; render(); }
  // Returns [x, y] pixel coords for a lon/lat, in whichever renderer is active.
  function projectToScreen(lon, lat) {
    if (map) { const p = map.project([lon, lat]); return [p.x, p.y]; }
    const vp = deckOverlay && deckOverlay.getViewports && deckOverlay.getViewports()[0];
    return vp ? vp.project([lon, lat]) : [0, 0];
  }
  return { initMap, setZones, dropPins, setOverlay, projectToScreen, CENTER };
})();
