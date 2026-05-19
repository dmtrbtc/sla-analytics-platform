import { create } from "zustand";

interface DemoModeState {
  enabled: boolean;
  toggle: () => void;
  enable: () => void;
  disable: () => void;
}

export const useDemoMode = create<DemoModeState>((set) => ({
  enabled: false,
  toggle: () => set((s) => ({ enabled: !s.enabled })),
  enable: () => set({ enabled: true }),
  disable: () => set({ enabled: false }),
}));
