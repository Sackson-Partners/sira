// SIRA Africa Infrastructure Data — real coordinates

export interface Port {
  id: string; name: string; country: string; coords: [number, number];
  type: string; vessels: number; volume: string;
}
export interface Vessel {
  id: string; name: string; type: string; lat: number; lng: number;
  heading: number; speed: number; flag: string; imo: string;
}
export interface Truck {
  id: string; name: string; coords: [number, number]; route: string; cargo: string;
}
export interface GasStation {
  id: string; name: string; coords: [number, number]; brand: string;
}
export interface Corridor {
  id: string; name: string; color: string; weight: number;
  path: [number, number][];
}
export interface Railway {
  id: string; name: string; color: string; weight: number;
  dashArray: string; path: [number, number][];
}
export interface MiningSite {
  id: string; name: string; country: string; coords: [number, number];
  type: string; operator: string;
}
export interface OilGasSite {
  id: string; name: string; country: string; coords: [number, number];
  type: string; production: string;
}
export interface EnergySite {
  id: string; name: string; country: string; coords: [number, number];
  type: string; capacity: string;
}

// ─── COASTAL PORTS ────────────────────────────────────────────────────────────
export const coastalPorts: Port[] = [
  { id: "p1",  name: "Port of Abidjan",         country: "Côte d'Ivoire", coords: [5.289, -4.003],   type: "port", vessels: 12, volume: "2.1M TEU" },
  { id: "p2",  name: "Port of Lagos (Apapa)",   country: "Nigeria",       coords: [6.447, 3.364],    type: "port", vessels: 28, volume: "1.8M TEU" },
  { id: "p3",  name: "Port of Tema",             country: "Ghana",         coords: [5.637, -0.017],   type: "port", vessels: 15, volume: "0.9M TEU" },
  { id: "p4",  name: "Port of Dakar",            country: "Senegal",       coords: [14.692, -17.437], type: "port", vessels: 8,  volume: "0.6M TEU" },
  { id: "p5",  name: "Port of Lomé",             country: "Togo",          coords: [6.133, 1.283],    type: "port", vessels: 10, volume: "1.2M TEU" },
  { id: "p6",  name: "Port of Cotonou",          country: "Benin",         coords: [6.348, 2.421],    type: "port", vessels: 7,  volume: "0.8M TEU" },
  { id: "p7",  name: "Port of Conakry",          country: "Guinea",        coords: [9.508, -13.700],  type: "port", vessels: 5,  volume: "0.4M TEU" },
  { id: "p8",  name: "Tin Can Island Port",      country: "Nigeria",       coords: [6.424, 3.298],    type: "port", vessels: 18, volume: "1.1M TEU" },
  { id: "p9",  name: "Port of Mombasa",          country: "Kenya",         coords: [-4.043, 39.668],  type: "port", vessels: 20, volume: "1.5M TEU" },
  { id: "p10", name: "Port of Dar es Salaam",    country: "Tanzania",      coords: [-6.819, 39.289],  type: "port", vessels: 16, volume: "0.8M TEU" },
  { id: "p11", name: "Port of Djibouti",         country: "Djibouti",      coords: [11.589, 43.145],  type: "port", vessels: 22, volume: "1.0M TEU" },
  { id: "p12", name: "Port of Maputo",           country: "Mozambique",    coords: [-25.966, 32.572], type: "port", vessels: 9,  volume: "0.5M TEU" },
  { id: "p13", name: "Port of Durban",           country: "South Africa",  coords: [-29.868, 31.029], type: "port", vessels: 35, volume: "2.7M TEU" },
  { id: "p14", name: "Port of Cape Town",        country: "South Africa",  coords: [-33.917, 18.424], type: "port", vessels: 18, volume: "0.9M TEU" },
  { id: "p15", name: "Port Elizabeth (Ngqura)",  country: "South Africa",  coords: [-33.843, 25.624], type: "port", vessels: 12, volume: "0.7M TEU" },
]

