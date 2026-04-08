import type { ApiEnvelope } from "@/types";

const rawOrigin = import.meta.env.VITE_API_URL || window.location.origin;

export const API_ORIGIN = rawOrigin.replace(/\/api$/, "").replace(/\/$/, "");
export const API_BASE = rawOrigin.includes("/api")
  ? rawOrigin.replace(/\/$/, "")
  : `${API_ORIGIN}/api`;

const unwrapPayload = <T>(payload: unknown): T => {
  if (!payload || typeof payload !== "object") {
    return payload as T;
  }

  const maybeEnvelope = payload as ApiEnvelope<T>;
  if (typeof maybeEnvelope.code === "number" && "data" in maybeEnvelope) {
    if (maybeEnvelope.code !== 0) {
      throw new Error(maybeEnvelope.msg || "请求失败");
    }
    return maybeEnvelope.data;
  }

  return payload as T;
};

const parseError = (payload: unknown, fallback: string) => {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const msg = "msg" in payload ? payload.msg : undefined;
  const detail = "detail" in payload ? payload.detail : undefined;

  if (typeof msg === "string" && msg.trim()) {
    return msg;
  }

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  return fallback;
};

export const apiRequest = async <T>(path: string, options: RequestInit = {}) => {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(parseError(payload, response.statusText || "请求失败"));
  }

  return unwrapPayload<T>(payload ?? {});
};

export const apiGet = <T>(path: string) => apiRequest<T>(path);

export const apiPost = <T>(path: string, body?: unknown) =>
  apiRequest<T>(path, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const apiPut = <T>(path: string, body?: unknown) =>
  apiRequest<T>(path, {
    method: "PUT",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const apiDelete = <T>(path: string) =>
  apiRequest<T>(path, {
    method: "DELETE",
  });

export const apiUpload = <T>(path: string, file: File, fieldName = "file") => {
  const formData = new FormData();
  formData.append(fieldName, file);

  return apiRequest<T>(path, {
    method: "POST",
    body: formData,
  });
};

export const buildWsUrl = (path: string, params: Record<string, string>) => {
  const url = new URL(path, API_ORIGIN);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";

  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });

  return url.toString();
};

export const resolveAssetUrl = (path: string) => {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  return `${API_ORIGIN}${path.startsWith("/") ? path : `/${path}`}`;
};
