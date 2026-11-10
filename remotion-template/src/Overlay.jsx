import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";

const DEFAULT_BRAND = {
  primary: "#C24B2A",
  ink: "#1A1714",
  paper: "#F6F1E8",
  accent: "#C24B2A",
  font: "Liberation Sans",
  safe_margin: 48,
};

const DEFAULT_POSITION = {
  lower_third: "bottom-left",
  title: "center",
  callout: "bottom-right",
  quote: "center",
  cta: "bottom-center",
  logo: "top-right",
  stat: "top-left",
};

const rgba = (hex, alpha) => {
  const value = String(hex || "#000000").replace("#", "");
  const n = parseInt(value.length === 3 ? value.split("").map((c) => c + c).join("") : value, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const clamp01 = (value) => Math.max(0, Math.min(1, value));

const positionStyle = (position, margin) => {
  switch (position) {
    case "bottom-right":
      return { right: margin, bottom: margin, display: "flex", justifyContent: "flex-end" };
    case "top-left":
      return { left: margin, top: margin, display: "flex", justifyContent: "flex-start" };
    case "top-right":
      return { right: margin, top: margin, display: "flex", justifyContent: "flex-end" };
    case "center":
      return { left: 0, right: 0, top: 0, bottom: 0, display: "flex", alignItems: "center", justifyContent: "center" };
    case "bottom-center":
      return { left: 0, right: 0, bottom: margin, display: "flex", justifyContent: "center" };
    case "top-center":
      return { left: 0, right: 0, top: margin, display: "flex", justifyContent: "center" };
    default:
      return { left: margin, bottom: margin, display: "flex", justifyContent: "flex-start" };
  }
};

const textStyle = (style, brand, color) => ({
  color,
  fontFamily: `${style.font || brand.font}, "Liberation Sans", Arial, Helvetica, sans-serif`,
  fontWeight: 600,
  letterSpacing: style.uppercase ? 1.2 : 0.1,
  textTransform: style.uppercase ? "uppercase" : "none",
  lineHeight: 1.18,
});

const shadow = (enabled) =>
  enabled ? "0 8px 28px rgba(0, 0, 0, 0.28)" : "none";

const LowerThird = ({ layer, style, brand, width, height }) => {
  const text = layer.text || "";
  const subtext = layer.subtext || "";
  const accent = style.accent || brand.accent;
  const ink = style.ink || brand.ink;
  const paper = style.paper || brand.paper;
  const fontSize = style.font_size || Math.max(16, Math.round(height * 0.034));
  const subSize = Math.max(11, Math.round(fontSize * 0.58));
  return (
    <div
      style={{
        display: "flex",
        gap: Math.round(fontSize * 0.55),
        alignItems: "stretch",
        width: Math.min(style.width || Math.round(width * 0.42), width - 2 * (brand.safe_margin ?? 48)),
        background: rgba(paper, 0.96),
        borderLeft: `5px solid ${accent}`,
        borderRadius: style.radius ?? 10,
        padding: `${Math.round(fontSize * 0.5)}px ${Math.round(fontSize * 0.75)}px`,
        boxShadow: shadow(style.shadow !== false),
        opacity: style.opacity ?? 1,
      }}
    >
      <div style={{ width: 4, borderRadius: 2, background: accent, alignSelf: "stretch" }} />
      <div style={{ minWidth: 0 }}>
        <div style={{ ...textStyle(style, brand, ink), fontSize, textAlign: style.align || "left" }}>
          {text}
        </div>
        {subtext ? (
          <div
            style={{
              ...textStyle(style, brand, rgba(ink, 0.72)),
              fontSize: subSize,
              fontWeight: 500,
              marginTop: Math.round(fontSize * 0.18),
              textAlign: style.align || "left",
            }}
          >
            {subtext}
          </div>
        ) : null}
      </div>
    </div>
  );
};

const Title = ({ layer, style, brand, width, height }) => {
  const ink = style.ink || brand.ink;
  const paper = style.paper || brand.paper;
  const accent = style.accent || brand.accent;
  const fontSize = style.font_size || Math.max(30, Math.round(height * 0.078));
  return (
    <div
      style={{
        maxWidth: Math.min(style.width || Math.round(width * 0.78), width - 2 * (brand.safe_margin ?? 48)),
        padding: `${Math.round(fontSize * 0.55)}px ${Math.round(fontSize * 0.8)}px`,
        background: rgba(paper, 0.92),
        borderRadius: style.radius ?? 18,
        borderBottom: `5px solid ${accent}`,
        boxShadow: shadow(style.shadow !== false),
        opacity: style.opacity ?? 1,
        textAlign: style.align || "center",
      }}
    >
      <div style={{ ...textStyle(style, brand, ink), fontSize, fontWeight: 700 }}>
        {layer.text || ""}
      </div>
      {layer.subtext ? (
        <div
          style={{
            ...textStyle(style, brand, rgba(ink, 0.7)),
            fontSize: Math.max(13, Math.round(fontSize * 0.36)),
            fontWeight: 500,
            marginTop: Math.round(fontSize * 0.22),
            textAlign: style.align || "center",
          }}
        >
          {layer.subtext}
        </div>
      ) : null}
    </div>
  );
};

const Callout = ({ layer, style, brand, width, height }) => {
  const ink = style.ink || brand.ink;
  const paper = style.paper || brand.paper;
  const accent = style.accent || brand.accent;
  const fontSize = style.font_size || Math.max(18, Math.round(height * 0.042));
  return (
    <div
      style={{
        width: Math.min(style.width || Math.round(width * 0.38), width - 2 * (brand.safe_margin ?? 48)),
        background: rgba(paper, 0.97),
        border: `1px solid ${rgba(accent, 0.35)}`,
        borderLeft: `6px solid ${accent}`,
        borderRadius: style.radius ?? 14,
        padding: `${Math.round(fontSize * 0.7)}px ${Math.round(fontSize * 0.85)}px`,
        boxShadow: shadow(style.shadow !== false),
        opacity: style.opacity ?? 1,
      }}
    >
      <div style={{ ...textStyle(style, brand, ink), fontSize, textAlign: style.align || "left" }}>
        {layer.text || ""}
      </div>
      {layer.subtext ? (
        <div
          style={{
            ...textStyle(style, brand, rgba(ink, 0.68)),
            fontSize: Math.max(12, Math.round(fontSize * 0.62)),
            fontWeight: 500,
            marginTop: Math.round(fontSize * 0.25),
            textAlign: style.align || "left",
          }}
        >
          {layer.subtext}
        </div>
      ) : null}
    </div>
  );
};

const Quote = ({ layer, style, brand, width, height }) => {
  const ink = style.ink || brand.ink;
  const paper = style.paper || brand.paper;
  const accent = style.accent || brand.accent;
  const fontSize = style.font_size || Math.max(22, Math.round(height * 0.052));
  return (
    <div
      style={{
        width: Math.min(style.width || Math.round(width * 0.66), width - 2 * (brand.safe_margin ?? 48)),
        padding: `${Math.round(fontSize * 0.6)}px ${Math.round(fontSize * 0.9)}px`,
        background: rgba(paper, 0.94),
        borderRadius: style.radius ?? 16,
        boxShadow: shadow(style.shadow !== false),
        opacity: style.opacity ?? 1,
        textAlign: style.align || "left",
      }}
    >
      <div style={{ color: accent, fontFamily: "Georgia, serif", fontSize: Math.round(fontSize * 2.2), lineHeight: 0.7, marginBottom: Math.round(fontSize * 0.25) }}>
        “
      </div>
      <div style={{ ...textStyle(style, brand, ink), fontSize, fontStyle: "italic", fontWeight: 500, textAlign: style.align || "left" }}>
        {layer.text || ""}
      </div>
      {layer.subtext ? (
        <div
          style={{
            ...textStyle(style, brand, rgba(ink, 0.65)),
            fontSize: Math.max(12, Math.round(fontSize * 0.42)),
            fontWeight: 500,
            marginTop: Math.round(fontSize * 0.45),
            textAlign: style.align || "left",
          }}
        >
          {layer.subtext}
        </div>
      ) : null}
    </div>
  );
};

const Cta = ({ layer, style, brand, height }) => {
  const paper = style.paper || brand.paper;
  const accent = style.accent || brand.accent;
  const fontSize = style.font_size || Math.max(16, Math.round(height * 0.033));
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: `${Math.round(fontSize * 0.7)}px ${Math.round(fontSize * 1.25)}px`,
        borderRadius: style.radius ?? 999,
        background: accent,
        boxShadow: shadow(style.shadow !== false),
        opacity: style.opacity ?? 1,
      }}
    >
      <div
        style={{
          ...textStyle(style, brand, paper),
          fontSize,
          fontWeight: 700,
          letterSpacing: 1.1,
          textTransform: "uppercase",
          textAlign: style.align || "center",
        }}
      >
        {layer.text || ""}
      </div>
    </div>
  );
};

