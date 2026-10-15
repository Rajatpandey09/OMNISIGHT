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
    this.demoMode = this._isDemoMode();
    this._fixtureRegistry = new Map(); // In-memory fixture storage for demo mode
    this._initDemoFixtures(); // Seed with default fixtures
  }

  _isDemoMode() {
    // Check demo mode flag from DOM or environment
    if (typeof window !== "undefined") {
      const demoToggle = document.getElementById("demoMode");
      if (demoToggle) return demoToggle.checked;
      if (window.OmniSightConfig && typeof window.OmniSightConfig.demoMode === "boolean") {
        return window.OmniSightConfig.demoMode;
      }
    }
    // Fallback to environment variable or default to false for production
    if (typeof process !== "undefined" && process.env && typeof process.env.OMNISIGHT_DEMO === "boolean") {
      return process.env.OMNISIGHT_DEMO;
    }
    return false;
  }

  _initDemoFixtures() {
    // Register demo fixtures for various endpoints
    this._fixtureRegistry.set("/dashboard", {
      total_scans: 14,
      issues_found: 8,
      verified_resolved: 3,
      needs_attention: 5,
      last_updated: "2026-10-14T09:30:00Z"
    });

    this._fixtureRegistry.set("/scans", [
      { id: "DEMO-014", target: "shop.demo.local", started_at: "2026-10-14T10:42:00Z", viewports: ["Desktop", "Mobile"], status: "completed", issue_count: 4 },
      { id: "DEMO-013", target: "docs.demo.local", started_at: "2026-10-13T16:18:00Z", viewports: ["Desktop"], status: "completed", issue_count: 2 },
      { id: "DEMO-012", target: "landing.demo.local", started_at: "2026-10-12T14:00:00Z", viewports: ["Mobile"], status: "partial", issue_count: 3 }
    ]);

    this._fixtureRegistry.set("/issues", [
      { id: "OS-101", title: "Primary action overlaps sticky footer", type: "Layout", viewport: "Mobile", severity: "High", state: "proposed", scan_id: "DEMO-014", verified: false },
      { id: "OS-102", title: "Hero media exceeds content width", type: "Layout", viewport: "Mobile", severity: "Medium", state: "detected", scan_id: "DEMO-014", verified: false },
      { id: "OS-103", title: "Secondary action has weak contrast", type: "Accessibility", viewport: "Desktop", severity: "High", state: "proposed", scan_id: "DEMO-013", verified: false },
      { id: "OS-104", title: "Product cards use inconsistent corner radius", type: "Visual", viewport: "Desktop", severity: "Low", state: "applied", scan_id: "DEMO-013", verified: true },
      { id: "OS-105", title: "Horizontal page scrolling at 390px", type: "Layout", viewport: "Mobile", severity: "High", state: "inconclusive", scan_id: "DEMO-012", verified: false },
      { id: "OS-106", title: "Form submit control is not visible", type: "Visibility", viewport: "Desktop", severity: "Medium", state: "failed", scan_id: "DEMO-012", verified: false }
    ]);

    this._fixtureRegistry.set("/targets", [
      { id: "demo-overflow", name: "Demo target — mobile overflow" },
      { id: "demo-hidden", name: "Demo target — hidden control" },
      { id: "demo-standard", name: "Demo target — standard layout" }
    ]);

    // Register action-specific fixtures
    this._fixtureRegistry.set("/approve_fix", { success: true, issue_id: "OS-101", verification: "applied" });
    this._fixtureRegistry.set("/reject_fix", { success: true, issue_id: "OS-102", verification: "detected" });
    this._fixtureRegistry.set("/verify_fix", { success: true, issue_id: "OS-103", verification: "verified" });
  }

  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    // Handle demo mode
    if (this.demoMode) {
      clearTimeout(timeoutId);
      await new Promise(resolve => setTimeout(resolve, DEMO_LATENCY_MS));
      const fixture = this._fixtureRegistry.get(path) || this._fixtureRegistry.get("/default") || {};
      return this._normalizeDemoResponse(path, fixture);
    }

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

  // Utility method to switch demo mode
  setDemoMode(enabled) {
    this.demoMode = enabled;
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
