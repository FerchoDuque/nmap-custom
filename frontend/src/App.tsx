import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, LinearProgress, Typography } from '@mui/material';
import Dashboard from './components/Dashboard/Dashboard';

const ScanDetails = lazy(() => import('./components/ScanDetails/ScanDetails'));
const Schedules = lazy(() => import('./components/Schedules/Schedules'));
const ResultsBrowser = lazy(
  () => import('./components/Results/ResultsBrowser')
);

function RouteFallback() {
  return (
    <Box sx={{ width: '100%', p: 4 }}>
      <LinearProgress />
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 1, display: 'block' }}
      >
        &gt; LOADING_MODULE...
      </Typography>
    </Box>
  );
}

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scan/:id" element={<ScanDetails />} />
          <Route path="/results" element={<ResultsBrowser />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/settings" element={<div>Settings (Coming Soon)</div>} />
        </Routes>
      </Suspense>
    </Box>
  );
}

export default App;
