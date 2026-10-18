"use strict";

/**
 * OmniSight API client for frontend-backend communication.
 *
 * Manages HTTP requests, error handling, and maintains configuration
 * for API endpoints. Operates in both demo mode (for development/testing)
 * and live mode (when a backend is available).
 */

// API base URL configuration
const API_BASE_URL = (() => {
  const envBase = typeof process !== "undefined" && process.env && process.env.OMNISIGHT_API_BASE_URL;
  const globalConfig = typeof window !== "undefined" && window.OmniSightAPIConfig && window.OmniSightAPIConfig.baseUrl;
  return envBase || globalConfig || "https://your-backend-domain.com/api"; // Default fallback for production
})();

// API client configuration
const DEFAULT_TIMEOUT_MS = 15000;
const DEMO_LATENCY_MS = 600; // Simulate network delay for demo mode

/**
 * Standardized error class for API-related issues.
 */
class ApiError extends Error {
  constructor(message, status = null, response = null, networkError = false) {
    super(message);
    this.name = "ApiError";
    this.status = status; // HTTP status code or null
    this.response = response; // The raw response object for inspection
    this.networkError = networkError; // Whether this is a network-level error
  }
}

/**
 * Universal request handler that supports both demo and live modes.
 * In demo mode, responses are generated from local fixtures with a simulated delay.
 * In live mode, it performs actual HTTP requests using the Fetch API.
 */
class ApiClient {
  constructor(baseUrl = API_BASE_URL, timeout = DEFAULT_TIMEOUT_MS) {
  this.baseUrl = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  this.timeout = timeout;
}
  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    // Handle live mode
    try {
      const headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        ...options.headers
      };

      const response = await fetch(url, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
        credentials: "same-origin" // Use same-origin for cookies/auth if needed
      });

      const contentType = response.headers.get("content-type");
      let data;

      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        // Handle non-JSON responses gracefully
        const text = await response.text();
        data = text ? { message: text, raw: text } : {};
      }

      if (!response.ok) {
        throw new ApiError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          response,
          false
        );
      }

      return data;
    } catch (error) {
      // Enhanced error handling for network and abort errors
      if (error.name === "AbortError" || error.name === "TimeoutError") {
        throw new ApiError("Request timed out", null, null, true);
      }

      if (error instanceof ApiError) throw error;

      // Network or other unexpected errors
      throw new ApiError(
        `Network error: ${error.message}`,
        null,
        null,
        true
      );
    } finally {
      clearTimeout(timeoutId);
    }
  }

  _normalizeDemoResponse(path, fixture) {
    // Convert fixture data into a realistic API response structure
    switch (path) {
      case "/dashboard":
        return {
          total_scans: fixture.total_scans,
          issues_found: fixture.issues_found,
          verified_resolved: fixture.verified_resolved,
          needs_attention: fixture.needs_attention,
          last_updated: fixture.last_updated
        };

      case "/scans":
        return Array.isArray(fixture) ? fixture : (fixture.items || []);

      case "/issues":
        return Array.isArray(fixture) ? fixture.map(i => ({
          ...i,
          // Ensure consistent field names for both demo and live modes
          id: i.id || i.issue_id || `OS-${String(i.id || Math.floor(Math.random() * 1000)).padStart(3, "0")}`,
          title: i.title || i.issue_title || "Untitled issue",
          type: i.type || i.issue_type || "Unknown",
          viewport: i.viewport || i.viewport_size || "Unknown",
          severity: i.severity || "Medium",
          state: i.state || i.verification_state || "detected",
          scan_id: i.scan_id || i.scan || null,
          verified: i.verified || i.verified || false
        })) : [];

      case "/targets":
        return Array.isArray(fixture) ? fixture.map(t => ({
          id: t.id || t.target_id || `target_${t.id}`,
          name: t.name || t.label || "Unnamed target"
        })) : [];

      default:
        return fixture;
    }
  }

  // API method shortcuts

  async dashboard() {
    return this.request("/dashboard");
  }

  async scans() {
    return this.request("/scans");
  }
  async scan(id) {
    return this.request(`/scans/${id}`);
  }

  async issues() {
    return this.request("/issues");
  }
  async issue(id) {
    return this.request(`/issues/${id}`);
  }

  async targets() {
    return this.request("/targets");
 }

  async createScan(payload) {
    return this.request("/scans", {
      method: "POST",
      body: payload
    });
 }

  async approveFix(id) {
    return this.request("/approve_fix", {
      method: "POST",
      body: { issue_id: id }
    });
 }

  async rejectFix(id) {
    return this.request("/reject_fix", {
      method: "POST",
      body: { issue_id: id }
    });
 }

  async verifyFix(id) {
    return this.request("/verify_fix", {
      method: "POST",
      body: { issue_id: id }
    });
 }
  // Method to override base URL (useful for testing)
  setBaseUrl(url) {
    this.baseUrl = url.endsWith("/") ? url.slice(0, -1) : url;
  }
}

// Singleton instance for use throughout the application
const OmniSightAPI = new ApiClient();

// Make the API instance and error class available globally for inspection
if (typeof window !== "undefined") {
  window.OmniSightAPI = OmniSightAPI;
  window.ApiError = ApiError;
}
