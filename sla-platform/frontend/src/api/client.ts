import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  // FastAPI expects `?queue=A&queue=B` for List[str] query params.
  // Axios default serialization (`queue[]=A`) breaks server-side parsing.
  paramsSerializer: {
    serialize: (params) => {
      const usp = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null) continue;
        if (Array.isArray(v)) {
          v.forEach((item) => usp.append(k, String(item)));
        } else {
          usp.append(k, String(v));
        }
      }
      return usp.toString();
    },
  },
});

let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const resp = await axios.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
        const { access_token, refresh_token: new_refresh } = resp.data;

        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", new_refresh);

        pendingRequests.forEach((cb) => cb(access_token));
        pendingRequests = [];

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return client(originalRequest);
      } catch {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default client;
