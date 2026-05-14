import client from "./client";

export const authApi = {
  login: (email: string, password: string) =>
    client.post("/auth/login", { email, password }),
  refresh: (refreshToken: string) =>
    client.post("/auth/refresh", { refresh_token: refreshToken }),
  me: () => client.get("/auth/me"),
  logout: () => client.post("/auth/logout"),
  listUsers: (limit = 100, offset = 0) =>
    client.get("/auth/users", { params: { limit, offset } }),
  createUser: (data: {
    email: string;
    display_name: string;
    password: string;
    role: string;
  }) => client.post("/auth/users", data),
  updateUser: (
    id: string,
    data: {
      email?: string;
      display_name?: string;
      password?: string;
      role?: string;
      is_active?: boolean;
    }
  ) => client.put(`/auth/users/${id}`, data),
  deleteUser: (id: string) => client.delete(`/auth/users/${id}`),
};
