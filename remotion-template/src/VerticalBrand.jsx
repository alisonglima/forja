import { AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Captions } from "./Captions.jsx";

// Zonas seguras do vertical 1080x1920: 15% topo/base e 10% laterais.
const SAFE_TOP = 0.15;
const SAFE_BOTTOM = 0.15;
const SAFE_SIDE = 0.1;
const SAFE_MARGIN = 48;
const DEFAULT_FPS = 30;
const DEFAULT_DURATION_S = 5;
const DEFAULT_FRAMES = 150;

const clamp01 = (value) => Math.max(0, Math.min(1, value));

// Mesmas chaves do runtime de marca (primary, ink, paper, accent, font,
// safe_margin). Fallbacks neutros: o tema real chega por props.
export const mergeBrand = (brand = {}) => ({
  ink: brand.ink || "black",
  paper: brand.paper || "white",
  accent: brand.accent || brand.primary || "white",
  primary: brand.primary || brand.accent || "white",
  font: brand.font || "Liberation Sans",
  safe_margin: brand.safe_margin ?? SAFE_MARGIN,
});

const LogoMark = ({ brand, size, color }) => {
  if (brand.logo) {
    return <Img src={staticFile(brand.logo)} style={{ width: size, height: "auto", objectFit: "contain", display: "block" }} />;
  }
  const name = brand.name || brand.id || "";
  if (!name) return null;
  return (
    <div
      style={{
        width: size, height: size, background: color, color: brand.paper || "black",
        borderRadius: Math.round(size * 0.22), display: "flex", alignItems: "center",
        justifyContent: "center", fontSize: Math.round(size * 0.52), fontWeight: 800, lineHeight: 1,
      }}
    >
      {name.slice(0, 1).toUpperCase()}
    </div>
  );
};

