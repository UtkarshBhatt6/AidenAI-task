import React from 'react';
import { Users, UserX, CheckCircle, TrendingUp, AlertTriangle, DollarSign } from 'lucide-react';

export default function DailyKPIBar({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid-cols-4" style={{ marginBottom: '24px' }}>
      
      {/* Total Scheduled */}
      <div className="glass-panel kpi-card" style={{ '--glow-color': 'rgba(56, 189, 248, 0.15)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)' }}>DAILY APPOINTMENTS</span>
          <Users size={18} color="#38bdf8" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: '1.75rem', fontWeight: '700' }}>{summary.total_appointments}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            ({summary.scheduled_count} pending arrival)
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {summary.completed_count} completed • {summary.cancelled_count} cancelled
        </div>
      </div>

      {/* No-Shows & Reconciliation */}
      <div className="glass-panel kpi-card" style={{ '--glow-color': 'rgba(244, 63, 94, 0.18)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)' }}>RECONCILED NO-SHOWS</span>
          <UserX size={18} color="#fb7185" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: '1.75rem', fontWeight: '700', color: summary.no_show_count > 0 ? '#fb7185' : 'inherit' }}>
            {summary.no_show_count}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            of {summary.completed_count + summary.no_show_count} arrived/missed
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: '#fb7185' }}>
          Actual No-Show Rate: <strong>{summary.actual_no_show_rate}%</strong>
        </div>
      </div>

      {/* AI Predicted Rate vs Expected */}
      <div className="glass-panel kpi-card" style={{ '--glow-color': 'rgba(245, 158, 11, 0.15)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)' }}>AI PREDICTED NO-SHOW RATE</span>
          <TrendingUp size={18} color="#fbbf24" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: '1.75rem', fontWeight: '700', color: '#fbbf24' }}>
            {summary.predicted_no_show_rate}%
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            (~{summary.predicted_no_shows_expected} expected misses)
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Model ROC-AUC: <strong>0.79</strong> (Calibrated)
        </div>
      </div>

      {/* Revenue At Risk */}
      <div className="glass-panel kpi-card" style={{ '--glow-color': 'rgba(168, 85, 247, 0.15)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)' }}>REVENUE AT RISK</span>
          <DollarSign size={18} color="#c084fc" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: '1.75rem', fontWeight: '700', color: '#c084fc' }}>
            ${summary.total_revenue_at_risk.toLocaleString()}
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Lost so far: <span style={{ color: '#fb7185' }}>${summary.revenue_lost_from_no_shows.toLocaleString()}</span>
        </div>
      </div>

    </div>
  );
}
