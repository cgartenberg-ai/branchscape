// branchscape/council/map.js  (browser-only)
// Uses the proven index.html renderer: a maplibre-gl map with an interleaved
// deck.gl MapboxOverlay. Online = CARTO dark basemap; offline (?offline) = an
// inline no-network "void" style (zero tile requests). The vendored deck.gl
// bundle ships MapboxOverlay + layers but NOT a standalone DeckGL/Deck class,
// so everything renders through the maplibre overlay in both modes. If the
// online basemap fails to load (venue wifi), we auto-fall back to the void.
const CENTER = { longitude: -112.07, latitude: 33.45, zoom: 9.2, pitch: 55, bearing: -17 };
const OFFLINE = new URLSearchParams(location.search).has('offline');
const VOID_STYLE = {
  version: 8, sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#02040a' } }],
};
const ONLINE_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const CouncilMap = (function () {
  let map, deckOverlay, ready = false;
  const BR = window.BRANCH_DATA.branches;
  const depOf = b => (b.dep && (b.dep['2024'] || 0)) || 0;
  const overlays = { gap: false, saturation: false, community: false };
  let candidatePins = [];
  let zones = [];

  // deposit topography: cool blue (low) → warm gold (high), bright enough to read
  function towerColor(b) {
    const t = Math.min(1, depOf(b) / 2000000); // 0..1 up to ~$2B
    return [Math.round(127 + 128 * t), Math.round(211 - 40 * t), Math.round(255 - 160 * t), 215];
  }
  function towerLayer() {
    return new deck.ColumnLayer({
      id: 'towers', data: BR, diskResolution: 6, radius: 110, extruded: true,
      getPosition: b => [b.lon, b.lat],
      getElevation: b => Math.min(depOf(b), 4000000) / 1200,
      getFillColor: towerColor,
      elevationScale: 1, pickable: false, material: false,
    });
  }
  function heatLayer(id, signal, rgb) {
    if (!overlays[id]) return null;
    return new deck.ScatterplotLayer({
      id, data: zones, radiusUnits: 'meters', getRadius: 700,
      getPosition: z => [z.lon, z.lat],
      getFillColor: z => [rgb[0], rgb[1], rgb[2], Math.round(40 + 170 * (z.norm ? z.norm[signal] : 0))],
    });
  }
  function pinLayer() {
    return new deck.ScatterplotLayer({
      id: 'pins', data: candidatePins, radiusUnits: 'pixels', getRadius: 15,
      getPosition: z => [z.lon, z.lat],
      getFillColor: [255, 216, 107, 235], stroked: true,
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
    if (!ready) return;
    if (!deckOverlay) { deckOverlay = new deck.MapboxOverlay({ interleaved: true, layers: layers() }); map.addControl(deckOverlay); }
    else deckOverlay.setProps({ layers: layers() });
  }
  function markReady() { if (!ready) { ready = true; } render(); }
  function initMap() {
    map = new maplibregl.Map({
      container: 'map',
      style: OFFLINE ? VOID_STYLE : ONLINE_STYLE,
      center: [CENTER.longitude, CENTER.latitude],
      zoom: CENTER.zoom, pitch: CENTER.pitch, bearing: CENTER.bearing,
      attributionControl: false,
    });
    map.on('load', markReady);
    map.on('error', () => { /* tile/style errors → handled by the fallback below */ });
    // Venue-wifi safety: if the online basemap hasn't loaded in 5s, swap to the
    // void (which loads instantly, with no network) and render onto it.
    if (!OFFLINE) setTimeout(() => {
      if (!ready) { try { map.setStyle(VOID_STYLE); map.once('styledata', markReady); } catch (_) { markReady(); } }
    }, 5000);
  }
  function setZones(z) { zones = z; render(); }
  function dropPins(z) { candidatePins = z; render(); }
  function setOverlay(name, on) { overlays[name] = on; render(); }
  function projectToScreen(lon, lat) {
    if (!map) return [0, 0];
    const p = map.project([lon, lat]);
    return [p.x, p.y];
  }
  return { initMap, setZones, dropPins, setOverlay, projectToScreen, CENTER };
})();
