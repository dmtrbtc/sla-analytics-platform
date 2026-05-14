import { create } from "zustand";

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("access_token"),
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("access_token", token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("access_token");
    set({ token: null, user: null });
  },
}));