export const Opening = ({ brand = {}, title = "", subtitle = "", width = 1080, height = 1920 }) => {
  const frame = useCurrentFrame();
  const theme = mergeBrand(brand);
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
  // Visivel ja no primeiro frame: nunca comeca em opacidade zero.
  const enter = interpolate(frame, [0, 12], [0.85, 1], clamp);
  const rise = interpolate(frame, [0, 18], [18, 0], clamp);
  const zoom = interpolate(frame, [0, 24], [0.98, 1], clamp);
  const padX = Math.max(Math.round(width * SAFE_SIDE), theme.safe_margin);
  const padY = Math.max(Math.round(height * SAFE_TOP), theme.safe_margin);
  const titleSize = Math.max(56, Math.round(height * 0.082));
  const logoSize = Math.round(width * 0.16);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.ink, fontFamily: theme.font }}>
      <div
        style={{
          position: "absolute", inset: 0, padding: `${padY}px ${padX}px`,
          display: "flex", flexDirection: "column", justifyContent: "space-between",
          opacity: enter, transform: `translateY(${rise}px)`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: Math.round(width * 0.04) }}>
          <div style={{ transform: `scale(${zoom})`, transformOrigin: "left center" }}>
            <LogoMark brand={brand} size={logoSize} color={theme.accent} />
          </div>
          {brand.name ? (
            <div
              style={{
                color: theme.paper, fontSize: Math.round(width * 0.038), fontWeight: 600,
                letterSpacing: 1.4, textTransform: "uppercase", opacity: 0.86,
              }}
            >
              {brand.name}
            </div>
          ) : null}
        </div>

        <div style={{ maxWidth: width - 2 * padX }}>
          <div
            style={{
              width: Math.round(width * 0.18), height: 8, borderRadius: 4,
              background: theme.accent, marginBottom: Math.round(height * 0.028),
            }}
          />
          {title ? (
            <div
              style={{
                color: theme.paper, fontSize: titleSize, fontWeight: 800,
                lineHeight: 1.02, letterSpacing: -1.5, wordBreak: "break-word",
              }}
            >
              {title}
            </div>
          ) : null}
          {subtitle ? (
            <div
              style={{
                color: theme.paper, fontSize: Math.max(26, Math.round(height * 0.023)),
                fontWeight: 500, lineHeight: 1.3, marginTop: Math.round(height * 0.022), opacity: 0.74,
              }}
            >
              {subtitle}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const LowerThird = ({
  text = "", subtext = "", brand = {}, width = 1080, height = 1920,
  durationInFrames = DEFAULT_FRAMES,
}) => {
  const frame = useCurrentFrame();
  const theme = mergeBrand(brand);
  const side = Math.max(Math.round(width * SAFE_SIDE), theme.safe_margin);
  const visible = Math.min(clamp01(frame / 8), clamp01((durationInFrames - frame) / 8));
  const slide = (1 - clamp01(frame / 8)) * 24;
  const fontSize = Math.max(28, Math.round(height * 0.028));
  const subSize = Math.max(20, Math.round(fontSize * 0.62));
  return (
    <div
      style={{
        position: "absolute", left: side, right: side,
        // Acima da faixa da legenda (base em 94,5% = ~206 px do fundo).
        bottom: 240, opacity: visible, transform: `translateY(${slide}px)`,
      }}
    >
      <div
        style={{
          display: "flex", gap: Math.round(fontSize * 0.55), alignItems: "stretch",
          background: theme.paper, borderLeft: `6px solid ${theme.accent}`, borderRadius: 12,
          padding: `${Math.round(fontSize * 0.55)}px ${Math.round(fontSize * 0.8)}px`,
          boxShadow: "0 8px 28px rgba(0, 0, 0, 0.28)",
        }}
      >
        <div style={{ width: 4, borderRadius: 2, background: theme.accent, alignSelf: "stretch" }} />
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              color: theme.ink, fontFamily: theme.font, fontSize, fontWeight: 700,
              lineHeight: 1.18, wordBreak: "break-word",
            }}
          >
            {text}
          </div>
          {subtext ? (
            <div
              style={{
                color: theme.ink, fontFamily: theme.font, fontSize: subSize, fontWeight: 500,
                lineHeight: 1.22, marginTop: Math.round(fontSize * 0.18), opacity: 0.72,
                wordBreak: "break-word",
              }}
            >
              {subtext}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
const normalizeWindow = (item, index) => {
  if (Array.isArray(item)) {
    return { key: `lt-${index}`, start: item[0] || 0, end: item[1] || 0, text: item[2] || "", subtext: item[3] || "" };
  }
  const rule = item || {};
  return {
    key: rule.id || `lt-${index}`, start: rule.start || 0, end: rule.end || 0,
    text: rule.text || "", subtext: rule.subtext || "",
  };
};

export const VerticalBrand = ({
  brand = {}, subs = [], lowerThirds = [], title = "", subtitle = "",
  fps = DEFAULT_FPS, width = 1080, height = 1920, durationS = DEFAULT_DURATION_S, fontSize = 44,
}) => {
  const durationInFrames = Math.max(1, Math.round(durationS * fps));
  const theme = mergeBrand(brand);
  const side = Math.max(Math.round(width * SAFE_SIDE), theme.safe_margin);
  const windows = (lowerThirds || []).map(normalizeWindow);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.ink, fontFamily: theme.font }}>
      <Sequence durationInFrames={durationInFrames}>
        <Opening brand={brand} title={title} subtitle={subtitle} width={width} height={height} />
      </Sequence>

      {windows.map((window) => {
        if (window.end <= window.start) return null;
        const from = Math.max(0, Math.round(window.start * fps));
        const available = Math.max(1, durationInFrames - from);
        const frames = Math.max(1, Math.min(available, Math.round((window.end - window.start) * fps)));
        return (
          <Sequence key={window.key} from={from} durationInFrames={frames}>
            <LowerThird
              text={window.text} subtext={window.subtext} brand={brand}
              width={width} height={height} durationInFrames={frames}
            />
          </Sequence>
        );
      })}

      {/* Legenda limitada a 10% de cada lado; a base continua a do Captions. */}
      <div style={{ position: "absolute", top: 0, left: side, right: side, height: "100%" }}>
        <Captions
          subs={subs} lowerThirds={windows.map((w) => [w.start, w.end, w.text, w.subtext])} fps={fps}
          width={width - 2 * side} height={height} fontSize={fontSize}
        />
      </div>
    </AbsoluteFill>
  );
};
