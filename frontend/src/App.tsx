import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Dashboard from './components/Dashboard/Dashboard';
import ScanDetails from './components/ScanDetails/ScanDetails';
import Schedules from './components/Schedules/Schedules';
import ResultsBrowser from './components/Results/ResultsBrowser';

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan/:id" element={<ScanDetails />} />
        <Route path="/results" element={<ResultsBrowser />} />
        <Route path="/schedules" element={<Schedules />} />
        <Route path="/settings" element={<div>Settings (Coming Soon)</div>} />
      </Routes>
    </Box>
  );
}

export default App;
