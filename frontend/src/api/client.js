/**
 * NexAbility Core API Client
 * Centralized HTTP client supporting GET, POST, PATCH, PUT, DELETE
 * with standard response/error envelope handling, Bearer token injection,
 * automatic token refresh retry, 204 No-Content handling, and in-memory token security.
 */

export class ApiError extends Error {
  constructor(
    message,
    status,
    data = null,
    validationErrors = null,
    isProxyError = false,
    isNetworkError = false
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    this.validationErrors = validationErrors;
    this.isProxyError = isProxyError;
    this.isNetworkError = isNetworkError;
  }
}

// In-memory token storage (NEVER stored in localStorage or sessionStorage for security)
let inMemoryAccessToken = null;
let inMemoryRefreshToken = null;

// Concurrency lock for refresh requests to prevent multiple simultaneous refresh calls
let activeRefreshPromise = null;
let refreshHandler = null;

export const tokenStore = {
  getAccessToken: () => inMemoryAccessToken,
  setAccessToken: (token) => {
    inMemoryAccessToken = token;
  },
  getRefreshToken: () => inMemoryRefreshToken,
  setRefreshToken: (token) => {
    inMemoryRefreshToken = token;
  },
  clearTokens: () => {
    inMemoryAccessToken = null;
    inMemoryRefreshToken = null;
  },
  hasTokens: () => Boolean(inMemoryAccessToken || inMemoryRefreshToken),
  registerRefreshHandler: (handler) => {
    refreshHandler = handler;
  },
  executeRefresh: async () => {
    if (!refreshHandler) {
      throw new Error("No refresh handler registered.");
    }
    if (activeRefreshPromise) {
      return activeRefreshPromise;
    }
    activeRefreshPromise = (async () => {
      try {
        const result = await refreshHandler();
        return result;
      } finally {
        activeRefreshPromise = null;
      }
    })();
    return activeRefreshPromise;
  },
};

/**
 * Normalizes and formats FastAPI / Pydantic validation error arrays
 */
function formatValidationErrors(detail) {
  if (Array.isArray(detail)) {
    return detail.map((err) => {
      const field = Array.isArray(err.loc) ? err.loc.slice(1).join(".") : "field";
      return {
        field: field || "input",
        message: err.msg || "Invalid value",
        type: err.type,
      };
    });
  }
  return null;
}

/**
 * Returns a user-friendly message for common HTTP status codes
 */
function getDefaultErrorMessage(status) {
  switch (status) {
    case 400:
      return "Invalid request. Please check the information provided.";
    case 401:
      return "Authentication required. Please sign in with valid credentials.";
    case 403:
      return "Access denied. You do not have permission to perform this action.";
    case 404:
      return "The requested resource could not be found.";
    case 409:
      return "A conflict occurred. This record or email may already exist.";
    case 422:
      return "Validation failed. Please correct the highlighted errors.";
    case 429:
      return "Too many requests. Please wait a moment before trying again.";
    case 500:
    case 502:
    case 503:
    case 504:
      return "The server encountered an error. Please try again later.";
    default:
      return `Request failed with status ${status}.`;
  }
}

/**
 * Resolves the API base URL from import.meta.env.VITE_API_BASE_URL
 * Defaults to '/api/v1' if not defined or if using the local Vite proxy.
 */
export function getApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string") {
    // Strip trailing slash if present
    return envUrl.trim().replace(/\/+$/, "");
  }
  return "/api/v1";
}

/**
 * Builds the complete request URL while preventing duplicate /api/v1 or /api prefixes.
 */
export function buildApiUrl(endpoint) {
  const baseUrl = getApiBaseUrl();
  let normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  // Prevent duplicate /api/v1 or /api prefix when both baseUrl and endpoint include it
  if (baseUrl.endsWith("/api/v1")) {
    if (normalizedEndpoint.startsWith("/api/v1/")) {
      normalizedEndpoint = normalizedEndpoint.slice("/api/v1".length);
    } else if (normalizedEndpoint === "/api/v1") {
      normalizedEndpoint = "";
    }
  } else if (baseUrl.endsWith("/api")) {
    if (normalizedEndpoint.startsWith("/api/")) {
      normalizedEndpoint = normalizedEndpoint.slice("/api".length);
    } else if (normalizedEndpoint === "/api") {
      normalizedEndpoint = "";
    }
  }

  return `${baseUrl}${normalizedEndpoint}`;
}

