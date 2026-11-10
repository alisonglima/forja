import { interpolate, useCurrentFrame } from "remotion";

const FADE = 4; // quadros

export const Captions = ({ subs = [], lowerThirds = [], fps, width, height, fontSize }) => {
  const EDGE_BASE = Math.round(height * 0.945);
  const EDGE_RAISED = Math.round(height * 0.795);
  const maxWidth = width * 0.875;
  const lineHeight = fontSize * 1.25;

  // 0 = base, 1 = acima da tarja; sobe/desce suavemente (6 quadros) conforme a tarja entra e sai.
  const raise = (frame) =>
    Math.max(0, ...lowerThirds.map(([a, b]) => {
      let f1 = Math.round((a - 0.2) * fps);
      let f2 = Math.round((b + 0.2) * fps);
      if (f2 <= f1) f2 = f1 + 1;
      return interpolate(frame, [f1 - 6, f1, f2, f2 + 6], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    }));

  const frame = useCurrentFrame();
  const raisedAt = raise(frame);

  return (
    <>
      {subs.map((s, i) => {
        const a = Math.round(s.start * fps);
        const b = Math.max(a + 1, Math.round(s.end * fps));
        if (frame < a || frame >= b) return null;
        const opacity = interpolate(frame, [a, a + FADE, b - FADE, b], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const bottom = height - (EDGE_BASE + (EDGE_RAISED - EDGE_BASE) * (s.raised ? raisedAt : 0));
        return (
          <div key={i} style={{ position: "absolute", left: 0, right: 0, bottom, display: "flex", justifyContent: "center", opacity }}>
            <div
              style={{
                background: "rgba(0,0,0,0.58)",
                borderRadius: 12,
                padding: "8px 22px 10px",
                textAlign: "center",
                color: "#fff",
                fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
                fontWeight: 700,
                fontSize,
                lineHeight: `${lineHeight}px`,
                fontStyle: s.narrador ? "italic" : "normal",
                textShadow: "0 2px 4px rgba(0,0,0,0.7)",
                maxWidth,
              }}
            >
              {s.lines.map((l, j) => (
                <div key={j}>{l}</div>
              ))}
            </div>
          </div>
        );
      })}
    </>
  );
};
