import { MarketOverview } from "../MarketOverview";
import { MarketSignals } from "../MarketSignals";

export function OverviewRoute({
  panelStates,
  ...props
}) {
  return (
    <>
      <MarketOverview {...props} panelState={panelStates.overview} />
      <MarketSignals {...props} panelState={panelStates.signals} />
    </>
  );
}
