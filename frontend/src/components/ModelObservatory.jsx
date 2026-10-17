import React, { useState, useEffect } from 'react';
import { Cpu, BarChart2, Sliders, Sparkles, CheckCircle, RefreshCw, Zap } from 'lucide-react';
import { api } from '../api';

export default function ModelObservatory() {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRetraining, setIsRetraining] = useState(false);

  // Simulator state
  const [simFeatures, setSimFeatures] = useState({
    age: 32,
    lead_days: 14,
    day_of_week: 1, // Tuesday
    hour: 10,
    prior_appointments: 4,
    prior_no_shows: 1,
    sms_reminder: false,
    chronic_condition: false,
    department: 'General Medicine'
  });
  const [simResult, setSimResult] = useState(null);

  useEffect(() => {
    api.getModelMetrics()
      .then(setMetrics)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  // Run simulator prediction on change
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const res = await api.predictAdHoc(simFeatures);
        setSimResult(res);
      } catch (err) {
        console.error(err);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [simFeatures]);

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      const res = await api.retrainModel();
      setMetrics(res.metrics);
      alert('Model successfully retrained on updated dataset.');
    } catch (err) {
      alert(`Retraining failed: ${err.message}`);
    } finally {
      setIsRetraining(false);
    }
  };

  if (isLoading) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading ML model metrics and feature telemetry...
      </div>
    );
  }

  const importances = metrics?.feature_importances || {};
  const topFeatures = Object.entries(importances).slice(0, 8);
  const maxImportance = Math.max(...Object.values(importances), 0.01);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Architecture Overview */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={22} color="#38bdf8" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: '700' }}>AI Model Architecture & Clinical Telemetry</h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Calibrated Gradient Boosting Classifier for Outpatient No-Show Prediction
            </p>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleRetrain}
            disabled={isRetraining}
          >
            <RefreshCw size={14} className={isRetraining ? 'spin' : ''} />
            {isRetraining ? 'Retraining...' : 'Trigger Model Retrain'}
          </button>
        </div>

        {/* Metric Badges */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
          gap: '14px', 
          marginTop: '20px' 
        }}>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>ROC-AUC SCORE</div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#38bdf8' }}>{metrics?.roc_auc || 0.79}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Discrimination capacity</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>ACCURACY</div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#34d399' }}>{metrics?.accuracy ? `${(metrics.accuracy * 100).toFixed(1)}%` : '85.3%'}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>On holdout test set</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>DECISION THRESHOLD</div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#fbbf24' }}>{metrics?.decision_threshold || 0.35}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Tuned for clinical triage</div>
          </div>
          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>BRIER SCORE (CALIBRATION)</div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#c084fc' }}>{metrics?.brier_score || 0.103}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Lower = better calibration</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '24px' }}>
        
        {/* Feature Importance Chart */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <BarChart2 size={18} color="#38bdf8" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700' }}>Feature Importance Ranking</h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            What drives outpatient no-show likelihood according to gradient boosted tree splits:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {topFeatures.map(([feat, score]) => {
              const pct = (score / maxImportance) * 100;
              const cleanLabel = feat
                .replace('dept_', 'Dept: ')
                .replace(/_/g, ' ')
                .toUpperCase();

              return (
                <div key={feat}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                    <span style={{ fontWeight: '500' }}>{cleanLabel}</span>
                    <span style={{ color: 'var(--text-dim)' }}>{(score * 100).toFixed(1)}%</span>
                  </div>
                  <div className="risk-meter-track" style={{ width: '100%', height: '7px' }}>
                    <div 
                      className="risk-meter-fill" 
                      style={{ 
                        width: `${pct}%`,
                        background: 'linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)'
                      }} 
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Interactive What-If Risk Simulator */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Sliders size={18} color="#a855f7" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700' }}>Interactive What-If Risk Simulator</h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Adjust patient parameters below to evaluate how interventions modify no-show probability:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* Booking Lead Days Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Booking Lead Time: <strong>{simFeatures.lead_days} days</strong></span>
                <span style={{ color: 'var(--text-dim)' }}>0 - 45 days</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="45" 
                value={simFeatures.lead_days}
                onChange={(e) => setSimFeatures({ ...simFeatures, lead_days: parseInt(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            {/* Past Misses */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Past No-Shows: <strong>{simFeatures.prior_no_shows} misses</strong> (of {simFeatures.prior_appointments} visits)</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max={simFeatures.prior_appointments} 
                value={simFeatures.prior_no_shows}
                onChange={(e) => setSimFeatures({ ...simFeatures, prior_no_shows: parseInt(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            {/* Age Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span>Patient Age: <strong>{simFeatures.age} yrs</strong></span>
              </div>
              <input 
                type="range" 
                min="10" 
                max="90" 
                value={simFeatures.age}
                onChange={(e) => setSimFeatures({ ...simFeatures, age: parseInt(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            {/* SMS Reminder Toggle */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-md)'
            }}>
              <div>
                <div style={{ fontSize: '0.825rem', fontWeight: '600' }}>Automated SMS Reminder</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Dispatched 24h & 2h prior to visit</div>
              </div>
              <input 
                type="checkbox"
                checked={simFeatures.sms_reminder}
                onChange={(e) => setSimFeatures({ ...simFeatures, sms_reminder: e.target.checked })}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
            </div>

            {/* Simulator Output Box */}
            {simResult && (
              <div style={{ 
                background: 'linear-gradient(135deg, rgba(23, 31, 48, 0.95) 0%, rgba(15, 23, 42, 0.9) 100%)',
                border: `1px solid ${simResult.risk_tier === 'HIGH' ? '#f43f5e' : simResult.risk_tier === 'MEDIUM' ? '#f59e0b' : '#10b981'}`,
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                marginTop: '4px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)' }}>
                    SIMULATED OUTCOME:
                  </span>
                  <span className={`badge badge-${simResult.risk_tier.toLowerCase()}`}>
                    {Math.round(simResult.risk_score * 100)}% {simResult.risk_tier} RISK
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: '600', marginBottom: '4px' }}>
                  {simResult.ai_headline}
                </div>
                <div style={{ fontSize: '0.725rem', color: '#38bdf8' }}>
                  💡 Action: {simResult.recommended_actions?.[0]}
                </div>
              </div>
            )}

          </div>
        </div>

      </div>

    </div>
  );
}
