import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { Captions } from "./Captions.jsx";

export const Legendas = (props) => {
  const { subs = [], lowerThirds = [], fps, width, height, fontSize, clip } = props;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <OffthreadVideo muted src={staticFile(clip)} style={{ width, height, objectFit: "contain" }} />
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
};
