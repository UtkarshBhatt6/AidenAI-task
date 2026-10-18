import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Calendar, 
  UserCheck, 
  PlusCircle, 
  Database, 
  Zap, 
  Activity, 
  ShieldCheck, 
  Sparkles 
} from 'lucide-react';
import { api, getActiveUser, setActiveUser, subscribeToCacheEvents } from '../api';

export default function Header({ 
  selectedClinic, 
  setSelectedClinic, 
  selectedDate, 
  setSelectedDate, 
  onNewAppointmentClick,
  onDataRefresh,
  activeRole,
  onRoleChange
}) {
  const [cacheEvent, setCacheEvent] = useState(null);
  const [cacheStats, setCacheStats] = useState({ hits: 0, misses: 0, hit_ratio_percent: 0 });
  const [isSeeding, setIsSeeding] = useState(false);

  useEffect(() => {
    // Subscribe to real-time cache telemetry events
    const unsubscribe = subscribeToCacheEvents((ev) => {
      setCacheEvent(ev);
      // Fetch aggregate cache stats
      api.getCacheStats()
        .then(setCacheStats)
        .catch(console.error);
    });

    api.getCacheStats().then(setCacheStats).catch(console.error);

    return () => unsubscribe();
  }, []);

  const handleRoleToggle = (newRole) => {
    if (onRoleChange) {
      onRoleChange(newRole);
    } else {
      const userName = newRole === 'CLINIC_MANAGER' ? 'Dr. Alex Rivera (Clinic Director)' : 'Nurse Sarah Jenkins';
      setActiveUser({ role: newRole, name: userName });
      onDataRefresh();
    }
  };

  const handleSeedDemoData = async () => {
    setIsSeeding(true);
    try {
      await api.seedDemoAppointments(selectedClinic);
      onDataRefresh();
    } catch (e) {
      alert(`Error seeding demo data: ${e.message}`);
    } finally {
      setIsSeeding(false);
    }
  };

  return (
    <header className="glass-panel" style={{ padding: '16px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Brand & System Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ 
            width: '42px', 
            height: '42px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(2, 132, 199, 0.4)'
          }}>
            <Activity size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: '700', letterSpacing: '-0.02em' }}>MediTrack</h1>
              <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                <Sparkles size={11} /> AI Insights Engine
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Daily Outpatient No-Show Reconciliation & Predictive Triage</p>
          </div>
        </div>

        {/* Global Controls: Clinic & Date */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          
          {/* Clinic Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Building2 size={16} color="var(--text-dim)" />
            <select 
              id="clinic-selector"
              value={selectedClinic} 
              onChange={(e) => {
                setSelectedClinic(e.target.value);
                setActiveUser({ clinicId: e.target.value });
              }}
              style={{ fontSize: '0.825rem', padding: '6px 10px' }}
            >
              <option value="branch-central">MediTrack Central Hospital</option>
              <option value="branch-west">MediTrack Westside Clinic</option>
              <option value="branch-north">MediTrack North Ambulatory</option>
            </select>
          </div>

          {/* Date Picker */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={16} color="var(--text-dim)" />
            <input 
              id="date-selector"
              type="date" 
              value={selectedDate} 
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{ fontSize: '0.825rem', padding: '5px 10px' }}
            />
          </div>

          {/* RBAC Role Switcher */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '4px', 
            background: 'var(--bg-tertiary)', 
            padding: '3px', 
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)'
          }}>
            <button
              id="role-switch-staff"
              onClick={() => handleRoleToggle('CLINIC_STAFF')}
              style={{
                background: activeRole === 'CLINIC_STAFF' ? 'var(--primary)' : 'transparent',
                color: activeRole === 'CLINIC_STAFF' ? '#fff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 10px',
                fontSize: '0.775rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <UserCheck size={13} /> Staff Mode
            </button>
            <button
              id="role-switch-manager"
              onClick={() => handleRoleToggle('CLINIC_MANAGER')}
              style={{
                background: activeRole === 'CLINIC_MANAGER' ? '#7c3aed' : 'transparent',
                color: activeRole === 'CLINIC_MANAGER' ? '#fff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 10px',
                fontSize: '0.775rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <ShieldCheck size={13} /> Manager Mode
            </button>
          </div>

          {/* Action Buttons */}
          <button 
            id="btn-seed-data"
            onClick={handleSeedDemoData} 
            disabled={isSeeding}
            className="btn btn-secondary btn-sm"
            title="Populate schedule with realistic sample appointments"
          >
            <Database size={14} /> {isSeeding ? 'Seeding...' : 'Seed Schedule'}
          </button>

          <button 
            id="btn-add-appointment"
            onClick={onNewAppointmentClick}
            className="btn btn-primary btn-sm"
          >
            <PlusCircle size={15} /> Add Appointment
          </button>
        </div>
      </div>

      {/* Live Caching & Latency HUD Bar */}
      <div style={{ 
        marginTop: '14px', 
        paddingTop: '12px', 
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: 'var(--text-muted)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Zap size={14} color="#f59e0b" />
            <span style={{ fontWeight: '600', color: 'var(--text-main)' }}>Cache Layer:</span>
            {cacheStats.backend === 'redis' && (
              <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '1px 6px', fontSize: '0.68rem', fontWeight: '700' }}>
                REDIS
              </span>
            )}
            {cacheEvent?.cacheStatus === 'HIT' ? (
              <span id="cache-status-badge" className="badge" style={{ background: 'var(--emerald-bg)', color: '#34d399', border: '1px solid var(--emerald-border)' }}>
                ● CACHE HIT ({cacheEvent.serverTimeMs}ms)
              </span>
            ) : cacheEvent?.cacheStatus === 'MISS' ? (
              <span id="cache-status-badge" className="badge" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                ○ CACHE MISS ({cacheEvent.serverTimeMs}ms)
              </span>
            ) : (
              <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-dim)' }}>READY</span>
            )}
          </div>
          <span>Hits: <strong>{cacheStats.hits}</strong></span>
          <span>Misses: <strong>{cacheStats.misses}</strong></span>
          <span>Hit Ratio: <strong>{cacheStats.hit_ratio_percent}%</strong></span>
          <span>Latency Saved: <strong>~{cacheStats.estimated_latency_saved_ms} ms</strong></span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="pulse-indicator" style={{ background: '#10b981' }}></span>
          <span>Active Role: <strong style={{ color: activeRole === 'CLINIC_MANAGER' ? '#c084fc' : '#38bdf8' }}>{activeRole}</strong> ({activeRole === 'CLINIC_MANAGER' ? 'Dr. Alex Rivera (Clinic Director)' : 'Nurse Sarah Jenkins'})</span>
        </div>
      </div>
    </header>
  );
}
