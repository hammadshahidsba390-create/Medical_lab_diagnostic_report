"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError, ExtractedRow, Report, User } from "@/lib/api";
import { clearToken, getToken } from "@/lib/session";

const SAMPLE_CBC: ExtractedRow[] = [
  { raw_name: "Hemoglobin", value: 11.2, unit: "g/dL", reference_range: "13.0 - 17.0" },
  { raw_name: "Hematocrit", value: 34.0, unit: "%", reference_range: "36.0 - 46.0" },
  { raw_name: "WBC Count", value: 6.8, unit: "x10³/µL", reference_range: "4.5 - 11.0" },
  { raw_name: "Platelets", value: 220, unit: "x10³/µL", reference_range: "150 - 450" },
];

const SAMPLE_METABOLIC: ExtractedRow[] = [
  { raw_name: "Fasting Blood Glucose", value: 138, unit: "mg/dL", reference_range: "70 - 99" },
  { raw_name: "Serum Creatinine", value: 0.9, unit: "mg/dL", reference_range: "0.6 - 1.2" },
  { raw_name: "Blood Urea Nitrogen (BUN)", value: 16, unit: "mg/dL", reference_range: "7 - 20" },
  { raw_name: "Total Cholesterol", value: 225, unit: "mg/dL", reference_range: "< 200" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Vertical Slice: Test Analyzer State
  const [reportTitle, setReportTitle] = useState("Complete Blood Count (CBC)");
  const [rows, setRows] = useState<ExtractedRow[]>(SAMPLE_CBC);
  const [analyzing, setAnalyzing] = useState(false);
  const [lastSavedReport, setLastSavedReport] = useState<Report | null>(null);

  // Vertical Slice: Database Reports History State
  const [savedReports, setSavedReports] = useState<Report[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .me(token)
      .then((u) => {
        setUser(u);
        loadReports(token);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
        } else {
          setError(err instanceof ApiError ? err.message : "Something went wrong.");
        }
      });
  }, [router]);

  async function loadReports(token: string) {
    setLoadingReports(true);
    try {
      const data = await api.listReports(token);
      setSavedReports(data);
    } catch {
      // Non-fatal if list reports fails
    } finally {
      setLoadingReports(false);
    }
  }

  async function handleAnalyzeAndSave() {
    const token = getToken();
    if (!token) return;
    setAnalyzing(true);
    setError(null);
    try {
      const created = await api.createReport(token, reportTitle, rows);
      setLastSavedReport(created);
      await loadReports(token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to analyze and save report.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleDeleteReport(id: string) {
    const token = getToken();
    if (!token) return;
    try {
      await api.deleteReport(token, id);
      setSavedReports((prev) => prev.filter((r) => r.id !== id));
      if (lastSavedReport?.id === id) setLastSavedReport(null);
    } catch {
      setError("Could not delete report.");
    }
  }

  async function logout() {
    const token = getToken();
    if (token) await api.logout(token).catch(() => undefined);
    clearToken();
    router.replace("/login");
  }

  return (
    <main>
      <h1>Patient Dashboard & Lab Analyzer</h1>
      {error && <div className="message error" role="alert">{error}</div>}
      {!user && !error && <p>Loading account details...</p>}

      {user && (
        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
          {/* 1. Account Card */}
          <div className="card">
            <h2>Your Profile</h2>
            <dl>
              <dt>Email</dt>
              <dd>{user.email}</dd>
              <dt>Role</dt>
              <dd>{user.role}</dd>
            </dl>
            <button onClick={logout}>Log out</button>
          </div>

          {/* 2. Vertical Slice: Diagnostic Calculation Engine */}
          <div className="card">
            <h2>Core Business Logic: Lab Test Analyzer (Vertical Slice)</h2>
            <p className="lead">
              Enter clinical biomarker measurements or load presets. The core rule engine evaluates reference ranges,
              generates diagnostic flags, and saves the verified report into PostgreSQL.
            </p>

            <div style={{ display: "flex", gap: "10px", margin: "16px 0" }}>
              <button
                type="button"
                onClick={() => {
                  setReportTitle("Complete Blood Count (CBC)");
                  setRows(SAMPLE_CBC);
                }}
              >
                Load CBC Blood Preset
              </button>
              <button
                type="button"
                onClick={() => {
                  setReportTitle("Comprehensive Metabolic Panel (CMP)");
                  setRows(SAMPLE_METABOLIC);
                }}
              >
                Load Metabolic Panel Preset
              </button>
            </div>

            <label htmlFor="report-title">Report Title</label>
            <input
              id="report-title"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
            />

            <table>
              <thead>
                <tr>
                  <th>Biomarker Test</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Reference Range</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr key={idx}>
                    <td><strong>{row.raw_name}</strong></td>
                    <td>{row.value}</td>
                    <td>{row.unit || "—"}</td>
                    <td>{row.reference_range || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              className="primary"
              onClick={handleAnalyzeAndSave}
              disabled={analyzing}
              style={{ marginTop: "16px" }}
            >
              {analyzing ? "Evaluating & Persisting to Database..." : "Run Clinical Evaluation & Save Report"}
            </button>

            {/* Live Evaluation Results */}
            {lastSavedReport && (
              <div className="notice" style={{ marginTop: "20px" }}>
                <h3 style={{ margin: "0 0 10px" }}>
                  Clinical Evaluation: {lastSavedReport.title} (Saved to DB)
                </h3>
                <p style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "var(--muted)" }}>
                  Summary: {lastSavedReport.summary.total} total tests —{" "}
                  <strong>{lastSavedReport.summary.normal} Normal</strong>,{" "}
                  <strong>{lastSavedReport.summary.low} Low</strong>,{" "}
                  <strong>{lastSavedReport.summary.high} High</strong>.
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Test Name</th>
                      <th>Value</th>
                      <th>Range</th>
                      <th>Clinical Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastSavedReport.results.map((r, i) => (
                      <tr key={i}>
                        <td>{r.biomarker_name || r.raw_name}</td>
                        <td>{r.value} {r.unit || ""}</td>
                        <td>{r.reference_range || "N/A"}</td>
                        <td>
                          <span className={`badge ${r.flag}`}>{r.flag}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 3. Database Reports History */}
          <div className="card">
            <h2>Your Saved Diagnostic Reports (Database Records)</h2>
            <p className="lead">
              Reports persisted in the PostgreSQL database for user <code>{user.id}</code>.
            </p>

            {loadingReports && <p>Loading saved reports from database...</p>}

            {!loadingReports && savedReports.length === 0 && (
              <p style={{ fontStyle: "italic", color: "var(--muted)" }}>
                No reports saved yet. Use the analyzer above to create your first report.
              </p>
            )}

            {!loadingReports && savedReports.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Report Title</th>
                    <th>Total Tests</th>
                    <th>Flags Breakdown</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {savedReports.map((rep) => (
                    <tr key={rep.id}>
                      <td>{new Date(rep.created_at).toLocaleDateString()}</td>
                      <td><strong>{rep.title}</strong></td>
                      <td>{rep.summary.total} biomarkers</td>
                      <td>
                        <span className="badge normal">{rep.summary.normal} normal</span>{" "}
                        {rep.summary.low > 0 && <span className="badge low">{rep.summary.low} low</span>}{" "}
                        {rep.summary.high > 0 && <span className="badge high">{rep.summary.high} high</span>}
                      </td>
                      <td>
                        <button
                          style={{ margin: 0, padding: "4px 8px", fontSize: "0.8rem" }}
                          onClick={() => handleDeleteReport(rep.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