// ─── LIVE VESSELS ─────────────────────────────────────────────────────────────
export const initialVessels: Vessel[] = [
  { id: "v1",  name: "MSC Abidjan",     type: "container", lat: 5.8,   lng: -4.5,  heading: 135, speed: 0.008, flag: "🇨🇮", imo: "9234567" },
  { id: "v2",  name: "Crude Carrier I", type: "tanker",    lat: 4.2,   lng: 3.8,   heading: 90,  speed: 0.006, flag: "🇳🇬", imo: "9345678" },
  { id: "v3",  name: "Bulk Lagos",      type: "bulk",      lat: 6.8,   lng: 2.1,   heading: 200, speed: 0.007, flag: "🇳🇬", imo: "9456789" },
  { id: "v4",  name: "Tema Star",       type: "container", lat: 5.2,   lng: 0.5,   heading: 270, speed: 0.009, flag: "🇬🇭", imo: "9567890" },
  { id: "v5",  name: "Dakar Express",   type: "cargo",     lat: 14.1,  lng: -17.8, heading: 45,  speed: 0.010, flag: "🇸🇳", imo: "9678901" },
  { id: "v6",  name: "Gulf of Guinea",  type: "tanker",    lat: 3.5,   lng: 5.2,   heading: 180, speed: 0.005, flag: "🇳🇬", imo: "9789012" },
  { id: "v7",  name: "Mombasa Trader",  type: "container", lat: -3.5,  lng: 40.2,  heading: 225, speed: 0.008, flag: "🇰🇪", imo: "9890123" },
  { id: "v8",  name: "Indian Ocean I",  type: "bulk",      lat: -6.2,  lng: 41.5,  heading: 315, speed: 0.007, flag: "🇹🇿", imo: "9901234" },
  { id: "v9",  name: "Djibouti Link",   type: "cargo",     lat: 11.2,  lng: 43.8,  heading: 160, speed: 0.009, flag: "🇩🇯", imo: "9012345" },
  { id: "v10", name: "Durban Carrier",  type: "container", lat: -30.2, lng: 31.5,  heading: 45,  speed: 0.008, flag: "🇿🇦", imo: "9123456" },
  { id: "v11", name: "Cape Trader",     type: "tanker",    lat: -34.2, lng: 17.8,  heading: 90,  speed: 0.006, flag: "🇿🇦", imo: "9234561" },
  { id: "v12", name: "Offshore Rig I",  type: "offshore",  lat: 3.8,   lng: 6.5,   heading: 0,   speed: 0.001, flag: "🇳🇬", imo: "9345672" },
  { id: "v13", name: "FPSO Atlantic",   type: "fpso",      lat: -8.5,  lng: 12.2,  heading: 0,   speed: 0.001, flag: "🇦🇴", imo: "9456783" },
]

// ─── INLAND CORRIDOR TRUCKS ───────────────────────────────────────────────────
export const trucks: Truck[] = [
  { id: "t1", name: "Abidjan–Ouaga Corridor",  coords: [7.2, -5.4],   route: "Port of Abidjan → Ouagadougou", cargo: "Electronics" },
  { id: "t2", name: "Lagos–Kano Corridor",     coords: [9.1, 7.8],    route: "Lagos → Kano → Niger",         cargo: "Consumer Goods" },
  { id: "t3", name: "Tema–Ouaga Corridor",     coords: [8.5, -1.2],   route: "Tema → Ouagadougou → Bamako",  cargo: "Fuel" },
  { id: "t4", name: "Lomé–Ouaga Corridor",     coords: [9.8, 0.9],    route: "Lomé → Ouagadougou",           cargo: "Mixed Cargo" },
  { id: "t5", name: "Mombasa–Nairobi",         coords: [-1.2, 37.8],  route: "Mombasa → Nairobi → Kampala",  cargo: "FMCG" },
  { id: "t6", name: "Dar–Lusaka Corridor",     coords: [-8.9, 33.4],  route: "Dar es Salaam → Lusaka",       cargo: "Copper" },
  { id: "t7", name: "Durban–Jo'burg",          coords: [-27.5, 29.8], route: "Durban → Johannesburg",        cargo: "Automobiles" },
  { id: "t8", name: "Walvis Bay Corridor",     coords: [-22.9, 18.5], route: "Walvis Bay → Zambia",          cargo: "Mining Equipment" },
]

// ─── GAS STATIONS ─────────────────────────────────────────────────────────────
export const gasStations: GasStation[] = [
  { id: "g1", name: "TotalEnergies Abidjan Hub", coords: [5.4, -4.1],   brand: "TotalEnergies" },
  { id: "g2", name: "Shell Lagos Distribution",  coords: [6.6, 3.5],    brand: "Shell" },
  { id: "g3", name: "Vivo Energy Tema",          coords: [5.7, -0.1],   brand: "Vivo Energy" },
  { id: "g4", name: "ORYX Dakar",                coords: [14.8, -17.5], brand: "ORYX" },
  { id: "g5", name: "TotalEnergies Nairobi",     coords: [-1.3, 36.9],  brand: "TotalEnergies" },
  { id: "g6", name: "Engen Mombasa",             coords: [-4.1, 39.7],  brand: "Engen" },
  { id: "g7", name: "BP Cape Town",              coords: [-33.9, 18.5], brand: "BP" },
  { id: "g8", name: "Sasol Johannesburg",        coords: [-26.2, 28.1], brand: "Sasol" },
]

