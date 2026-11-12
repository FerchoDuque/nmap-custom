import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  LinearProgress,
  Chip,
  Alert,
  AlertTitle,
  Snackbar,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Add as AddIcon,
  Terminal as TerminalIcon,
  Schedule as ScheduleIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useScanStore } from '@/store/scanStore';
import { scanApi } from '@/services/api';
import type { Scan, ScanCreateRequest } from '@/types';
import ScanDialog from '../ScanDialog';
import { WebSocketService } from '@/services/websocket';
import {
  formatStatusLabel,
  getStatusColor,
  isActiveStatus,
  isTerminalStatus,
  snapshotToScanUpdates,
} from '@/utils/scan';
import { getErrorMessage } from '@/utils/errors';

function ScanCard({ scan, onOpen }: { scan: Scan; onOpen: () => void }) {
  const active = isActiveStatus(scan.status);

  return (
    <Card>
      <CardContent>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <Typography variant="h6" noWrap>
            {scan.name || `Scan #${scan.id}`}
          </Typography>
          <Chip
            label={formatStatusLabel(scan.status)}
            color={getStatusColor(scan.status)}
            size="small"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          <Box component="span" sx={{ color: 'primary.main' }}>
            &gt;
          </Box>{' '}
          {scan.target}
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
          TYPE // {scan.scan_type}
        </Typography>

        {active && (
          <>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              HOST // {scan.current_host || 'Initializing...'}
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  PROGRESS
                </Typography>
                <Typography variant="caption" color="primary.main">
                  {Math.round(scan.progress)}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={scan.progress} />
            </Box>
          </>
        )}

        {!active && (
          <Box sx={{ display: 'flex', gap: 3, mt: 1 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                HOSTS UP
              </Typography>
              <Typography variant="body2">
                {scan.total_hosts_up} / {scan.hosts_total}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                PORTS
              </Typography>
              <Typography variant="body2">{scan.total_ports_found}</Typography>
            </Box>
          </Box>
        )}
      </CardContent>
      <CardActions>
        <Button size="small" onClick={onOpen}>
          {active ? 'View Details' : 'View Results'}
        </Button>
      </CardActions>
    </Card>
  );
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
      <TerminalIcon color="primary" fontSize="small" />
      <Typography variant="h5" component="h2">
        &gt; {title}
      </Typography>
      <Chip label={count} size="small" color="primary" variant="outlined" />
    </Box>
  );
}

function Dashboard() {
  const { scans, activeScans, setScans, setLoading, setError, error, updateScan } =
    useScanStore();
  const navigate = useNavigate();
  const [refreshing, setRefreshing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const wsConnections = useRef<Map<number, WebSocketService>>(new Map());

  /*
   * activeScans changes on every progress update. Deriving a stable string id
   * list keeps the WebSocket effect from re-running on every tick.
   */
  const activeScanIds = activeScans
    .map((scan) => scan.id)
    .sort((a, b) => a - b)
    .join(',');
  const activeScansRef = useRef(activeScans);

  useEffect(() => {
    activeScansRef.current = activeScans;
  }, [activeScans]);

  const loadScans = useCallback(async () => {
    try {
      setLoading(true);
      const data = await scanApi.listScans({ limit: 20 });
      setScans(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load scans'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setScans, setError]);

  useEffect(() => {
    void loadScans();
  }, [loadScans]);

  // WebSocket connections for active scans
  useEffect(() => {
    const currentScans = activeScansRef.current;

    // 1. Connect new scans
    currentScans.forEach((scan) => {
      if (wsConnections.current.has(scan.id)) return;

      const ws = new WebSocketService(scan.id);
      ws.connect(
        (message) => {
          if (message.type === 'error') {
            setError(message.message || 'WebSocket error');
            return;
          }

          updateScan(scan.id, snapshotToScanUpdates(message));

          if (isTerminalStatus(message.status)) {
            const connection = wsConnections.current.get(scan.id);
            connection?.disconnect();
            wsConnections.current.delete(scan.id);

            setSnackbarMessage(`Scan ${message.status}. Reloading dashboard...`);
            setSnackbarOpen(true);
            void loadScans();
            // Extra refreshes to absorb DB/task write latency.
            setTimeout(() => void loadScans(), 1000);
            setTimeout(() => void loadScans(), 3000);
          }
        },
        (wsError) => {
          console.error(`WebSocket error for scan ${scan.id}:`, wsError);
        }
      );

      wsConnections.current.set(scan.id, ws);
    });

    // 2. Disconnect scans that are no longer active
    const currentActiveIds = new Set(currentScans.map((scan) => scan.id));
    wsConnections.current.forEach((ws, scanId) => {
      if (!currentActiveIds.has(scanId)) {
        ws.disconnect();
        wsConnections.current.delete(scanId);
      }
    });
  }, [activeScanIds, loadScans, setError, updateScan]);

  // Cleanup WebSockets on unmount
  useEffect(() => {
    const connections = wsConnections.current;
    return () => {
      connections.forEach((ws) => ws.disconnect());
      connections.clear();
    };
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadScans();
    setRefreshing(false);
  };

  const handleCreateScan = async (data: ScanCreateRequest) => {
    try {
      await scanApi.createScan(data);
      await loadScans();
    } catch (err: unknown) {
      throw new Error(getErrorMessage(err, 'Failed to create scan'));
    }
  };

  return (
    <>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header */}
        <Box
          sx={{
            mb: 4,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 2,
            flexWrap: 'wrap',
            borderBottom: '1px solid',
            borderColor: 'divider',
            pb: 2,
          }}
        >
          <Box>
            <Typography
              variant="h3"
              component="h1"
              sx={{ color: 'primary.main', textShadow: '0 0 12px rgba(0,229,255,0.35)' }}
            >
              &gt; NETWORK_SCANNER
            </Typography>
            <Typography variant="caption" color="text.secondary">
              [CYBERPUNK CONSOLE // AUTHORIZED NETWORK RECON]
            </Typography>
          </Box>
          <Box>
            <Button
              variant="outlined"
              startIcon={<ScheduleIcon />}
              onClick={() => navigate('/schedules')}
              sx={{ mr: 2 }}
            >
              Schedules
            </Button>
            <Button
              variant="outlined"
              startIcon={<SearchIcon />}
              onClick={() => navigate('/results')}
              sx={{ mr: 2 }}
            >
              Results
            </Button>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={refreshing}
              sx={{ mr: 2 }}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setDialogOpen(true)}
            >
              New Scan
            </Button>
          </Box>
        </Box>

        {/* Legal disclaimer */}
        <Alert severity="warning" sx={{ mb: 4 }}>
          <AlertTitle>Legal Notice</AlertTitle>
          This tool is intended for use on <strong>LOCAL NETWORKS ONLY</strong>.
          Scanning networks without proper authorization is illegal. Use
          responsibly and only on networks you own or have explicit permission to
          scan.
        </Alert>

        {/* Error display */}
        {error && (
          <Alert severity="error" sx={{ mb: 4 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Active scans */}
        {activeScans.length > 0 && (
          <Box sx={{ mb: 4 }}>
            <SectionHeader title="ACTIVE_OPERATIONS" count={activeScans.length} />
            <Grid container spacing={3}>
              {activeScans.map((scan) => (
                <Grid item xs={12} md={6} lg={4} key={scan.id}>
                  <ScanCard scan={scan} onOpen={() => navigate(`/scan/${scan.id}`)} />
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Recent scans */}
        <Box>
          <SectionHeader title="RECENT_OPERATIONS" count={scans.length} />
          <Grid container spacing={3}>
            {scans.slice(0, 6).map((scan) => (
              <Grid item xs={12} md={6} lg={4} key={scan.id}>
                <ScanCard scan={scan} onOpen={() => navigate(`/scan/${scan.id}`)} />
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* Empty state */}
        {scans.length === 0 && !refreshing && (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              &gt; NO_SCANS_DETECTED
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Create your first network scan to get started.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setDialogOpen(true)}
            >
              Create Scan
            </Button>
          </Paper>
        )}
      </Container>

      <ScanDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleCreateScan}
      />

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </>
  );
}

export default Dashboard;
