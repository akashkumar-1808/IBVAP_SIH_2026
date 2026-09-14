/**
 * IBVAP TATVA — Static GIS Geographic Vector Dataset
 * 
 * ZERO runtime satellite / external tile API dependencies.
 * All geometry is compiled client-side as lightweight SVG vector paths.
 * 
 * Spatial projection:
 * Longitude: 68.0°E (X: 80) to 97.5°E (X: 920)
 * Latitude: 37.5°N (Y: 50) to 8.0°N (Y: 930)
 */

export interface SectorMarker {
  id: string;
  name: string;
  region: string;
  lat: number;
  lng: number;
  x: number;
  y: number;
  isActivePrototype: boolean;
  status: 'ACTIVE_PROTOTYPE' | 'CONTEXT_ONLY';
  sensorsCount: number;
  description: string;
}

// Coordinate projection helper
export function projectGeoToSvg(lng: number, lat: number, width = 1000, height = 1000): [number, number] {
  const minLng = 67.0;
  const maxLng = 98.0;
  const minLat = 6.5;
  const maxLat = 37.5;

  const x = ((lng - minLng) / (maxLng - minLng)) * (width * 0.86) + (width * 0.07);
  // Invert Y axis because SVG coordinates grow downwards
  const y = ((maxLat - lat) / (maxLat - minLat)) * (height * 0.88) + (height * 0.05);
  return [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
}

export function unprojectSvgToGeo(x: number, y: number, width = 1000, height = 1000): [number, number] {
  const minLng = 67.0;
  const maxLng = 98.0;
  const minLat = 6.5;
  const maxLat = 37.5;

  const lng = ((x - width * 0.07) / (width * 0.86)) * (maxLng - minLng) + minLng;
  const lat = maxLat - ((y - height * 0.05) / (height * 0.88)) * (maxLat - minLat);
  return [Math.round(lng * 100) / 100, Math.round(lat * 100) / 100];
}

/**
 * High-fidelity, smooth polygonal outline path for India mainland & major islands.
 * Normalized to 1000x1000 viewBox.
 */
export const INDIA_OUTLINE_PATH = `
  M 270 70 
  C 285 55, 310 50, 335 55
  C 355 60, 375 75, 385 95
  C 400 110, 420 125, 415 145
  C 410 160, 395 175, 385 190
  C 375 205, 370 220, 380 235
  C 395 245, 420 250, 445 250
  C 470 250, 495 260, 520 270
  C 545 280, 570 285, 595 280
  C 615 275, 630 265, 645 250
  C 655 240, 675 235, 690 240
  C 710 245, 730 230, 755 210
  C 775 195, 800 190, 830 195
  C 860 200, 890 215, 915 235
  C 925 250, 910 270, 890 290
  C 870 310, 865 330, 875 350
  C 885 370, 870 395, 845 410
  C 825 420, 805 435, 800 455
  C 790 475, 775 485, 755 490
  C 735 495, 720 480, 705 465
  C 690 450, 675 445, 655 450
  C 640 455, 625 470, 615 490
  C 605 510, 590 525, 570 540
  C 555 555, 550 575, 555 595
  C 560 615, 550 640, 535 665
  C 520 690, 505 715, 490 740
  C 475 765, 460 790, 445 815
  C 430 840, 420 865, 410 890
  C 405 905, 395 915, 385 910
  C 375 900, 365 875, 355 850
  C 345 825, 335 800, 325 770
  C 315 740, 305 710, 290 680
  C 275 650, 260 625, 245 600
  C 230 575, 215 550, 205 525
  C 195 500, 185 475, 175 455
  C 165 440, 150 435, 135 440
  C 115 445, 95 460, 80 475
  C 75 485, 70 470, 80 450
  C 95 425, 115 405, 130 380
  C 145 355, 160 330, 175 305
  C 190 280, 205 255, 215 230
  C 225 205, 235 180, 245 155
  C 255 130, 260 100, 270 70
  Z
`.trim();

/**
 * Critical frontier border segments.
 */
export const FRONTIER_BORDER_PATHS = [
  // Northern Frontier (J&K, Ladakh, Sector B-07 region)
  {
    id: 'north_border',
    name: 'Northern Frontier (J&K / Ladakh)',
    path: 'M 270 70 C 290 60, 320 50, 350 60 C 375 70, 395 90, 415 120 C 420 140, 410 160, 385 190',
    type: 'RESTRICTED_BORDER',
    color: '#EF4444',
  },
  // Western Frontier (Punjab, Rajasthan, Gujarat / Sir Creek)
  {
    id: 'west_border',
    name: 'Western Frontier (Punjab / Rajasthan / Rann of Kutch)',
    path: 'M 245 155 C 235 180, 225 210, 215 240 C 200 270, 185 310, 170 350 C 150 390, 120 420, 80 450',
    type: 'INTERNATIONAL_BORDER',
    color: '#F59E0B',
  },
  // Eastern & Northeastern Frontier (Sikkim, Arunachal, Assam, Tripura)
  {
    id: 'east_border',
    name: 'Eastern & Northeastern Frontier',
    path: 'M 645 250 C 665 240, 690 240, 720 235 C 755 210, 800 195, 850 200 C 890 215, 915 240, 910 270 C 875 330, 870 380, 845 410',
    type: 'HIGH_ALTITUDE_BORDER',
    color: '#3B82F6',
  },
];

/**
 * Realistic neighbor country context silhouettes (dark/neutral, no active data).
 */
export const NEIGHBOR_CONTEXT = [
  { name: 'PAKISTAN', x: 120, y: 220 },
  { name: 'CHINA / TIBET', x: 540, y: 150 },
  { name: 'NEPAL', x: 530, y: 285 },
  { name: 'BHUTAN', x: 720, y: 260 },
  { name: 'BANGLADESH', x: 710, y: 440 },
  { name: 'MYANMAR', x: 920, y: 460 },
  { name: 'ARABIAN SEA', x: 160, y: 690 },
  { name: 'BAY OF BENGAL', x: 670, y: 690 },
  { name: 'INDIAN OCEAN', x: 380, y: 960 },
];

/**
 * Sector references across the national boundary.
 * Strictly distinguishes ACTIVE PROTOTYPE SECTOR from CONTEXT ONLY sectors.
 */
export const NATIONAL_SECTOR_REGISTRY: SectorMarker[] = [
  {
    id: 'SECTOR-B07',
    name: 'Sector B-07 (Northern Command)',
    region: 'Northern Frontier / J&K',
    lat: 34.25,
    lng: 74.82,
    x: 295,
    y: 125,
    isActivePrototype: true,
    status: 'ACTIVE_PROTOTYPE',
    sensorsCount: 1, // Real connected demo camera
    description: 'Active prototype operational sector. Real-time YOLO, ByteTrack, Spatial, Behavior & Fusion pipeline running.',
  },
  {
    id: 'SECTOR-W01',
    name: 'Sector W-01 (Punjab Plains)',
    region: 'Western Frontier / Punjab',
    lat: 31.63,
    lng: 74.62,
    x: 288,
    y: 200,
    isActivePrototype: false,
    status: 'CONTEXT_ONLY',
    sensorsCount: 0,
    description: 'National border context only. No live sensors connected to prototype.',
  },
  {
    id: 'SECTOR-W02',
    name: 'Sector W-02 (Thar Desert)',
    region: 'Western Frontier / Rajasthan',
    lat: 26.91,
    lng: 70.92,
    x: 185,
    y: 330,
    isActivePrototype: false,
    status: 'CONTEXT_ONLY',
    sensorsCount: 0,
    description: 'National border context only. No live sensors connected to prototype.',
  },
  {
    id: 'SECTOR-W03',
    name: 'Sector W-03 (Sir Creek / Kutch)',
    region: 'Western Frontier / Gujarat',
    lat: 23.75,
    lng: 68.80,
    x: 125,
    y: 430,
    isActivePrototype: false,
    status: 'CONTEXT_ONLY',
    sensorsCount: 0,
    description: 'National border context only. No live sensors connected to prototype.',
  },
  {
    id: 'SECTOR-E01',
    name: 'Sector E-01 (Brahmaputra Basin)',
    region: 'Eastern Frontier / Assam',
    lat: 26.15,
    lng: 91.75,
    x: 775,
    y: 360,
    isActivePrototype: false,
    status: 'CONTEXT_ONLY',
    sensorsCount: 0,
    description: 'National border context only. No live sensors connected to prototype.',
  },
  {
    id: 'SECTOR-E02',
    name: 'Sector E-02 (Himalayan Ridge)',
    region: 'Eastern Frontier / Arunachal',
    lat: 28.20,
    lng: 95.80,
    x: 880,
    y: 290,
    isActivePrototype: false,
    status: 'CONTEXT_ONLY',
    sensorsCount: 0,
    description: 'National border context only. No live sensors connected to prototype.',
  },
];
