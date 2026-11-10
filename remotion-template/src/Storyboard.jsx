import { AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Captions } from "./Captions.jsx";

const ClipLayer = ({ layer, width, height, fps }) => (
  <OffthreadVideo
    muted
    src={staticFile(layer.file)}
    startFrom={Math.round((layer.in_s || 0) * fps)}
    playbackRate={layer.playback_rate || 1}
    style={{ width, height, objectFit: layer.fit === "contain" ? "contain" : "cover" }}
  />
);

const CardLayer = ({ layer, durationInFrames }) => {
  const frame = useCurrentFrame();
  const fullFrame = Boolean(layer.full_frame);

  // Fade de 6 quadros na entrada/saída; encurta em durações curtas para manter
  // o inputRange estritamente crescente.
  let opacity = 1;
  if (durationInFrames > 2) {
    const fade = Math.min(6, Math.floor((durationInFrames - 1) / 2));
    opacity = interpolate(
      frame,
      [0, fade, durationInFrames - fade, durationInFrames],
      [0, 1, 1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }

  const scale = layer.pop
    ? interpolate(frame, [0, 8], [0.92, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;

  return (
    <Img
      src={staticFile(layer.asset)}
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        left: 0,
        right: 0,
        width: "100%",
        height: fullFrame ? "100%" : "auto",
        objectFit: "contain",
        margin: "auto",
        opacity,
        transform: `scale(${scale})`,
      }}
    />
  );
};

const Scene = ({ scene, fps, width, height }) => (
  <Sequence
    from={Math.round(scene.start * fps)}
    durationInFrames={Math.max(1, Math.round((scene.end - scene.start) * fps))}
  >
    {scene.layers.map((layer, i) => {
      if (layer.type !== "clip" && layer.type !== "card") return null;

      const start = layer.start ?? scene.start;
      const end = layer.end ?? scene.end;
      const durationInFrames = Math.max(1, Math.round((end - start) * fps));

      return (
        <Sequence
          key={i}
          from={Math.max(0, Math.round((start - scene.start) * fps))}
          durationInFrames={durationInFrames}
        >
          {layer.type === "clip" ? (
            <ClipLayer layer={layer} width={width} height={height} fps={fps} />
          ) : (
            <CardLayer layer={layer} durationInFrames={durationInFrames} />
          )}
        </Sequence>
      );
    })}
  </Sequence>
);

export const Storyboard = ({ timeline, subs = [], lowerThirds = [], fps, width, height, fontSize = 32 }) => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    {(timeline?.scenes ?? []).map((scene, i) => (
      <Scene key={scene.id ?? i} scene={scene} fps={fps} width={width} height={height} />
    ))}
    <Captions
      subs={subs}
      lowerThirds={lowerThirds}
      fps={fps}
      width={width}
      height={height}
      fontSize={fontSize}
    />
  </AbsoluteFill>
);
