// Reads REACT_APP_MAP_* once. Warns and falls back when unset/invalid.

const FALLBACK_FILE_PATH = '/carla_map/Town01/lanelet2_map.osm';

const num = (raw) => {
    const n = Number(raw);
    return Number.isFinite(n) ? n : 0;
};

const warnMissing = (name) => console.warn(
    `[mapConfig] ${name} unset — did you source env.sh / run prepare_env.sh?`
);

if (!process.env.REACT_APP_MAP_FILE_PATH) warnMissing('REACT_APP_MAP_FILE_PATH');
if (!process.env.REACT_APP_MAP_ORIGIN_LAT) warnMissing('REACT_APP_MAP_ORIGIN_LAT');
if (!process.env.REACT_APP_MAP_ORIGIN_LON) warnMissing('REACT_APP_MAP_ORIGIN_LON');

export const MAP_FILE_PATH = process.env.REACT_APP_MAP_FILE_PATH || FALLBACK_FILE_PATH;
export const MAP_ORIGIN_LAT = num(process.env.REACT_APP_MAP_ORIGIN_LAT);
export const MAP_ORIGIN_LON = num(process.env.REACT_APP_MAP_ORIGIN_LON);
export const MAP_CENTER = [MAP_ORIGIN_LAT, MAP_ORIGIN_LON];