// ─── INLAND CORRIDORS (ROADS) ─────────────────────────────────────────────────
export const corridors: Corridor[] = [
  { id: "r1", name: "Abidjan–Lagos Corridor",  color: "#f59e0b", weight: 3,
    path: [[5.289, -4.003], [5.637, -0.017], [6.133, 1.283], [6.348, 2.421], [6.447, 3.364]] },
  { id: "r2", name: "Dakar–Abidjan Highway",   color: "#f59e0b", weight: 3,
    path: [[14.692, -17.437], [13.5, -16.2], [12.3, -15.1], [9.5, -13.7], [7.7, -10.8], [6.3, -10.6], [5.289, -4.003]] },
  { id: "r3", name: "Trans-African Highway",   color: "#f59e0b", weight: 3,
    path: [[6.447, 3.364], [9.1, 7.8], [12.0, 8.5], [13.5, 13.2], [15.5, 32.5]] },
  { id: "r4", name: "Northern Corridor (EA)",  color: "#f59e0b", weight: 3,
    path: [[-4.043, 39.668], [-1.2, 37.8], [-1.286, 36.817], [0.3, 32.5]] },
  { id: "r5", name: "Dar–Lusaka Highway",      color: "#f59e0b", weight: 3,
    path: [[-6.819, 39.289], [-8.9, 33.4], [-10.5, 31.2], [-13.1, 32.5], [-15.4, 28.3]] },
  { id: "r6", name: "N1 — Durban–Jo'burg",    color: "#f59e0b", weight: 3,
    path: [[-29.868, 31.029], [-27.5, 29.8], [-26.2, 28.1]] },
  { id: "r7", name: "Walvis Bay Corridor",     color: "#f59e0b", weight: 3,
    path: [[-22.959, 14.505], [-22.9, 18.5], [-18.5, 22.3], [-15.4, 28.3]] },
]

// ─── RAILWAYS ─────────────────────────────────────────────────────────────────
export const railways: Railway[] = [
  { id: "rw1", name: "Abuja–Kaduna Railway",      color: "#a855f7", weight: 2, dashArray: "8,4",
    path: [[9.07, 7.39], [10.5, 7.44], [11.0, 7.8]] },
  { id: "rw2", name: "SGR Mombasa–Nairobi",       color: "#a855f7", weight: 2, dashArray: "8,4",
    path: [[-4.043, 39.668], [-1.286, 36.817]] },
  { id: "rw3", name: "TAZARA Railway",            color: "#a855f7", weight: 2, dashArray: "8,4",
    path: [[-6.819, 39.289], [-10.2, 34.1], [-13.1, 32.5], [-15.4, 28.3]] },
  { id: "rw4", name: "Benguela Railway (Angola)", color: "#a855f7", weight: 2, dashArray: "8,4",
    path: [[-12.3, 13.5], [-11.8, 19.9], [-11.0, 24.0], [-10.5, 28.5]] },
  { id: "rw5", name: "Gauteng Rail Network",      color: "#a855f7", weight: 2, dashArray: "8,4",
    path: [[-29.868, 31.029], [-26.2, 28.1], [-33.917, 18.424]] },
]

// ─── MINING SITES ─────────────────────────────────────────────────────────────
export const miningSites: MiningSite[] = [
  { id: "m1",  name: "Kibali Gold Mine",       country: "DRC",          coords: [3.6, 29.6],   type: "Gold",          operator: "Barrick" },
  { id: "m2",  name: "Tenke Fungurume",        country: "DRC",          coords: [-10.6, 26.1], type: "Copper/Cobalt", operator: "CMOC" },
  { id: "m3",  name: "Lumwana Copper Mine",    country: "Zambia",       coords: [-12.5, 25.8], type: "Copper",        operator: "Barrick" },
  { id: "m4",  name: "Obuasi Gold Mine",       country: "Ghana",        coords: [6.2, -1.7],   type: "Gold",          operator: "AngloGold" },
  { id: "m5",  name: "Marikana Platinum",      country: "South Africa", coords: [-25.7, 27.1], type: "Platinum",      operator: "Lonmin" },
  { id: "m6",  name: "Sishen Iron Ore",        country: "South Africa", coords: [-27.8, 23.0], type: "Iron Ore",      operator: "Kumba" },
  { id: "m7",  name: "Geita Gold Mine",        country: "Tanzania",     coords: [-2.9, 32.2],  type: "Gold",          operator: "AngloGold" },
  { id: "m8",  name: "Rossing Uranium",        country: "Namibia",      coords: [-22.5, 14.9], type: "Uranium",       operator: "Rio Tinto" },
  { id: "m9",  name: "Simandou Iron Ore",      country: "Guinea",       coords: [9.0, -12.0],  type: "Iron Ore",      operator: "Rio Tinto/Chinalco" },
  { id: "m10", name: "Tasiast Gold Mine",      country: "Mauritania",   coords: [21.0, -12.0], type: "Gold",          operator: "Kinross" },
]

