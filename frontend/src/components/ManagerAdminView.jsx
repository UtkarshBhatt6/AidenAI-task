import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  Zap, 
  Trash2, 
  History, 
  CheckCircle, 
  RefreshCw,
  Lock,
  ArrowRight
} from 'lucide-react';
import { api, getActiveUser } from '../api';

export default function ManagerAdminView({ activeRole, onRoleSwitch }) {
  const [cacheStats, setCacheStats] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isClearing, setIsClearing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const isManager = activeRole === 'CLINIC_MANAGER';

  const loadData = async () => {
    if (!isManager) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const [stats, logs] = await Promise.all([
        api.getCacheStats(),
        api.getAuditLogs(50)
      ]);
      setCacheStats(stats);
      setAuditLogs(logs);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeRole]);

  const handleClearCache = async () => {
    setIsClearing(true);
    setStatusMsg('');
    try {
      const res = await api.clearCache();
      setStatusMsg(res.message);
      setCacheStats(res.new_stats);
    } catch (err) {
      alert(`Cache clearance denied: ${err.message}`);
    } finally {
      setIsClearing(false);
    }
  };

  // If user is Staff, show RBAC Access Denied screen
  if (!isManager) {
    return (
      <div className="glass-panel" style={{ padding: '60px 24px', textAlign: 'center', maxWidth: '650px', margin: '40px auto' }}>
        <div style={{ 
          width: '64px', 
          height: '64px', 
          borderRadius: '50%', 
          background: 'var(--rose-bg)', 
          border: '1px solid var(--rose-border)',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          margin: '0 auto 20px'
        }}>
          <Lock size={32} color="#fb7185" />
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: '700', marginBottom: '10px' }}>
          Role-Based Access Control: Restricted Panel
        </h2>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: '1.6' }}>
          The Administrative Control Center and Audit Trail are restricted to the <strong>CLINIC_MANAGER</strong> role. 
          Your active session is running with <strong>CLINIC_STAFF</strong> privileges ({getActiveUser().name}).
        </p>
        <button
          id="btn-elevate-role"
          className="btn btn-primary"
          style={{ padding: '10px 24px', margin: '0 auto', fontSize: '0.9rem' }}
          onClick={() => {
            onRoleSwitch('CLINIC_MANAGER');
          }}
        >
          <ShieldCheck size={16} /> Switch to Manager Mode <ArrowRight size={14} />
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* RBAC Authorized Banner */}
      <div className="glass-panel" style={{ 
        padding: '16px 24px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.12) 0%, rgba(17, 24, 39, 0.8) 100%)',
        border: '1px solid rgba(124, 58, 237, 0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ShieldCheck size={24} color="#c084fc" />
          <div>
            <div style={{ fontWeight: '700', fontSize: '1.05rem', color: '#fff' }}>
              Clinic Manager Administration Console
            </div>
            <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
              Authorized as: <strong>{activeRole === 'CLINIC_MANAGER' ? 'Dr. Alex Rivera (Clinic Director)' : 'Nurse Sarah Jenkins'}</strong> (Role: {activeRole})
            </div>
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadData}>
          <RefreshCw size={13} /> Refresh Audit Trail
        </button>
      </div>

      {/* Caching Administrative Controls */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={20} color="#f59e0b" />
              <h3 style={{ fontSize: '1.15rem', fontWeight: '700' }}>In-Memory LRU/TTL Cache Administration</h3>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Monitors memory efficiency, query response latency savings, and invalidation triggers.
            </p>
          </div>
          <button
            id="btn-flush-cache"
            className="btn btn-rose btn-sm"
            onClick={handleClearCache}
            disabled={isClearing}
            title="Flush entire in-memory cache and reset telemetry"
          >
            <Trash2 size={14} /> {isClearing ? 'Flushing...' : 'Flush Cache'}
          </button>
        </div>

        {statusMsg && (
          <div style={{ 
            background: 'var(--emerald-bg)', 
            border: '1px solid var(--emerald-border)', 
            color: '#34d399', 
            padding: '10px 14px', 
            borderRadius: 'var(--radius-md)', 
            fontSize: '0.85rem',
            marginBottom: '16px' 
          }}>
            ✓ {statusMsg}
          </div>
        )}

        {/* Cache Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px' }}>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>TOTAL REQUESTS</div>
            <div style={{ fontSize: '1.4rem', fontWeight: '700' }}>{cacheStats?.total_requests || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>CACHE HITS</div>
            <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#34d399' }}>{cacheStats?.hits || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>CACHE MISSES</div>
            <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#38bdf8' }}>{cacheStats?.misses || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>HIT RATIO</div>
            <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#fbbf24' }}>{cacheStats?.hit_ratio_percent || 0}%</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>LATENCY SAVED</div>
            <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#c084fc' }}>~{cacheStats?.estimated_latency_saved_ms || 0} ms</div>
          </div>
        </div>
      </div>

      {/* Clinical Audit Trail Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <History size={18} color="#38bdf8" />
          <h3 style={{ fontSize: '1.15rem', fontWeight: '700' }}>Staff Reconciliation Audit Trail</h3>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Immutable logging of all appointment modifications, status reconciliations, and staff notes.
        </p>

        {auditLogs.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-dim)' }}>
            No audit events recorded yet.
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Staff Member</th>
                  <th>Role</th>
                  <th>Appointment ID</th>
                  <th>Status Transition</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: '0.775rem', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td>
                      <span className="badge" style={{ 
                        background: log.action === 'RECONCILED' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                        color: log.action === 'RECONCILED' ? '#38bdf8' : 'var(--text-main)'
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontWeight: '600' }}>{log.performed_by}</td>
                    <td style={{ fontSize: '0.75rem' }}>{log.role}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {log.appointment_id}
                    </td>
                    <td>
                      {log.old_status ? (
                        <span>
                          <span style={{ color: 'var(--text-dim)' }}>{log.old_status}</span> → <strong style={{ color: log.new_status === 'COMPLETED' ? '#34d399' : '#fb7185' }}>{log.new_status}</strong>
                        </span>
                      ) : (
                        <strong style={{ color: '#38bdf8' }}>{log.new_status}</strong>
                      )}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {log.notes || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