/**
 * Central request dispatcher with automatic token injection and 401 refresh retry
 */
async function request(endpoint, options = {}) {
  const {
    method = "GET",
    body = null,
    headers = {},
    requiresAuth = false,
    responseType = "json",
    _isRetry = false,
    ...customOptions
  } = options;

  const url = buildApiUrl(endpoint);

  const requestHeaders = {
    Accept: responseType === "blob" ? "*/*" : "application/json",
    // Ngrok free tunnels show an interstitial page unless this header is present
    "ngrok-skip-browser-warning": "true",
    ...headers,
  };

  if (body !== null && !(body instanceof FormData)) {
    requestHeaders["Content-Type"] = "application/json";
  }

  // Attach Bearer token to authenticated requests
  if (requiresAuth) {
    const token = tokenStore.getAccessToken();
    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }
  }

  const fetchOptions = {
    method,
    headers: requestHeaders,
    // Support backend refresh-cookie policy
    credentials: "include",
    ...customOptions,
  };

  if (body !== null) {
    fetchOptions.body = body instanceof FormData ? body : JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (networkError) {
    throw new ApiError(
      `Network error: Failed to connect to server (${networkError.message || "Network request failed"}). Please check your connection.`,
      0,
      { originalError: networkError.message },
      null,
      false, // isProxyError
      true // isNetworkError
    );
  }

  // Handle 401 Unauthorized for authenticated requests: attempt single token refresh retry
  if (
    response.status === 401 &&
    requiresAuth &&
    !_isRetry &&
    tokenStore.getRefreshToken()
  ) {
    try {
      await tokenStore.executeRefresh();
      // Retry request with updated token and _isRetry guard
      return await request(endpoint, {
        ...options,
        _isRetry: true,
      });
    } catch {
      tokenStore.clearTokens();
      // Continue to let standard error handler process the 401
    }
  }

  // Handle HTTP 204 No Content
  if (response.status === 204) {
    return null;
  }

  // Handle binary/blob response when response.ok and responseType === "blob"
  if (response.ok && responseType === "blob") {
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition");
    let filename = "download";
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename, mimeType: response.headers.get("content-type") || blob.type };
  }

  // Parse JSON response or fallback to empty object / text
  let responseData = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      responseData = await response.json();
    } catch {
      // Keep responseData as null
    }
  } else {
    try {
      const text = await response.text();
      if (text) {
        responseData = { raw: text };
      }
    } catch {
      // Keep responseData as null
    }
  }

  // Handle error responses
  if (!response.ok) {
    const isProxyError =
      response.headers.get("x-proxy-error") === "true" ||
      response.status === 502 ||
      response.status === 504;

    let errorMessage = "";
    let validationErrors = null;

    if (responseData) {
      if (typeof responseData.detail === "string") {
        errorMessage = responseData.detail;
      } else if (Array.isArray(responseData.detail)) {
        validationErrors = formatValidationErrors(responseData.detail);
        if (validationErrors && validationErrors.length > 0) {
          errorMessage = validationErrors.map((v) => `${v.field}: ${v.message}`).join(", ");
        }
      } else if (typeof responseData.message === "string") {
        errorMessage = responseData.message;
      } else if (typeof responseData.error === "string") {
        errorMessage = responseData.error;
      } else if (responseData.raw && typeof responseData.raw === "string") {
        errorMessage = responseData.raw;
      }
    }

    if (!errorMessage) {
      if (isProxyError) {
        errorMessage = `Proxy error (${response.status}): Failed to connect to backend service via Vite proxy.`;
      } else {
        errorMessage = getDefaultErrorMessage(response.status);
      }
    }

    throw new ApiError(
      errorMessage,
      response.status,
      responseData,
      validationErrors,
      isProxyError,
      false
    );
  }

  return responseData;
}

export const apiClient = {
  get: (endpoint, options = {}) => request(endpoint, { ...options, method: "GET" }),
  post: (endpoint, body, options = {}) => request(endpoint, { ...options, method: "POST", body }),
  patch: (endpoint, body, options = {}) => request(endpoint, { ...options, method: "PATCH", body }),
  put: (endpoint, body, options = {}) => request(endpoint, { ...options, method: "PUT", body }),
  delete: (endpoint, options = {}) => request(endpoint, { ...options, method: "DELETE" }),
  download: (endpoint, options = {}) =>
    request(endpoint, { ...options, method: "GET", responseType: "blob" }),
  buildApiUrl,
  tokenStore,
};

export default apiClient;