const Logo = ({ layer, style }) => (
  <Img
    src={staticFile(layer.asset)}
    style={{
      width: style.width || 120,
      height: "auto",
      opacity: style.opacity ?? 0.92,
      filter: style.shadow === false ? "none" : "drop-shadow(0 4px 14px rgba(0,0,0,0.28))",
    }}
  />
);

const Stat = ({ layer, style, brand, height }) => {
  const ink = style.ink || brand.ink;
  const accent = style.accent || brand.accent;
  const fontSize = style.font_size || Math.max(34, Math.round(height * 0.095));
  return (
    <div style={{ opacity: style.opacity ?? 1, textAlign: style.align || "left" }}>
      <div style={{ ...textStyle(style, brand, accent), fontSize, fontWeight: 800, lineHeight: 1 }}>
        {layer.text || ""}
      </div>
      {layer.subtext ? (
        <div
          style={{
            ...textStyle(style, brand, ink),
            fontSize: Math.max(12, Math.round(height * 0.022)),
            fontWeight: 600,
            letterSpacing: 0.8,
            textTransform: "uppercase",
            marginTop: Math.round(height * 0.012),
            textAlign: style.align || "left",
          }}
        >
          {layer.subtext}
        </div>
      ) : null}
    </div>
  );
};

const PRESETS = {
  lower_third: LowerThird,
  title: Title,
  callout: Callout,
  quote: Quote,
  cta: Cta,
  logo: Logo,
  stat: Stat,
};

export const Overlay = ({ layer, brand = {}, width, height, durationInFrames = 1 }) => {
  const frame = useCurrentFrame();
  const style = layer.style || {};
  const merged = { ...DEFAULT_BRAND, ...brand };
  const preset = layer.preset;
  const Component = PRESETS[preset];
  if (!Component) return null;

  const margin = layer.safe_area === false ? 0 : merged.safe_margin ?? 48;
  const enter = clamp01(frame / 8);
  const exit = clamp01((durationInFrames - frame) / 8);
  const opacity = Math.min(enter, exit);
  const slide = (1 - enter) * 18;
  const scale = preset === "title" || preset === "logo" ? 0.96 + 0.04 * enter : 1;
  const position = positionStyle(layer.position || DEFAULT_POSITION[preset], margin);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          ...position,
          opacity,
          transform: `translate3d(0, ${slide}px, 0) scale(${scale})`,
        }}
      >
        <Component
          layer={layer}
          style={style}
          brand={merged}
          width={width}
          height={height}
        />
      </div>
    </AbsoluteFill>
  );
};
