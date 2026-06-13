import { NewsPanel } from "../NewsPanel";
import { TickerWorkspace } from "../TickerWorkspace";

export function TickerRoute({
  panelStates,
  ...props
}) {
  return (
    <>
      <TickerWorkspace {...props} panelState={panelStates.ticker} />
      <NewsPanel {...props} panelState={panelStates.news} />
    </>
  );
}
