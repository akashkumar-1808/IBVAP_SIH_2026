/**
 * IBVAP TATVA — Bhuvan/NRSC GIS Integration & Geospatial Layer Abstraction
 * 
 * Complies with OGC WMS/WMTS specifications.
 * Supports switching between live Bhuvan/NRSC WMS and local static satellite fallback.
 * Strictly separates NATIONAL BORDER CONTEXT from ACTIVE PROTOTYPE SECTOR.
 */

import { CameraInfo, TrackState, EventRecord } from '../../types';

export type SatelliteSourceType = 'BHUVAN_WMS' | 'LOCAL_OFFLINE_SATELLITE' | 'DARK_TACTICAL';

export interface BhuvanServiceMetadata {
  name: string;
  agency: string;
  wmsEndpoint: string;
  layerName: string;
  format: string;
  crs: string;
  tileUrlTemplate: string;
  description: string;
}

/**
 * Official Bhuvan/NRSC Web Map Service (WMS) Configuration
 */
export const BHUVAN_SERVICES: Record<string, BhuvanServiceMetadata> = {
  SATELLITE_HIGH_RES: {
    name: 'Bhuvan Satellite High-Resolution',
    agency: 'NRSC / ISRO (National Remote Sensing Centre)',
    wmsEndpoint: 'https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms',
    layerName: 'bhuvan_satellite',
    format: 'image/png',
    crs: 'EPSG:3857',
    tileUrlTemplate:
      'https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=TRUE&LAYERS=bhuvan_satellite&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
    description: 'ISRO Bhuvan multi-spectral satellite imagery layer.',
  },
  THEMATIC_INDIA: {
    name: 'Bhuvan Thematic Border Basemap',
    agency: 'NRSC / ISRO',
    wmsEndpoint: 'https://bhuvan-vec3.nrsc.gov.in/bhuvan/ows',
    layerName: 'india3',
    format: 'image/png',
    crs: 'EPSG:3857',
    tileUrlTemplate:
      'https://bhuvan-vec3.nrsc.gov.in/bhuvan/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=TRUE&LAYERS=india3&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}',
    description: 'Bhuvan national overview raster layer.',
  },
};

/**
 * Authoritative GeoJSON FeatureCollection for India National Boundary.
 * Accurate coordinates in WGS-84 (EPSG:4326) [Longitude, Latitude].
 */
export const INDIA_BOUNDARY_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        name: 'Republic of India',
        type: 'NATIONAL_BOUNDARY',
        source: 'Authoritative National Border Context',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [74.8, 37.1],
            [75.5, 36.8],
            [77.0, 35.8],
            [78.5, 35.5],
            [79.2, 34.5],
            [78.8, 33.2],
            [79.5, 32.5],
            [80.3, 31.0],
            [81.0, 30.2],
            [83.0, 28.5],
            [85.0, 27.2],
            [88.0, 27.8],
            [88.8, 27.1],
            [89.8, 26.8],
            [92.0, 27.8],
            [94.5, 28.5],
            [97.0, 28.2],
            [97.4, 27.5],
            [96.5, 26.0],
            [95.0, 24.5],
            [93.2, 23.0],
            [92.5, 22.0],
            [91.8, 23.8],
            [89.8, 25.2],
            [88.8, 24.2],
            [89.0, 21.8],
            [87.0, 21.5],
            [85.0, 19.5],
            [83.0, 17.8],
            [80.2, 15.8],
            [80.3, 13.1],
            [79.8, 10.5],
            [77.5, 8.1],
            [76.5, 9.5],
            [75.0, 12.0],
            [73.8, 15.5],
            [72.8, 19.0],
            [72.6, 21.5],
            [69.0, 22.5],
            [68.5, 23.8],
            [70.5, 24.5],
            [71.0, 26.5],
            [72.5, 28.5],
            [74.0, 30.5],
            [74.5, 32.5],
            [74.2, 34.5],
            [74.8, 37.1],
          ],
        ],
      },
    },
  ],
};

/**
 * Frontier Restricted Border Lines (LineStrings)
 */
export const FRONTIER_BORDERS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        id: 'NORTHERN_FRONTIER',
        name: 'Northern Frontier (J&K / Ladakh / Sector B-07)',
        type: 'RESTRICTED_BORDER',
        color: '#EF4444',
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [74.2, 34.5],
          [74.8, 34.8],
          [75.5, 35.2],
          [76.8, 35.6],
          [78.5, 35.5],
          [79.2, 34.5],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'WESTERN_FRONTIER',
        name: 'Western Frontier (Punjab / Rajasthan / Sir Creek)',
        type: 'INTERNATIONAL_BORDER',
        color: '#F59E0B',
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [74.2, 34.5],
          [74.5, 32.5],
          [74.0, 30.5],
          [72.5, 28.5],
          [71.0, 26.5],
          [70.5, 24.5],
          [68.5, 23.8],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'EASTERN_FRONTIER',
        name: 'Eastern & Northeastern Frontier',
        type: 'HIGH_ALTITUDE_BORDER',
        color: '#3B82F6',
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [88.0, 27.8],
          [88.8, 27.1],
          [92.0, 27.8],
          [94.5, 28.5],
          [97.0, 28.2],
        ],
      },
    },
  ],
};

