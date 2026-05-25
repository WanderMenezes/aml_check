import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const auth = window.localStorage.getItem("aml-auth");
    const locale = window.localStorage.getItem("aml-locale") || "pt";
    if (auth) {
      const parsed = JSON.parse(auth);
      config.headers.Authorization = `Bearer ${parsed.access}`;
    }
    config.headers["Accept-Language"] = locale;
    config.headers["X-Requested-With"] = "XMLHttpRequest";
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as typeof error.config & { _retry?: boolean };
    if (!original || typeof window === "undefined" || error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    const auth = window.localStorage.getItem("aml-auth");
    if (!auth) {
      window.location.href = "/session-expired";
      return Promise.reject(error);
    }

    try {
      original._retry = true;
      const parsed = JSON.parse(auth);
      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh: parsed.refresh });
      const nextAuth = { ...parsed, access: data.access, session_key: data.session_key };
      window.localStorage.setItem("aml-auth", JSON.stringify(nextAuth));
      original.headers = original.headers ?? {};
      original.headers.Authorization = `Bearer ${data.access}`;
      return api(original);
    } catch (refreshError) {
      window.localStorage.removeItem("aml-auth");
      window.location.href = "/session-expired";
      return Promise.reject(refreshError);
    }
  }
);
