import { useQuery } from "@tanstack/react-query";
import { authApi } from "../api/auth";
import { useAuthStore } from "../stores/authStore";

export function useAuth() {
  const { token, user, setAuth, setUser, logout, refreshToken } = useAuthStore();

  const { data: userData, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const resp = await authApi.me();
      return resp.data;
    },
    enabled: !!token,
    retry: false,
    onSuccess: (data: any) => {
      setUser(data);
    },
    onError: () => {
      if (!navigator.onLine) return;
      const rt = localStorage.getItem("refresh_token");
      if (!rt) {
        logout();
      }
    },
  } as any);

  return {
    token,
    refreshToken,
    user: user || userData,
    isAuthenticated: !!token,
    isLoading: !!token && isLoading && !user,
    setAuth,
    logout,
  };
}
