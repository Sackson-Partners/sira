module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    // Existing codebase uses `any` types throughout — enforce gradually, not all at once
    '@typescript-eslint/no-explicit-any': 'off',
    // Existing codebase has unused vars throughout — enforce gradually
    '@typescript-eslint/no-unused-vars': 'off',
    // Allow empty catch blocks (common pattern for optional error handling)
    'no-empty': ['error', { allowEmptyCatch: true }],
  },
}