// ─── OFFSHORE & ONSHORE OIL/GAS ───────────────────────────────────────────────
export const oilGasSites: OilGasSite[] = [
  { id: "o1",  name: "Bonga Deepwater (FPSO)", country: "Nigeria",    coords: [3.8, 5.5],    type: "offshore", production: "225,000 bpd" },
  { id: "o2",  name: "Agbami Deepwater",       country: "Nigeria",    coords: [3.2, 6.2],    type: "offshore", production: "250,000 bpd" },
  { id: "o3",  name: "Jubilee Field",          country: "Ghana",      coords: [5.0, -2.5],   type: "offshore", production: "100,000 bpd" },
  { id: "o4",  name: "SNE Field",              country: "Senegal",    coords: [12.5, -17.8], type: "offshore", production: "100,000 bpd" },
  { id: "o5",  name: "Coral FLNG",             country: "Mozambique", coords: [-12.0, 41.5], type: "offshore", production: "3.4M tpa LNG" },
  { id: "o6",  name: "Block 17 (FPSO Dalia)",  country: "Angola",     coords: [-7.8, 11.5],  type: "offshore", production: "160,000 bpd" },
  { id: "o7",  name: "Bonny Oil Terminal",     country: "Nigeria",    coords: [4.5, 7.2],    type: "onshore",  production: "Terminal" },
  { id: "o8",  name: "Warri Refinery",         country: "Nigeria",    coords: [5.5, 5.8],    type: "onshore",  production: "Refinery" },
  { id: "o9",  name: "Hassi Messaoud",         country: "Algeria",    coords: [31.7, 6.1],   type: "onshore",  production: "400,000 bpd" },
  { id: "o10", name: "Mellitah Complex",       country: "Libya",      coords: [32.9, 12.6],  type: "onshore",  production: "Gas/Oil" },
]

// ─── ENERGY SITES ─────────────────────────────────────────────────────────────
export const energySites: EnergySite[] = [
  { id: "e1",  name: "Hornsdale Power Reserve", country: "South Africa",  coords: [-28.5, 24.5], type: "Battery Storage", capacity: "150 MW" },
  { id: "e2",  name: "Noor Ouarzazate Solar",   country: "Morocco",       coords: [30.9, -6.9],  type: "Solar CSP",       capacity: "580 MW" },
  { id: "e3",  name: "Lake Turkana Wind",        country: "Kenya",         coords: [2.1, 36.8],   type: "Wind Farm",       capacity: "310 MW" },
  { id: "e4",  name: "Inga Hydropower",          country: "DRC",           coords: [-5.5, 13.6],  type: "Hydro",           capacity: "351 MW" },
  { id: "e5",  name: "Benban Solar Park",        country: "Egypt",         coords: [24.5, 32.7],  type: "Solar PV",        capacity: "1,650 MW" },
  { id: "e6",  name: "De Aar Wind Farm",         country: "South Africa",  coords: [-30.7, 24.0], type: "Wind Farm",       capacity: "240 MW" },
  { id: "e7",  name: "Azito Power Plant",        country: "Côte d'Ivoire", coords: [5.4, -4.0],   type: "Gas Power",       capacity: "440 MW" },
  { id: "e8",  name: "Koysha Dam",               country: "Ethiopia",      coords: [6.5, 37.2],   type: "Hydro",           capacity: "2,160 MW" },
  { id: "e9",  name: "Lekela Wind (Senegal)",    country: "Senegal",       coords: [14.9, -16.8], type: "Wind Farm",       capacity: "158 MW" },
  { id: "e10", name: "Kipeto Wind Farm",         country: "Kenya",         coords: [-1.8, 36.5],  type: "Wind Farm",       capacity: "100 MW" },
]

export const REGIONS = {
  westAfrica:    { center: [7.5, -2.5]   as [number,number], zoom: 5 },
  eastAfrica:    { center: [-2.0, 37.0]  as [number,number], zoom: 5 },
  southernAfrica:{ center: [-28.0, 25.0] as [number,number], zoom: 5 },
  fullAfrica:    { center: [5.0, 20.0]   as [number,number], zoom: 4 },
}
