import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { favoritesApi, type FavoriteQueue } from "../api/favorites";

interface FavoritesCtx {
  favorites: FavoriteQueue[];
  favoriteSet: Set<string>;
  loading: boolean;
  isStarred: (queue: string) => boolean;
  toggle: (queue: string) => Promise<void>;
  refresh: () => Promise<void>;
  /** When non-empty, dashboards/forensics should filter to these queue_names. */
  activeFilter: string[];
  setActiveFilter: (queues: string[]) => void;
  enableFavoritesOnly: boolean;
  setEnableFavoritesOnly: (b: boolean) => void;
}

const Ctx = createContext<FavoritesCtx | null>(null);

const FAVORITES_ONLY_KEY = "sla.favoritesOnly";
const ACTIVE_FILTER_KEY = "sla.activeQueueFilter";

export function FavoritesProvider({ children }: { children: React.ReactNode }) {
  const [favorites, setFavorites] = useState<FavoriteQueue[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, _setActiveFilter] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(ACTIVE_FILTER_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  });
  const [enableFavoritesOnly, _setEnableFavoritesOnly] = useState<boolean>(() => {
    return localStorage.getItem(FAVORITES_ONLY_KEY) === "1";
  });

  const setActiveFilter = useCallback((queues: string[]) => {
    _setActiveFilter(queues);
    try { localStorage.setItem(ACTIVE_FILTER_KEY, JSON.stringify(queues)); }
    catch {}
  }, []);

  const setEnableFavoritesOnly = useCallback((b: boolean) => {
    _setEnableFavoritesOnly(b);
    localStorage.setItem(FAVORITES_ONLY_KEY, b ? "1" : "0");
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const d = await favoritesApi.list();
      setFavorites(d.queues || []);
    } catch (e) {
      // 401/403 — silently empty; logged-out users have no favorites
      setFavorites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // If "favorites only" mode is on, keep activeFilter synced to favorite list.
  useEffect(() => {
    if (enableFavoritesOnly) {
      const list = favorites.map(f => f.queue_name);
      _setActiveFilter(list);
      try { localStorage.setItem(ACTIVE_FILTER_KEY, JSON.stringify(list)); } catch {}
    }
  }, [enableFavoritesOnly, favorites]);

  const favoriteSet = useMemo(() => new Set(favorites.map(f => f.queue_name)), [favorites]);

  const isStarred = useCallback((q: string) => favoriteSet.has(q), [favoriteSet]);

  const toggle = useCallback(async (queue: string) => {
    const has = favoriteSet.has(queue);
    // Optimistic update so the star UI flips instantly.
    if (has) {
      setFavorites(prev => prev.filter(f => f.queue_name !== queue));
      try { await favoritesApi.unstar(queue); }
      catch { await refresh(); /* roll back to server truth */ }
    } else {
      const optimistic: FavoriteQueue = {
        queue_name: queue,
        position: favorites.length + 1,
        starred_at: new Date().toISOString(),
      };
      setFavorites(prev => [...prev, optimistic]);
      try { await favoritesApi.star(queue); }
      catch { await refresh(); }
    }
  }, [favoriteSet, favorites.length, refresh]);

  const value: FavoritesCtx = {
    favorites, favoriteSet, loading, isStarred, toggle, refresh,
    activeFilter, setActiveFilter,
    enableFavoritesOnly, setEnableFavoritesOnly,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFavorites(): FavoritesCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useFavorites must be used inside FavoritesProvider");
  return v;
}
