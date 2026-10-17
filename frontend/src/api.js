/**
 * MediTrack API Client
 * Automatically attaches RBAC headers and captures caching telemetry.
 */

let activeUser = {
  name: "Nurse Sarah Jenkins",
  role: "CLINIC_STAFF",
  clinicId: "branch-central"
};

let cacheTelemetryListeners = [];

export function setActiveUser(user) {
  activeUser = { ...activeUser, ...user };
}

export function getActiveUser() {
  return activeUser;
}

export function subscribeToCacheEvents(callback) {
  cacheTelemetryListeners.push(callback);
  return () => {
    cacheTelemetryListeners = cacheTelemetryListeners.filter(cb => cb !== callback);
  };
}

function notifyCacheEvent(event) {
  cacheTelemetryListeners.forEach(cb => cb(event));
}

async function request(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-User-Role": activeUser.role,
    "X-User-Name": activeUser.name,
    "X-Clinic-ID": activeUser.clinicId,
    ...(options.headers || {})
  };

  const startTime = performance.now();
  const res = await fetch(url, { ...options, headers });
  const clientLatency = Math.round(performance.now() - startTime);

  const cacheStatus = res.headers.get("X-Cache") || "NONE";
  const serverTime = res.headers.get("X-Response-Time-ms");
  const cacheKey = res.headers.get("X-Cache-Key") || "";

  notifyCacheEvent({
    url,
    cacheStatus,
    clientLatencyMs: clientLatency,
    serverTimeMs: serverTime ? parseFloat(serverTime) : clientLatency,
    cacheKey,
    timestamp: new Date().toLocaleTimeString()
  });

  if (!res.ok) {
    let errorDetail = "Request failed";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch (e) {
      errorDetail = await res.text();
    }
    const err = new Error(errorDetail);
    err.status = res.status;
    throw err;
  }

  // Handle blob or json
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await res.json();
  }
  return res;
}

export const api = {
  async getAppointments({ clinicId, date, status, riskTier, search }) {
    const params = new URLSearchParams();
    if (clinicId) params.append("clinic_id", clinicId);
    if (date) params.append("date", date);
    if (status && status !== "ALL") params.append("status", status);
    if (riskTier && riskTier !== "ALL") params.append("risk_tier", riskTier);
    if (search) params.append("search", search);
    return await request(`/api/v1/appointments?${params.toString()}`);
  },

  async createAppointment(appointmentData) {
    return await request("/api/v1/appointments", {
      method: "POST",
      body: JSON.stringify(appointmentData)
    });
  },

  async reconcileAppointment(id, { status, notes }) {
    return await request(`/api/v1/appointments/${id}/reconcile`, {
      method: "PATCH",
      body: JSON.stringify({ status, notes })
    });
  },

  async getDailySummary(clinicId, date) {
    const params = new URLSearchParams();
    if (clinicId) params.append("clinic_id", clinicId);
    if (date) params.append("date", date);
    return await request(`/api/v1/reports/daily-summary?${params.toString()}`);
  },

  async getCacheStats() {
    return await request("/api/v1/cache/stats");
  },

  async clearCache() {
    return await request("/api/v1/cache/clear", {
      method: "POST"
    });
  },

  async getModelMetrics() {
    return await request("/api/v1/model/metrics");
  },

  async retrainModel() {
    return await request("/api/v1/model/retrain", {
      method: "POST"
    });
  },

  async predictAdHoc(features) {
    return await request("/api/v1/appointments/predict", {
      method: "POST",
      body: JSON.stringify(features)
    });
  },

  async getAuditLogs(limit = 40) {
    return await request(`/api/v1/audit/logs?limit=${limit}`);
  },

  async seedDemoAppointments(clinicId = "branch-central") {
    return await request(`/api/v1/appointments/batch-seed?clinic_id=${clinicId}`, {
      method: "POST"
    });
  },

  getExportCsvUrl(clinicId, date) {
    const params = new URLSearchParams();
    if (clinicId) params.append("clinic_id", clinicId);
    if (date) params.append("date", date);
    return `/api/v1/reports/export?${params.toString()}`;
  }
};
