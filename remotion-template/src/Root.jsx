import { Composition } from "remotion";
import { Legendas } from "./Legendas.jsx";
import { Storyboard } from "./Storyboard.jsx";

export const Root = () => (
  <>
    <Composition
      id="Legendas"
      component={Legendas}
      durationInFrames={1}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{
        clip: "clip.mp4",
        durationS: 5,
        fps: 30,
        width: 1280,
        height: 720,
        fontSize: 32,
        subs: [],
        lowerThirds: [],
      }}
      calculateMetadata={({ props }) => ({
        durationInFrames: Math.max(1, Math.round(props.durationS * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
    <Composition
      id="Storyboard"
      component={Storyboard}
      durationInFrames={1}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{
        timeline: { fps: 30, total_s: 1, scenes: [] },
        subs: [],
        lowerThirds: [],
        durationS: 5,
        fps: 30,
        width: 1280,
        height: 720,
        fontSize: 32,
      }}
      calculateMetadata={({ props }) => ({
        durationInFrames: Math.max(1, Math.round(props.durationS * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
  </>
);