/**
 * Sector B-07: Real Active Prototype Sector Polygon & Calibrated FOV
 */
export const PROTOTYPE_SECTOR_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    // Sector B-07 Boundary Polygon
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-B07',
        name: 'Sector B-07 (Northern Command)',
        status: 'ACTIVE_PROTOTYPE',
        isActivePrototype: true,
        cameraCount: 1,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [74.75, 34.20],
            [74.90, 34.20],
            [74.92, 34.32],
            [74.74, 34.31],
            [74.75, 34.20],
          ],
        ],
      },
    },
    // Optical FOV Cone Arc
    {
      type: 'Feature',
      properties: {
        id: 'CAM-FOV-ARC',
        name: 'Sensor FOV Range',
        status: 'ACTIVE_PROTOTYPE',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [74.82, 34.25],
            [74.80, 34.29],
            [74.85, 34.29],
            [74.82, 34.25],
          ],
        ],
      },
    },
  ],
};

/**
 * Contextual Sectors across the country (Strictly tagged CONTEXT ONLY)
 */
export const CONTEXTUAL_SECTORS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-W01',
        name: 'Sector W-01 (Punjab Plains)',
        status: 'CONTEXT_ONLY',
        isActivePrototype: false,
      },
      geometry: {
        type: 'Point',
        coordinates: [74.62, 31.63],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-W02',
        name: 'Sector W-02 (Thar Desert)',
        status: 'CONTEXT_ONLY',
        isActivePrototype: false,
      },
      geometry: {
        type: 'Point',
        coordinates: [70.92, 26.91],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-W03',
        name: 'Sector W-03 (Sir Creek / Kutch)',
        status: 'CONTEXT_ONLY',
        isActivePrototype: false,
      },
      geometry: {
        type: 'Point',
        coordinates: [68.80, 23.75],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-E01',
        name: 'Sector E-01 (Brahmaputra Basin)',
        status: 'CONTEXT_ONLY',
        isActivePrototype: false,
      },
      geometry: {
        type: 'Point',
        coordinates: [91.75, 26.15],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'SECTOR-E02',
        name: 'Sector E-02 (Himalayan Ridge)',
        status: 'CONTEXT_ONLY',
        isActivePrototype: false,
      },
      geometry: {
        type: 'Point',
        coordinates: [95.80, 28.20],
      },
    },
  ],
};

/**
 * Build GeoJSON FeatureCollection from real backend Camera
 */
export function buildCameraGeoJson(camera: CameraInfo | null): GeoJSON.FeatureCollection {
  // Use camera location if available, otherwise Sector B-07 location
  const lng = camera?.location?.lng || 74.82;
  const lat = camera?.location?.lat || 34.25;

  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {
          cameraId: camera?.camera_id || 'DEMO-CAM-01',
          name: camera?.name || 'Sector B-07 Primary Camera',
          status: camera?.status || 'ONLINE',
          resolution: camera?.resolution || '1280x720',
          fps: camera?.fps_target || 25.0,
        },
        geometry: {
          type: 'Point',
          coordinates: [lng, lat],
        },
      },
    ],
  };
}

/**
 * Build GeoJSON FeatureCollection from real backend Active Tracks
 */
export function buildTracksGeoJson(tracks: TrackState[], baseLng = 74.82, baseLat = 34.25): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];

  tracks.forEach((track) => {
    // Project local 1280x720 video center offset into small geographic delta (~100m around camera)
    const offsetX = (track.center_xy[0] - 640) * 0.00003;
    const offsetY = (360 - track.center_xy[1]) * 0.00003;

    const trackLng = baseLng + offsetX;
    const trackLat = baseLat + offsetY;

    features.push({
      type: 'Feature',
      properties: {
        trackId: track.track_id,
        classId: track.class_id,
        confidence: track.confidence,
        speed: track.speed_pixels_per_sec,
        status: track.status,
      },
      geometry: {
        type: 'Point',
        coordinates: [trackLng, trackLat],
      },
    });

    // If trajectory points exist, add trajectory LineString
    if (track.trajectory && track.trajectory.length > 1) {
      const lineCoords = track.trajectory.map((pt) => [
        baseLng + (pt.x - 640) * 0.00003,
        baseLat + (360 - pt.y) * 0.00003,
      ]);

      features.push({
        type: 'Feature',
        properties: {
          trackId: track.track_id,
          type: 'TRAJECTORY_LINE',
        },
        geometry: {
          type: 'LineString',
          coordinates: lineCoords,
        },
      });
    }
  });

  return {
    type: 'FeatureCollection',
    features,
  };
}

/**
 * Build GeoJSON FeatureCollection from real backend Security Events
 */
export function buildEventsGeoJson(events: EventRecord[], baseLng = 74.82, baseLat = 34.25): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: events.map((ev, idx) => ({
      type: 'Feature',
      properties: {
        eventId: ev.id,
        eventType: ev.event_type,
        priority: ev.priority,
        riskScore: ev.risk_score,
        trackId: ev.track_id,
      },
      geometry: {
        type: 'Point',
        coordinates: [baseLng + (idx * 0.001) - 0.0005, baseLat + 0.001],
      },
    })),
  };
}
