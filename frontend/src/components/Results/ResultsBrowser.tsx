import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ClearAll as ClearIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { scanApi } from '@/services/api';
import type { ExportFormat, Scan } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { formatStatusLabel, getPortStateColor, getStatusColor, isActiveStatus } from '@/utils/scan';
import {
  EMPTY_RESULT_FILTERS,
  buildExportFilename,
  countHosts,
  filterPortRows,
  flattenResults,
  getProtocolOptions,
  getServiceOptions,
  serviceLabel,
  type ResultFilters,
} from '@/utils/results';

const EXPORT_FORMATS: ExportFormat[] = ['json', 'csv', 'xml'];
const PORT_STATES = ['open', 'closed', 'filtered', 'unknown'];

function scanLabel(scan: Scan): string {
  return `#${scan.id} · ${scan.name || scan.target} · ${formatStatusLabel(scan.status)}`;
}

export default function ResultsBrowser() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedId, setSelectedId] = useState<number | ''>('');
  const [scan, setScan] = useState<Scan | null>(null);
  const [loadingScans, setLoadingScans] = useState(true);
  const [loadingScan, setLoadingScan] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ResultFilters>(EMPTY_RESULT_FILTERS);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);

  const loadScans = useCallback(async () => {
    try {
      setLoadingScans(true);
      setError(null);
      const data = await scanApi.listScans({ limit: 100 });
      setScans(data);
      setSelectedId((previous) => {
        if (previous !== '' && data.some((item) => item.id === previous)) {
          return previous;
        }
        const preferred =
          data.find(
            (item) => item.status === 'completed' && item.total_ports_found > 0
          ) ?? data[0];
        return preferred ? preferred.id : '';
      });
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load scans'));
    } finally {
      setLoadingScans(false);
    }
  }, []);

  useEffect(() => {
    void loadScans();
  }, [loadScans]);

  useEffect(() => {
    if (selectedId === '') {
      setScan(null);
      return;
    }

    let active = true;
    const load = async () => {
      try {
        setLoadingScan(true);
        setError(null);
        setFilters(EMPTY_RESULT_FILTERS);
        const data = await scanApi.getScan(selectedId);
        if (active) setScan(data);
      } catch (err: unknown) {
        if (active) {
          setScan(null);
          setError(getErrorMessage(err, 'Failed to load scan results'));
        }
      } finally {
        if (active) setLoadingScan(false);
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, [selectedId]);

  const rows = useMemo(() => flattenResults(scan?.results), [scan]);
  const filteredRows = useMemo(
    () => filterPortRows(rows, filters),
    [rows, filters]
  );
  const serviceOptions = useMemo(() => getServiceOptions(rows), [rows]);
  const protocolOptions = useMemo(() => getProtocolOptions(rows), [rows]);
  const visibleHosts = useMemo(() => countHosts(filteredRows), [filteredRows]);

  const updateFilter = <K extends keyof ResultFilters>(
    key: K,
    value: ResultFilters[K]
  ) => {
    setFilters((previous) => ({ ...previous, [key]: value }));
  };

  const handleExport = async (format: ExportFormat) => {
    if (!scan) return;

    setExporting(format);
    try {
      const blob = await scanApi.exportScan(scan.id, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = buildExportFilename(scan.id, format);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to export scan results'));
    } finally {
      setExporting(null);
    }
  };

  const activeScan = scan !== null && isActiveStatus(scan.status);
  const filtersActive =
    filters.query.trim().length > 0 ||
    filters.portState !== 'all' ||
    filters.protocol !== 'all' ||
    filters.service !== 'all';

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box
        sx={{
          mb: 3,
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            variant="outlined"
            size="small"
            onClick={() => navigate('/')}
          >
            Back
          </Button>
          <Box>
            <Typography
              variant="h3"
              component="h1"
              sx={{ color: 'primary.main', textShadow: '0 0 12px rgba(0,229,255,0.35)' }}
            >
              &gt; RESULTS_BROWSER
            </Typography>
            <Typography variant="caption" color="text.secondary">
              [PORT INVENTORY // FILTERS // EXPORT]
            </Typography>
          </Box>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => void loadScans()}
          disabled={loadingScans}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loadingScans ? (
        <Paper sx={{ p: 3 }}>
          <LinearProgress />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            &gt; LOADING_SCANS...
          </Typography>
        </Paper>
      ) : scans.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            &gt; NO_SCANS_DETECTED
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Run a scan first to browse and export its results.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/')}>
            Go to Dashboard
          </Button>
        </Paper>
      ) : (
        <>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <FormControl sx={{ minWidth: 320, flexGrow: 1 }} size="small">
                <InputLabel id="scan-select-label">Scan</InputLabel>
                <Select
                  labelId="scan-select-label"
                  label="Scan"
                  value={selectedId === '' ? '' : String(selectedId)}
                  onChange={(event) => setSelectedId(Number(event.target.value))}
                >
                  {scans.map((item) => (
                    <MenuItem key={item.id} value={String(item.id)}>
                      {scanLabel(item)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {scan && (
                <Chip
                  label={formatStatusLabel(scan.status)}
                  color={getStatusColor(scan.status)}
                  size="small"
                />
              )}

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {EXPORT_FORMATS.map((format) => (
                  <Button
                    key={format}
                    size="small"
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    disabled={!scan || rows.length === 0 || exporting !== null}
                    onClick={() => void handleExport(format)}
                  >
                    {exporting === format ? 'Exporting...' : format.toUpperCase()}
                  </Button>
                ))}
              </Box>
            </Box>
          </Paper>

          {loadingScan ? (
            <Paper sx={{ p: 3 }}>
              <LinearProgress />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                &gt; LOADING_RESULTS...
              </Typography>
            </Paper>
          ) : !scan ? (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">Select a scan to inspect its results.</Typography>
            </Paper>
          ) : (
            <>
              {activeScan && (
                <Alert severity="info" sx={{ mb: 3 }}>
                  Scan still in progress. Results may be partial and will refresh when
                  you reload.
                </Alert>
              )}

              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                <Chip label={`HOSTS ${visibleHosts} / ${scan.results?.length ?? 0}`} size="small" />
                <Chip
                  label={`PORTS ${filteredRows.length} / ${rows.length}`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
                <Chip label={scan.target} size="small" variant="outlined" />
                <Chip label={scan.scan_type} size="small" variant="outlined" />
              </Box>

              <Paper sx={{ p: 2, mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                  <TextField
                    size="small"
                    label="Search"
                    value={filters.query}
                    onChange={(event) => updateFilter('query', event.target.value)}
                    placeholder="host, port, service..."
                    InputProps={{ startAdornment: <SearchIcon fontSize="small" /> }}
                    sx={{ minWidth: 240, flexGrow: 1 }}
                  />

                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <InputLabel id="state-filter-label">State</InputLabel>
                    <Select
                      labelId="state-filter-label"
                      label="State"
                      value={filters.portState}
                      onChange={(event) =>
                        updateFilter('portState', event.target.value as string)
                      }
                    >
                      <MenuItem value="all">All states</MenuItem>
                      {PORT_STATES.map((state) => (
                        <MenuItem key={state} value={state}>
                          {state}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <InputLabel id="protocol-filter-label">Protocol</InputLabel>
                    <Select
                      labelId="protocol-filter-label"
                      label="Protocol"
                      value={filters.protocol}
                      onChange={(event) =>
                        updateFilter('protocol', event.target.value as string)
                      }
                    >
                      <MenuItem value="all">All protocols</MenuItem>
                      {protocolOptions.map((protocol) => (
                        <MenuItem key={protocol} value={protocol}>
                          {protocol}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ minWidth: 160 }}>
                    <InputLabel id="service-filter-label">Service</InputLabel>
                    <Select
                      labelId="service-filter-label"
                      label="Service"
                      value={filters.service}
                      onChange={(event) =>
                        updateFilter('service', event.target.value as string)
                      }
                    >
                      <MenuItem value="all">All services</MenuItem>
                      {serviceOptions.map((service) => (
                        <MenuItem key={service} value={service}>
                          {service}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <Button
                    size="small"
                    startIcon={<ClearIcon />}
                    disabled={!filtersActive}
                    onClick={() => setFilters(EMPTY_RESULT_FILTERS)}
                  >
                    Clear
                  </Button>
                </Box>
              </Paper>

              {rows.length === 0 ? (
                <Paper sx={{ p: 6, textAlign: 'center' }}>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    &gt; NO_PORTS_RECORDED
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    This scan did not persist any host results.
                  </Typography>
                </Paper>
              ) : (
                <TableContainer component={Paper}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Host</TableCell>
                        <TableCell>Port</TableCell>
                        <TableCell>Protocol</TableCell>
                        <TableCell>State</TableCell>
                        <TableCell>Service</TableCell>
                        <TableCell>Product / Version</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredRows.map((row) => (
                        <TableRow key={row.key} hover>
                          <TableCell>
                            <Typography variant="body2">
                              {row.hostname || row.ipAddress}
                            </Typography>
                            {row.hostname && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                {row.ipAddress}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>{row.port.port_number}</TableCell>
                          <TableCell>{row.port.protocol}</TableCell>
                          <TableCell>
                            <Chip
                              label={row.port.state}
                              color={getPortStateColor(row.port.state)}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>{serviceLabel(row.port)}</TableCell>
                          <TableCell>
                            {[row.port.service_product, row.port.service_version]
                              .filter(Boolean)
                              .join(' ') || '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                      {filteredRows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} align="center">
                            No ports match the current filters.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </>
          )}
        </>
      )}
    </Container>
  );
}
