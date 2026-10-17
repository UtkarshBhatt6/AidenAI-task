import React, { useState, useEffect } from 'react';
import { 
  CalendarCheck, 
  FileText, 
  Cpu, 
  ShieldCheck, 
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { api, getActiveUser } from './api';
import Header from './components/Header';
import DailyKPIBar from './components/DailyKPIBar';
import AppointmentsTable from './components/AppointmentsTable';
import NewAppointmentModal from './components/NewAppointmentModal';
import SummaryReportView from './components/SummaryReportView';
import ModelObservatory from './components/ModelObservatory';
import ManagerAdminView from './components/ManagerAdminView';

export default function App() {
  const [activeTab, setActiveTab] = useState('appointments'); // appointments, report, model, admin
  const [selectedClinic, setSelectedClinic] = useState('branch-central');
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [activeRole, setActiveRole] = useState('CLINIC_STAFF');
  
  // Data state
  const [appointments, setAppointments] = useState([]);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Filter state
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [apptsData, summaryData] = await Promise.all([
        api.getAppointments({
          clinicId: selectedClinic,
          date: selectedDate,
          status: statusFilter,
          riskTier: riskFilter,
          search: searchQuery
        }),
        api.getDailySummary(selectedClinic, selectedDate)
      ]);
      setAppointments(apptsData);
      setSummary(summaryData);
    } catch (err) {
      console.error("Failed to load appointment schedule:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedClinic, selectedDate, statusFilter, riskFilter, searchQuery]);

  return (
    <div className="app-container">
      
      {/* Top Header */}
      <Header
        selectedClinic={selectedClinic}
        setSelectedClinic={setSelectedClinic}
        selectedDate={selectedDate}
        setSelectedDate={setSelectedDate}
        onNewAppointmentClick={() => setIsModalOpen(true)}
        onDataRefresh={loadData}
        activeRole={activeRole}
        setActiveRole={setActiveRole}
      />

      {/* Daily KPI Metric Cards */}
      <DailyKPIBar summary={summary} />

      {/* Primary Tab Navigation */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        marginBottom: '20px', 
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '12px',
        overflowX: 'auto'
      }}>
        <button
          id="tab-appointments"
          onClick={() => setActiveTab('appointments')}
          className={`btn ${activeTab === 'appointments' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <CalendarCheck size={16} /> Appointments & Reconciliation
        </button>

        <button
          id="tab-report"
          onClick={() => setActiveTab('report')}
          className={`btn ${activeTab === 'report' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <FileText size={16} /> Daily Reconciliation Report
        </button>

        <button
          id="tab-model"
          onClick={() => setActiveTab('model')}
          className={`btn ${activeTab === 'model' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <Cpu size={16} /> AI Model Observatory & Simulator
        </button>

        <button
          id="tab-admin"
          onClick={() => setActiveTab('admin')}
          className={`btn ${activeTab === 'admin' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ position: 'relative' }}
        >
          <ShieldCheck size={16} /> Manager Admin & Audit
          {activeRole === 'CLINIC_STAFF' && (
            <span style={{ 
              fontSize: '0.65rem', 
              padding: '2px 5px', 
              background: 'var(--rose-bg)', 
              color: '#fb7185', 
              borderRadius: 'var(--radius-sm)',
              marginLeft: '4px'
            }}>
              RBAC
            </span>
          )}
        </button>
      </div>

      {/* Tab Views */}
      <main>
        {activeTab === 'appointments' && (
          <AppointmentsTable
            appointments={appointments}
            isLoading={isLoading}
            onReconcileSuccess={loadData}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            riskFilter={riskFilter}
            setRiskFilter={setRiskFilter}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
          />
        )}

        {activeTab === 'report' && (
          <SummaryReportView
            clinicId={selectedClinic}
            date={selectedDate}
            onReconcileClick={() => setActiveTab('appointments')}
          />
        )}

        {activeTab === 'model' && (
          <ModelObservatory />
        )}

        {activeTab === 'admin' && (
          <ManagerAdminView
            activeRole={activeRole}
            setActiveRole={setActiveRole}
            onRoleSwitch={(newRole) => {
              setActiveRole(newRole);
              loadData();
            }}
          />
        )}
      </main>

      {/* New Appointment Modal */}
      <NewAppointmentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={loadData}
        clinicId={selectedClinic}
        defaultDate={selectedDate}
      />

    </div>
  );
}
