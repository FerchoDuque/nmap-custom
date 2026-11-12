import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Grid,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ExpandMore as ExpandMoreIcon,
  Computer as ComputerIcon,
  Speed as SpeedIcon,
  Cancel as CancelIcon,
  Terminal as TerminalIcon,
} from '@mui/icons-material';
import { scanApi } from '@/services/api';
import { WebSocketService } from '@/services/websocket';
import type { Scan, ScanResult } from '@/types';
import {
  formatDuration,
  formatStatusLabel,
  getPortStateColor,
  getStatusColor,
  isActiveStatus,
  isTerminalStatus,
  snapshotToScanUpdates,
} from '@/utils/scan';
import { getErrorMessage } from '@/utils/errors';

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography variant="h6" component="div" sx={{ color: 'text.primary' }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function ScanDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const scanId = Number(id);

  const [scan, setScan] = useState<Scan | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocketService | null>(null);
  const loadScanRef = useRef<(targetId: number) => Promise<void>>(async () => {});

  const connectWebSocket = useCallback((targetId: number) => {
    if (wsRef.current) return;

    const ws = new WebSocketService(targetId);
    ws.connect(
      (message) => {
        if (message.type === 'error') {
          setError(message.message || 'WebSocket error');
          return;
        }

        setScan((previous) =>
          previous ? { ...previous, ...snapshotToScanUpdates(message) } : previous
        );

        if (isTerminalStatus(message.status)) {
          ws.disconnect();
          wsRef.current = null;
          // Fetch the final persisted detail, including results.
          void loadScanRef.current(targetId);
        }
      },
      () => setError('Realtime connection lost. Retrying...')
    );
    wsRef.current = ws;
  }, []);

  const loadScan = useCallback(
    async (targetId: number) => {
      try {
        setLoading(true);
        const data = await scanApi.getScan(targetId);
        setScan(data);
        setError(null);

        if (isActiveStatus(data.status)) {
          connectWebSocket(targetId);
        }
      } catch (err: unknown) {
        setError(getErrorMessage(err, 'Failed to load scan details'));
      } finally {
        setLoading(false);
      }
    },
    [connectWebSocket]
  );

  useEffect(() => {
    loadScanRef.current = loadScan;
  }, [loadScan]);

  useEffect(() => {
    if (Number.isNaN(scanId)) {
      setError('Invalid scan id');
      setLoading(false);
      return;
    }

    void loadScan(scanId);

    return () => {
      wsRef.current?.disconnect();
      wsRef.current = null;
    };
  }, [scanId, loadScan]);

  const handleCancel = async () => {
    if (!scan) return;

    setCancelling(true);
    try {
      wsRef.current?.disconnect();
      wsRef.current = null;
      await scanApi.updateScan(scan.id, { status: 'cancelled' });
      await loadScan(scan.id);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to cancel scan'));
    } finally {
      setCancelling(false);
    }
  };

  if (loading && !scan) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <LinearProgress />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          &gt; LOADING_SCAN_DATA...
        </Typography>
      </Container>
    );
  }

  if (error && !scan) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')} variant="outlined">
          Back to Dashboard
        </Button>
      </Container>
    );
  }

  if (!scan) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Scan not found
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')} variant="outlined">
          Back to Dashboard
        </Button>
      </Container>
    );
  }

  const active = isActiveStatus(scan.status);
  const terminal = isTerminalStatus(scan.status);
  const resultCount = scan.results?.length ?? 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 2,
          flexWrap: 'wrap',
          borderBottom: '1px solid',
          borderColor: 'divider',
          pb: 2,
          mb: 3,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/')}
            variant="outlined"
            size="small"
            sx={{ mt: 0.5 }}
          >
            Back
          </Button>
          <Box>
            <Typography
              variant="h4"
              component="h1"
              sx={{ color: 'primary.main', textShadow: '0 0 12px rgba(0,229,255,0.35)' }}
            >
              &gt; SCAN_DETAILS
            </Typography>
            <Typography variant="caption" color="text.secondary">
              TARGET // {scan.name || scan.target}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Chip
            label={formatStatusLabel(scan.status)}
            color={getStatusColor(scan.status)}
            size="small"
          />
          {active && (
            <Button
              variant="outlined"
              color="warning"
              size="small"
              startIcon={<CancelIcon />}
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? 'Cancelling...' : 'Cancel Scan'}
            </Button>
          )}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {scan.error_message && (
        <Alert severity={terminal && scan.status === 'failed' ? 'error' : 'warning'} sx={{ mb: 3 }}>
          {scan.error_message}
        </Alert>
      )}

      {/* Overview */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="caption" color="primary.main" display="block" sx={{ mb: 2 }}>
          // OPERATION_SUMMARY
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Target" value={scan.target} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Scan Type" value={scan.scan_type} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Hosts Up" value={`${scan.total_hosts_up} / ${scan.hosts_total}`} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Ports Found" value={scan.total_ports_found} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat
              label="Duration"
              value={formatDuration(scan.started_at, scan.completed_at)}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Hosts Scanned" value={`${scan.hosts_scanned} / ${scan.hosts_total}`} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Port Range" value={scan.port_range || 'default'} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Stat label="Task ID" value={scan.task_id || '-'} />
          </Grid>

          {active && (
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
                <Box sx={{ flexGrow: 1 }}>
                  <LinearProgress variant="determinate" value={scan.progress} />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 48 }}>
                  {Math.round(scan.progress)}%
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                &gt; {scan.current_host || 'Initializing...'}
              </Typography>
            </Grid>
          )}
        </Grid>
      </Paper>

      {/* Results */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <TerminalIcon color="primary" fontSize="small" />
        <Typography variant="h5" component="h2">
          &gt; DISCOVERED_HOSTS
        </Typography>
        <Chip label={resultCount} size="small" color="primary" variant="outlined" />
      </Box>

      {scan.results?.map((result: ScanResult) => (
        <Accordion key={result.id} defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <ComputerIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="subtitle1">{result.ip_address}</Typography>
                {result.hostname && (
                  <Typography variant="caption" color="text.secondary">
                    {result.hostname}
                  </Typography>
                )}
              </Box>
              <Chip
                label={`${result.ports.length} PORTS`}
                size="small"
                variant="outlined"
                color="primary"
                sx={{ mr: 2 }}
              />
              {result.os_name && (
                <Chip
                  icon={<SpeedIcon />}
                  label={`${result.os_name} (${result.os_accuracy ?? '?'}%)`}
                  size="small"
                  sx={{ mr: 2 }}
                />
              )}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Port</TableCell>
                    <TableCell>Protocol</TableCell>
                    <TableCell>State</TableCell>
                    <TableCell>Service</TableCell>
                    <TableCell>Version</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.ports.map((port) => (
                    <TableRow key={`${port.port_number}-${port.protocol}`}>
                      <TableCell>{port.port_number}</TableCell>
                      <TableCell>{port.protocol}</TableCell>
                      <TableCell>
                        <Chip
                          label={port.state}
                          color={getPortStateColor(port.state)}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{port.service_name || 'unknown'}</TableCell>
                      <TableCell>{port.service_version || '-'}</TableCell>
                    </TableRow>
                  ))}
                  {result.ports.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No open ports found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>
      ))}

      {resultCount === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            {active ? 'Scan in progress. Results will appear here.' : 'No active hosts found.'}
          </Typography>
        </Paper>
      )}
    </Container>
  );
}
