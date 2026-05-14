import client from "./client";

export const authApi = {
  login: (email: string, password: string) =>
    client.post("/auth/login", { email, password }),
  refresh: () => client.post("/auth/refresh"),
  me: () => client.get("/auth/me"),
};
