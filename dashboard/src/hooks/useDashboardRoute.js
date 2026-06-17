import { useCallback, useEffect, useState } from "react";

const ROUTE_PATHS = {
  overview: "/",
  ticker: "/ticker",
  watchlist: "/watchlist",
  observability: "/observability",
};

const PATH_ROUTES = Object.entries(ROUTE_PATHS).reduce((acc, [route, path]) => {
  acc[path] = route;
  return acc;
}, {});

function normalizePathname(pathname) {
  if (!pathname || pathname === "/") {
    return "/";
  }

  return pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
}

function readLocation() {
  if (typeof window === "undefined") {
    return {
      route: "overview",
      pathname: ROUTE_PATHS.overview,
      query: {},
    };
  }

  const url = new URL(window.location.href);
  const pathname = normalizePathname(url.pathname);
  return {
    route: PATH_ROUTES[pathname] || "overview",
    pathname,
    query: Object.fromEntries(url.searchParams.entries()),
  };
}

function buildUrl(pathname, query) {
  const searchParams = new URLSearchParams();
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }

    searchParams.set(key, String(value));
  });

  const search = searchParams.toString();
  return `${pathname}${search ? `?${search}` : ""}`;
}

export function useDashboardRoute() {
  const [locationState, setLocationState] = useState(readLocation);

  useEffect(() => {
    function handleLocationChange() {
      setLocationState(readLocation());
    }

    window.addEventListener("popstate", handleLocationChange);
    return () => window.removeEventListener("popstate", handleLocationChange);
  }, []);

  const commitLocation = useCallback((pathname, query, replace = false) => {
    if (typeof window === "undefined") {
      return;
    }

    const nextUrl = buildUrl(pathname, query);
    const currentUrl = `${window.location.pathname}${window.location.search}`;
    if (nextUrl === currentUrl) {
      setLocationState(readLocation());
      return;
    }

    window.history[replace ? "replaceState" : "pushState"]({}, "", nextUrl);
    setLocationState(readLocation());
  }, []);

  const navigate = useCallback(
    (route, options = {}) => {
      const pathname = ROUTE_PATHS[route] || ROUTE_PATHS.overview;
      const nextQuery =
        options.query === undefined ? locationState.query : options.query;
      commitLocation(pathname, nextQuery, options.replace);
    },
    [commitLocation, locationState.query],
  );

  const setQueryParams = useCallback(
    (updates, options = {}) => {
      const nextQuery = { ...locationState.query };
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined || value === null || value === "") {
          delete nextQuery[key];
          return;
        }

        nextQuery[key] = String(value);
      });

      commitLocation(locationState.pathname, nextQuery, options.replace ?? true);
    },
    [commitLocation, locationState.pathname, locationState.query],
  );

  return {
    route: locationState.route,
    query: locationState.query,
    navigate,
    setQueryParams,
  };
}
