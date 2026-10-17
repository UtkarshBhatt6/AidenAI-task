import React, { useState, useEffect } from 'react';
import { Sparkles, Calendar, Clock, User, Phone, CheckCircle, AlertTriangle } from 'lucide-react';
import { api } from '../api';

const DEPARTMENTS = [
  "General Medicine",
  "Cardiology",
  "Pediatrics",
  "Orthopedics",
  "Dermatology",
  "Endocrinology",
  "Neurology"
];

export default function NewAppointmentModal({ isOpen, onClose, onSuccess, clinicId, defaultDate }) {
  const [formData, setFormData] = useState({
    patient_name: '',
    patient_phone: '',
    age: 38,
    department: 'General Medicine',
    scheduled_date: defaultDate || new Date().toISOString().split('T')[0],
    scheduled_hour: 10,
    lead_days: 4,
    sms_reminder: true,
    prior_appointments: 2,
    prior_no_shows: 0,
    chronic_condition: false,
    initial_status: 'SCHEDULED'
  });

  const [livePrediction, setLivePrediction] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Run live ML prediction preview whenever key risk factors change
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(async () => {
      try {
        const pred = await api.predictAdHoc({
          age: parseInt(formData.age) || 35,
          lead_days: parseInt(formData.lead_days) || 0,
          day_of_week: new Date(formData.scheduled_date).getDay(),
          hour: parseInt(formData.scheduled_hour) || 10,
          prior_appointments: parseInt(formData.prior_appointments) || 0,
          prior_no_shows: parseInt(formData.prior_no_shows) || 0,
          sms_reminder: Boolean(formData.sms_reminder),
          chronic_condition: Boolean(formData.chronic_condition),
          department: formData.department
        });
        setLivePrediction(pred);
      } catch (err) {
        console.error("Live prediction error:", err);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [
    formData.age,
    formData.lead_days,
    formData.scheduled_date,
    formData.scheduled_hour,
    formData.prior_appointments,
    formData.prior_no_shows,
    formData.sms_reminder,
    formData.chronic_condition,
    formData.department,
    isOpen
  ]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!formData.patient_name.trim()) {
      setErrorMsg('Patient name is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Build full scheduled datetime
      const [year, month, day] = formData.scheduled_date.split('-');
      const scheduledTime = new Date(year, month - 1, day, formData.scheduled_hour, 0, 0);

      const bookingTime = new Date(scheduledTime);
      bookingTime.setDate(bookingTime.getDate() - parseInt(formData.lead_days || 0));

      const payload = {
        patient_name: formData.patient_name.trim(),
        patient_phone: formData.patient_phone || '+1 (555) 000-0000',
        age: parseInt(formData.age),
        clinic_id: clinicId || 'branch-central',
        department: formData.department,
        scheduled_time: scheduledTime.toISOString(),
        booking_time: bookingTime.toISOString(),
        sms_reminder: formData.sms_reminder,
        prior_appointments: parseInt(formData.prior_appointments),
        prior_no_shows: parseInt(formData.prior_no_shows),
        chronic_condition: formData.chronic_condition,
        initial_status: formData.initial_status
      };

      await api.createAppointment(payload);
      onSuccess();
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create appointment');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
        
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '700' }}>Schedule New Appointment</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Input patient appointment data with real-time AI no-show risk assessment
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>✕</button>
        </div>

        {errorMsg && (
          <div style={{ 
            background: 'var(--rose-bg)', 
            border: '1px solid var(--rose-border)', 
            color: '#fb7185', 
            padding: '10px 14px', 
            borderRadius: 'var(--radius-md)', 
            fontSize: '0.85rem',
            marginBottom: '16px' 
          }}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          
          {/* Patient Details */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Patient Full Name *
              </label>
              <input
                id="input-patient-name"
                type="text"
                placeholder="e.g. Jessica Sterling"
                value={formData.patient_name}
                onChange={(e) => setFormData({ ...formData, patient_name: e.target.value })}
                required
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Age
              </label>
              <input
                id="input-patient-age"
                type="number"
                min="0"
                max="120"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Phone Number
              </label>
              <input
                id="input-patient-phone"
                type="text"
                placeholder="+1 (555) 345-6789"
                value={formData.patient_phone}
                onChange={(e) => setFormData({ ...formData, patient_phone: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Clinical Department
              </label>
              <select
                id="input-department"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                style={{ width: '100%' }}
              >
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Schedule Time & Lead Time */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Scheduled Date
              </label>
              <input
                id="input-scheduled-date"
                type="date"
                value={formData.scheduled_date}
                onChange={(e) => setFormData({ ...formData, scheduled_date: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Time Slot
              </label>
              <select
                id="input-scheduled-hour"
                value={formData.scheduled_hour}
                onChange={(e) => setFormData({ ...formData, scheduled_hour: parseInt(e.target.value) })}
                style={{ width: '100%' }}
              >
                {[8, 9, 10, 11, 13, 14, 15, 16, 17].map((h) => (
                  <option key={h} value={h}>
                    {h === 12 ? '12:00 PM' : h > 12 ? `${h - 12}:00 PM` : `${h}:00 AM`}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Booking Lead (Days)
              </label>
              <input
                id="input-lead-days"
                type="number"
                min="0"
                max="90"
                value={formData.lead_days}
                onChange={(e) => setFormData({ ...formData, lead_days: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Prior History and Status */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Prior Visits
              </label>
              <input
                id="input-prior-appts"
                type="number"
                min="0"
                max="50"
                value={formData.prior_appointments}
                onChange={(e) => setFormData({ ...formData, prior_appointments: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Prior No-Shows
              </label>
              <input
                id="input-prior-noshows"
                type="number"
                min="0"
                max={formData.prior_appointments}
                value={formData.prior_no_shows}
                onChange={(e) => setFormData({ ...formData, prior_no_shows: e.target.value })}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', marginBottom: '6px' }}>
                Initial Status
              </label>
              <select
                id="input-initial-status"
                value={formData.initial_status}
                onChange={(e) => setFormData({ ...formData, initial_status: e.target.value })}
                style={{ width: '100%' }}
              >
                <option value="SCHEDULED">SCHEDULED</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="NO_SHOW">NO_SHOW</option>
              </select>
            </div>
          </div>

          {/* Checkboxes */}
          <div style={{ display: 'flex', gap: '24px', marginBottom: '20px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.825rem', cursor: 'pointer' }}>
              <input
                id="input-sms-reminder"
                type="checkbox"
                checked={formData.sms_reminder}
                onChange={(e) => setFormData({ ...formData, sms_reminder: e.target.checked })}
              />
              Send automated SMS reminder
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.825rem', cursor: 'pointer' }}>
              <input
                id="input-chronic-condition"
                type="checkbox"
                checked={formData.chronic_condition}
                onChange={(e) => setFormData({ ...formData, chronic_condition: e.target.checked })}
              />
              Chronic condition patient
            </label>
          </div>

          {/* Real-Time ML Live Prediction Box */}
          {livePrediction && (
            <div style={{ 
              background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%)',
              border: `1px solid ${livePrediction.risk_tier === 'HIGH' ? 'rgba(244, 63, 94, 0.4)' : livePrediction.risk_tier === 'MEDIUM' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '14px 16px',
              marginBottom: '20px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: '700', color: '#38bdf8' }}>
                  <Sparkles size={14} /> LIVE ML PREDICTION PREVIEW:
                </div>
                <span className={`badge badge-${livePrediction.risk_tier.toLowerCase()}`}>
                  {Math.round(livePrediction.risk_score * 100)}% {livePrediction.risk_tier} RISK
                </span>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: '500', marginBottom: '6px' }}>
                {livePrediction.ai_headline}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Primary driver: {livePrediction.risk_factors?.[0] || 'Standard baseline scheduling parameters'}
              </div>
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button 
              id="btn-submit-appointment"
              type="submit" 
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              <CheckCircle size={15} /> {isSubmitting ? 'Saving...' : 'Book Appointment'}
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
