import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PauseCircleOutline as PauseIcon,
  PlayCircleOutline as PlayIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { scheduleApi } from '@/services/api';
import type { Schedule, ScheduleCreateRequest } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { formatScheduleTime, summarizeScanConfig } from '@/utils/schedule';
import ScheduleDialog from './ScheduleDialog';

function Schedules() {
  const navigate = useNavigate();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Schedule | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const loadSchedules = useCallback(async () => {
    try {
      setError(null);
      const data = await scheduleApi.listSchedules({ limit: 100 });
      setSchedules(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load schedules'));
    }
  }, []);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        const data = await scheduleApi.listSchedules({ limit: 100 });
        if (active) setSchedules(data);
      } catch (err: unknown) {
        if (active) setError(getErrorMessage(err, 'Failed to load schedules'));
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadSchedules();
    setRefreshing(false);
  };

  const handleOpenCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = (schedule: Schedule) => {
    setEditing(schedule);
    setDialogOpen(true);
  };

  const handleSubmit = async (data: ScheduleCreateRequest) => {
    if (editing) {
      await scheduleApi.updateSchedule(editing.id, data);
    } else {
      await scheduleApi.createSchedule(data);
    }
    await loadSchedules();
  };

  const handleToggle = async (schedule: Schedule) => {
    setTogglingId(schedule.id);
    try {
      const updated = await scheduleApi.updateSchedule(schedule.id, {
        enabled: !schedule.enabled,
      });
      setSchedules((previous) =>
        previous.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to update schedule'));
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;

    setDeleting(true);
    try {
      await scheduleApi.deleteSchedule(pendingDelete.id);
      setPendingDelete(null);
      await loadSchedules();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to delete schedule'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
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
                &gt; SCHEDULE_OPERATIONS
              </Typography>
              <Typography variant="caption" color="text.secondary">
                [CELERY BEAT // DISPATCH EVERY 60s // TIMES IN UTC]
              </Typography>
            </Box>
          </Box>

          <Box>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={refreshing || loading}
              sx={{ mr: 2 }}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleOpenCreate}
            >
              New Schedule
            </Button>
          </Box>
        </Box>

        <Alert severity="info" sx={{ mb: 3 }}>
          Due schedules are dispatched by the backend every 60 seconds and create a
          new scan using the stored configuration. Only schedule networks you are
          authorized to scan.
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Paper sx={{ p: 3 }}>
            <LinearProgress />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              &gt; LOADING_SCHEDULES...
            </Typography>
          </Paper>
        ) : schedules.length === 0 ? (
          <Paper sx={{ p: 6, textAlign: 'center' }}>
            <ScheduleIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              &gt; NO_SCHEDULES_DETECTED
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Create a schedule to run recurring scans automatically.
            </Typography>
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreate}>
              Create Schedule
            </Button>
          </Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Schedule</TableCell>
                  <TableCell>Configuration</TableCell>
                  <TableCell>Cron</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Run</TableCell>
                  <TableCell>Next Run</TableCell>
                  <TableCell align="right">Runs</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {schedules.map((schedule) => (
                  <TableRow key={schedule.id} hover>
                    <TableCell>
                      <Typography variant="body2">{schedule.name}</Typography>
                      {schedule.description && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          {schedule.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {summarizeScanConfig(schedule.scan_config)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" sx={{ color: 'primary.main' }}>
                        {schedule.cron_expression}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={schedule.enabled ? 'ENABLED' : 'DISABLED'}
                        color={schedule.enabled ? 'success' : 'default'}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {formatScheduleTime(schedule.last_run_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {formatScheduleTime(schedule.next_run_at)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="caption" color="text.secondary">
                        {schedule.total_runs} / {schedule.successful_runs} ok /{' '}
                        {schedule.failed_runs} fail
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton
                          size="small"
                          aria-label={`Edit ${schedule.name}`}
                          onClick={() => handleOpenEdit(schedule)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={schedule.enabled ? 'Disable' : 'Enable'}>
                        <span>
                          <IconButton
                            size="small"
                            aria-label={
                              schedule.enabled
                                ? `Disable ${schedule.name}`
                                : `Enable ${schedule.name}`
                            }
                            onClick={() => handleToggle(schedule)}
                            disabled={togglingId === schedule.id}
                          >
                            {schedule.enabled ? (
                              <PauseIcon fontSize="small" />
                            ) : (
                              <PlayIcon fontSize="small" />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          aria-label={`Delete ${schedule.name}`}
                          onClick={() => setPendingDelete(schedule)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Container>

      <ScheduleDialog
        open={dialogOpen}
        schedule={editing}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
      />

      <Dialog open={pendingDelete !== null} onClose={() => setPendingDelete(null)}>
        <DialogTitle>&gt; DELETE_SCHEDULE</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete schedule “{pendingDelete?.name}”? Existing scans created by it are
            kept.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDelete(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            color="error"
            variant="contained"
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default Schedules;
