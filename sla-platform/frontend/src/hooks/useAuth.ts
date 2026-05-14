import { useQuery } from "@tanstack/react-query";
import { authApi } from "../api/auth";
import { useAuthStore } from "../stores/authStore";

export function useAuth() {
  const { token, user, setAuth, logout } = useAuthStore();

  const { data: userData } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
    enabled: !!token,
  });

  return {
    token,
    user: user || userData?.user,
    isAuthenticated: !!token,
    setAuth,
    logout,
  };
}
