// SIRA Design System — Typography Tokens
import { TextStyle } from 'react-native';

export const typography: Record<string, TextStyle> = {
  // Display: major headings
  displayLarge:   { fontSize: 32, fontWeight: '800', letterSpacing: -0.5 },
  displayMedium:  { fontSize: 24, fontWeight: '700', letterSpacing: -0.3 },

  // Body
  bodyLarge:      { fontSize: 17, fontWeight: '400', lineHeight: 26 },
  bodyMedium:     { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  bodySmall:      { fontSize: 13, fontWeight: '400', lineHeight: 18 },

  // UI labels
  labelLarge:     { fontSize: 16, fontWeight: '700', letterSpacing: 1 },
  labelMedium:    { fontSize: 14, fontWeight: '600', letterSpacing: 0.5 },
  caption:        { fontSize: 12, fontWeight: '500', letterSpacing: 0.3 },

  // Action buttons (uppercase)
  buttonPrimary:  { fontSize: 18, fontWeight: '800', letterSpacing: 1.5 },
  buttonSecondary:{ fontSize: 15, fontWeight: '700', letterSpacing: 0.8 },
};
