// SIRA Design System — Color Tokens
export const colors = {
  // Brand
  primary: '#0A1F44',        // Deep Navy
  primaryLight: '#1A3A6E',
  primaryDim: '#0A1F4499',
  accent: '#FF7A00',         // Operational Orange
  accentLight: '#FF7A0020',

  // Semantic
  success: '#00B96B',
  successLight: '#00B96B20',
  warning: '#F5A623',
  warningLight: '#F5A62320',
  error: '#E84040',
  errorLight: '#E8404020',
  info: '#3D8EFF',

  // Risk
  riskLow: '#00B96B',
  riskMedium: '#F5A623',
  riskHigh: '#E84040',

  // Surface
  background: '#060E1E',     // Near-black navy
  surface: '#0F1E38',
  surfaceHigh: '#162846',
  border: '#FFFFFF12',

  // Text
  white: '#FFFFFF',
  textPrimary: '#F0F4FF',
  textSecondary: '#8BA0C4',
  textMuted: '#4A6080',
} as const;

export type ColorKey = keyof typeof colors;
