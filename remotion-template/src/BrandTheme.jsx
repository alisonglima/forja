// Tema de marca do video: merge do `brand` que chega por props (plano:1574).
// Defaults espelham `forja/brand_tokens.py` e o fallback do Overlay.jsx.

export const DEFAULT_BRAND = {
  primary: "#C24B2A",
  ink: "#1A1714",
  paper: "#F6F1E8",
  accent: "#C24B2A",
  font: "Liberation Sans",
  safe_margin: 48,
};

export const BRAND_KEYS = [
  "primary",
  "ink",
  "paper",
  "accent",
  "font",
  "safe_margin",
];

// Devolve sempre um objeto novo; chave ausente ou nula cai no default.
export const mergeBrand = (brand = {}) => {
  const source = brand && typeof brand === "object" ? brand : {};
  const merged = { ...DEFAULT_BRAND };
  for (const key of BRAND_KEYS) {
    const value = source[key];
    if (value !== undefined && value !== null) {
      merged[key] = value;
    }
  }
  return merged;
};
