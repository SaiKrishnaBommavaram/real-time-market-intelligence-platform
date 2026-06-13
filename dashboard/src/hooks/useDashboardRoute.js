import { useEffect, useState } from "react";

const DEFAULT_ROUTE = "overview";
const VALID_ROUTES = new Set(["overview", "ticker", "watchlist", "observability"]);

function getRouteFromHash() {
  if (typeof window === "undefined") {
    return DEFAULT_ROUTE;
  }

  const rawHash = window.location.hash.replace(/^#\/?/, "").trim();
  if (!rawHash) {
    return DEFAULT_ROUTE;
  }

  return VALID_ROUTES.has(rawHash) ? rawHash : DEFAULT_ROUTE;
}

export function useDashboardRoute() {
  const [route, setRoute] = useState(getRouteFromHash);

  useEffect(() => {
    function syncRoute() {
      setRoute(getRouteFromHash());
    }

    window.addEventListener("hashchange", syncRoute);
    syncRoute();

    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  function navigate(nextRoute) {
    const safeRoute = VALID_ROUTES.has(nextRoute) ? nextRoute : DEFAULT_ROUTE;
    if (typeof window !== "undefined") {
      window.location.hash = `/${safeRoute}`;
    }
    setRoute(safeRoute);
  }

  return { route, navigate };
}
