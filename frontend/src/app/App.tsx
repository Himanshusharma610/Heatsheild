import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AppLayout } from '../components/layout/AppLayout';
import { DashboardPage } from '../pages/DashboardPage';
import { OverviewPage } from '../pages/OverviewPage';
import { DevicesPage } from '../pages/DevicesPage';
import { AlertsPage } from '../pages/AlertsPage';
import { HeatRiskCalculatorPage } from '../pages/HeatRiskCalculatorPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { LoginPage } from '../pages/LoginPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="devices" element={<ProtectedRoute><DevicesPage /></ProtectedRoute>} />
          <Route path="alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
          <Route path="calculator" element={<HeatRiskCalculatorPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
};

export default App;
