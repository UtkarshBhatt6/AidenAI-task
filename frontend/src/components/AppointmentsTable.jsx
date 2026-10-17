import React, { useState } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Search, 
  Filter, 
  MessageSquare, 
  Phone, 
  ChevronRight,
  Info,
  CalendarCheck
} from 'lucide-react';
import { api } from '../api';

export default function AppointmentsTable({ 
  appointments, 
  isLoading, 
  onReconcileSuccess,
  statusFilter,
  setStatusFilter,
  riskFilter,
  setRiskFilter,
  searchQuery,
  setSearchQuery
}) {
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [reconcileModalAppt, setReconcileModalAppt] = useState(null);
  const [reconcileStatus, setReconcileStatus] = useState('NO_SHOW');
  const [reconcileNotes, setReconcileNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenReconcile = (appt, status) => {
    setReconcileModalAppt(appt);
    setReconcileStatus(status);
    setReconcileNotes('');
  };

  const handleConfirmReconcile = async () => {
    if (!reconcileModalAppt) return;
    setIsSubmitting(true);
    try {
      await api.reconcileAppointment(reconcileModalAppt.id, {
        status: reconcileStatus,
        notes: reconcileNotes
      });
      setReconcileModalAppt(null);
      onReconcileSuccess();
    } catch (err) {
      alert(`Reconciliation failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatTime = (isoString) => {
    if (!isoString) return '--:--';
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Top Filter and Search Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        
        {/* Search */}
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '10px' }} />
          <input
            id="search-patients"
            type="text"
            placeholder="Search patient by name or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', paddingLeft: '36px' }}
          />
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          
          {/* Status Tabs */}
          <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: '3px' }}>
            {['ALL', 'SCHEDULED', 'COMPLETED', 'NO_SHOW', 'CANCELLED'].map((st) => (
              <button
                key={st}
                id={`filter-status-${st.toLowerCase()}`}
                onClick={() => setStatusFilter(st)}
                style={{
                  background: statusFilter === st ? 'var(--primary)' : 'transparent',
                  color: statusFilter === st ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  padding: '5px 12px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Risk Tier Tabs */}
          <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: '3px' }}>
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((risk) => (
              <button
                key={risk}
                id={`filter-risk-${risk.toLowerCase()}`}
                onClick={() => setRiskFilter(risk)}
                style={{
                  background: riskFilter === risk ? 'rgba(255,255,255,0.15)' : 'transparent',
                  color: risk === 'HIGH' ? '#f87171' : risk === 'MEDIUM' ? '#fbbf24' : risk === 'LOW' ? '#34d399' : '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                {risk === 'ALL' ? 'All Risks' : `${risk} Risk`}
              </button>
            ))}
          </div>

        </div>
      </div>

      {/* Main Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Patient</th>
              <th>Department</th>
              <th>Lead Time</th>
              <th>Reminders & History</th>
              <th>AI No-Show Risk</th>
              <th>Reconciliation Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  Loading clinic appointments...
                </td>
              </tr>
            ) : appointments.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-dim)' }}>
                  <CalendarCheck size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                  <div>No appointments match the selected filters.</div>
                  <div style={{ fontSize: '0.75rem', marginTop: '6px' }}>Try switching clinic, date, or clicking "Seed Schedule" above.</div>
                </td>
              </tr>
            ) : (
              appointments.map((appt) => {
                const isHighRisk = appt.risk_tier === 'HIGH';
                const isMedRisk = appt.risk_tier === 'MEDIUM';
                const riskPercent = Math.round(appt.risk_score * 100);

                return (
                  <tr key={appt.id} id={`row-appt-${appt.id}`}>
                    
                    {/* Time */}
                    <td style={{ fontWeight: '600', color: 'var(--text-main)', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} color="var(--text-dim)" />
                        {formatTime(appt.scheduled_time)}
                      </div>
                    </td>

                    {/* Patient */}
                    <td>
                      <div style={{ fontWeight: '600', color: '#fff' }}>{appt.patient_name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {appt.age} yrs • {appt.patient_phone || 'No phone'}
                      </div>
                    </td>

                    {/* Department */}
                    <td>
                      <span style={{ 
                        fontSize: '0.775rem', 
                        padding: '2px 8px', 
                        borderRadius: 'var(--radius-sm)', 
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid var(--border-subtle)'
                      }}>
                        {appt.department}
                      </span>
                    </td>

                    {/* Lead Time */}
                    <td>
                      <span style={{ fontSize: '0.8rem', color: appt.lead_days >= 14 ? '#fb7185' : 'var(--text-main)' }}>
                        {appt.lead_days} {appt.lead_days === 1 ? 'day' : 'days'}
                      </span>
                    </td>

                    {/* Reminders & Past Adherence */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
                        <span 
                          title={appt.sms_reminder ? "SMS Reminder Dispatched" : "No SMS Reminder Sent"}
                          style={{ color: appt.sms_reminder ? '#34d399' : '#94a3b8' }}
                        >
                          <MessageSquare size={13} style={{ verticalAlign: 'middle', marginRight: '3px' }} />
                          {appt.sms_reminder ? 'SMS' : 'No SMS'}
                        </span>
                        <span>•</span>
                        <span style={{ color: appt.prior_no_shows > 0 ? '#fb7185' : 'var(--text-dim)' }}>
                          {appt.prior_no_shows > 0 ? `${appt.prior_no_shows} past misses` : '0 misses'}
                        </span>
                      </div>
                    </td>

                    {/* AI Risk Score Meter */}
                    <td>
                      <div 
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedAppointment(appt)}
                        title="Click to view AI clinical recommendations"
                      >
                        <div className="risk-meter">
                          <span className={`badge badge-${appt.risk_tier.toLowerCase()}`}>
                            {riskPercent}% {appt.risk_tier}
                          </span>
                          <div className="risk-meter-track">
                            <div 
                              className="risk-meter-fill" 
                              style={{ 
                                width: `${riskPercent}%`, 
                                background: isHighRisk ? '#f43f5e' : isMedRisk ? '#f59e0b' : '#10b981' 
                              }} 
                            />
                          </div>
                        </div>
                        {appt.ai_headline && (
                          <div style={{ 
                            fontSize: '0.7rem', 
                            color: 'var(--text-dim)', 
                            marginTop: '4px',
                            maxWidth: '220px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {appt.ai_headline}
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td>
                      <span className={`badge badge-${appt.status.toLowerCase()}`}>
                        {appt.status}
                      </span>
                      {appt.reconciled_by && (
                        <div style={{ fontSize: '0.675rem', color: 'var(--text-dim)', marginTop: '3px' }}>
                          by {appt.reconciled_by}
                        </div>
                      )}
                    </td>

                    {/* Quick Reconciliation Actions */}
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        {appt.status === 'SCHEDULED' ? (
                          <>
                            <button
                              id={`btn-complete-${appt.id}`}
                              className="btn btn-emerald btn-sm"
                              onClick={() => handleOpenReconcile(appt, 'COMPLETED')}
                              title="Mark Patient Attended"
                            >
                              <CheckCircle size={13} /> Attended
                            </button>
                            <button
                              id={`btn-noshow-${appt.id}`}
                              className="btn btn-rose btn-sm"
                              onClick={() => handleOpenReconcile(appt, 'NO_SHOW')}
                              title="Mark Patient No-Show"
                            >
                              <XCircle size={13} /> No-Show
                            </button>
                          </>
                        ) : (
                          <button
                            id={`btn-reopen-${appt.id}`}
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleOpenReconcile(appt, appt.status === 'NO_SHOW' ? 'COMPLETED' : 'NO_SHOW')}
                            title="Re-open or override reconciliation"
                          >
                            Re-evaluate
                          </button>
                        )}
                        <button
                          id={`btn-inspect-${appt.id}`}
                          className="btn btn-secondary btn-sm"
                          onClick={() => setSelectedAppointment(appt)}
                          title="Inspect AI Insights"
                        >
                          <Info size={13} />
                        </button>
                      </div>
                    </td>

                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* AI Risk Detail & Intervention Modal */}
      {selectedAppointment && (
        <div className="modal-overlay" onClick={() => setSelectedAppointment(null)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <span className={`badge badge-${selectedAppointment.risk_tier.toLowerCase()}`} style={{ marginBottom: '8px' }}>
                  {Math.round(selectedAppointment.risk_score * 100)}% {selectedAppointment.risk_tier} RISK
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '700' }}>{selectedAppointment.patient_name}</h3>
                <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                  Scheduled {formatTime(selectedAppointment.scheduled_time)} • {selectedAppointment.department} • {selectedAppointment.age} yrs
                </p>
              </div>
              <button 
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedAppointment(null)}
              >
                ✕ Close
              </button>
            </div>

            {/* AI Headline */}
            <div style={{ 
              background: 'rgba(56, 189, 248, 0.08)', 
              border: '1px solid rgba(56, 189, 248, 0.25)', 
              borderRadius: 'var(--radius-md)', 
              padding: '14px', 
              marginBottom: '18px' 
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#38bdf8', marginBottom: '4px' }}>
                AI CLINICAL RECOMMENDATION
              </div>
              <p style={{ fontSize: '0.9rem', color: '#fff', fontWeight: '500' }}>
                {selectedAppointment.ai_headline || 'Standard outreach protocol.'}
              </p>
            </div>

            {/* Risk Drivers */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '8px' }}>
                KEY RISK FACTORS IDENTIFIED:
              </div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedAppointment.risk_factors.map((factor, idx) => (
                  <li key={idx} style={{ 
                    fontSize: '0.825rem', 
                    padding: '8px 12px', 
                    background: 'var(--bg-tertiary)', 
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <AlertTriangle size={14} color="#f59e0b" />
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Proactive Action Steps */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '8px' }}>
                SUGGESTED CLINIC ACTIONS:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedAppointment.recommended_actions.map((act, idx) => (
                  <div key={idx} style={{ 
                    fontSize: '0.825rem', 
                    padding: '8px 12px', 
                    background: 'rgba(16, 185, 129, 0.08)', 
                    border: '1px solid rgba(16, 185, 129, 0.2)', 
                    borderRadius: 'var(--radius-sm)',
                    color: '#34d399',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <CheckCircle size={14} />
                    <span>{act}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer reconciliation shortcut */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                className="btn btn-emerald"
                onClick={() => {
                  setSelectedAppointment(null);
                  handleOpenReconcile(selectedAppointment, 'COMPLETED');
                }}
              >
                <CheckCircle size={15} /> Mark Attended
              </button>
              <button
                className="btn btn-rose"
                onClick={() => {
                  setSelectedAppointment(null);
                  handleOpenReconcile(selectedAppointment, 'NO_SHOW');
                }}
              >
                <XCircle size={15} /> Mark No-Show
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reconciliation Confirmation Modal */}
      {reconcileModalAppt && (
        <div className="modal-overlay" onClick={() => setReconcileModalAppt(null)}>
          <div className="modal-content glass-panel" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '8px' }}>
              Reconcile Appointment Status
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Updating appointment for <strong>{reconcileModalAppt.patient_name}</strong>
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Outcome Status
              </label>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setReconcileStatus('COMPLETED')}
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: 'var(--radius-md)',
                    border: reconcileStatus === 'COMPLETED' ? '2px solid #10b981' : '1px solid var(--border-subtle)',
                    background: reconcileStatus === 'COMPLETED' ? 'var(--emerald-bg)' : 'var(--bg-tertiary)',
                    color: '#fff',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  Attended / Completed
                </button>
                <button
                  type="button"
                  onClick={() => setReconcileStatus('NO_SHOW')}
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: 'var(--radius-md)',
                    border: reconcileStatus === 'NO_SHOW' ? '2px solid #f43f5e' : '1px solid var(--border-subtle)',
                    background: reconcileStatus === 'NO_SHOW' ? 'var(--rose-bg)' : 'var(--bg-tertiary)',
                    color: '#fff',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  No-Show
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Staff Notes (Optional)
              </label>
              <textarea
                id="reconcile-notes-input"
                rows="3"
                placeholder="e.g. Patient called to reschedule, unreachable, transportation issue..."
                value={reconcileNotes}
                onChange={(e) => setReconcileNotes(e.target.value)}
                style={{ width: '100%', resize: 'none' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                type="button"
                className="btn btn-secondary"
                onClick={() => setReconcileModalAppt(null)}
              >
                Cancel
              </button>
              <button 
                id="btn-confirm-reconcile"
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmReconcile}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : 'Confirm Reconciliation'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
