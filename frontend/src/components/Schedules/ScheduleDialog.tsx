import { useEffect, useState } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import {
  Close as CloseIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import type { Schedule, ScheduleCreateRequest } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import {
  CRON_PRESETS,
  buildScanConfig,
  emptyScheduleForm,
  scheduleToForm,
  validateScheduleForm,
  type ScheduleFormErrors,
  type ScheduleFormInput,
} from '@/utils/schedule';

interface ScheduleDialogProps {
  open: boolean;
  schedule: Schedule | null;
  onClose: () => void;
  onSubmit: (data: ScheduleCreateRequest) => Promise<void>;
}

const SCAN_TYPES = [
  { value: 'tcp_connect', label: 'TCP Connect (Recommended)' },
  { value: 'tcp_syn', label: 'TCP SYN (Requires admin)' },
  { value: 'udp', label: 'UDP (Slower, requires admin)' },
  { value: 'comprehensive', label: 'Comprehensive (Requires admin)' },
];

export default function ScheduleDialog({
  open,
  schedule,
  onClose,
  onSubmit,
}: ScheduleDialogProps) {
  const [form, setForm] = useState<ScheduleFormInput>(emptyScheduleForm);
  const [errors, setErrors] = useState<ScheduleFormErrors>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setForm(schedule ? scheduleToForm(schedule) : emptyScheduleForm());
    setErrors({});
    setError(null);
  }, [open, schedule]);

  const update = <K extends keyof ScheduleFormInput>(
    key: K,
    value: ScheduleFormInput[K]
  ) => {
    setForm((previous) => ({ ...previous, [key]: value }));

    const errorKey: keyof ScheduleFormErrors | null =
      key === 'name'
        ? 'name'
        : key === 'target'
          ? 'target'
          : key === 'port_range'
            ? 'portRange'
            : key === 'cron_expression'
              ? 'cron'
              : null;

    if (errorKey) {
      setErrors((previous) => ({ ...previous, [errorKey]: undefined }));
    }
  };

  const handleClose = () => {
    if (!loading) onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    const nextErrors = validateScheduleForm(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      await onSubmit({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        scan_config: buildScanConfig(form),
        cron_expression: form.cron_expression.trim(),
        enabled: form.enabled,
      });
      onClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to save schedule'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle component="div">
          <Typography variant="h6" component="span" sx={{ color: 'primary.main' }}>
            {schedule ? '> EDIT_SCHEDULE' : '> NEW_SCHEDULE'}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            [CELERY BEAT // TIMES IN UTC]
          </Typography>
        </DialogTitle>

        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            <Alert severity="warning" icon={false}>
              <AlertTitle sx={{ mb: 0.5 }}>Authorization required</AlertTitle>
              <Typography variant="body2">
                Scheduled scans run unattended. Only schedule targets you own or
                have explicit permission to scan.
              </Typography>
            </Alert>

            <TextField
              label="Schedule Name"
              value={form.name}
              onChange={(event) => update('name', event.target.value)}
              required
              fullWidth
              autoFocus
              error={Boolean(errors.name)}
              helperText={errors.name}
              inputProps={{ maxLength: 255 }}
            />

            <TextField
              label="Description (Optional)"
              value={form.description}
              onChange={(event) => update('description', event.target.value)}
              fullWidth
            />

            <TextField
              label="Target"
              value={form.target}
              onChange={(event) => update('target', event.target.value)}
              required
              fullWidth
              error={Boolean(errors.target)}
              placeholder="192.168.1.0/24"
              helperText={errors.target ?? 'IP address, CIDR range, or hostname'}
            />

            <FormControl fullWidth required>
              <InputLabel>Scan Type</InputLabel>
              <Select
                value={form.scan_type}
                label="Scan Type"
                onChange={(event) => update('scan_type', event.target.value)}
              >
                {SCAN_TYPES.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Port Range (Optional)"
              value={form.port_range}
              onChange={(event) => update('port_range', event.target.value)}
              fullWidth
              error={Boolean(errors.portRange)}
              placeholder="1-1000 or 22,80,443"
              helperText={errors.portRange ?? 'Defaults to the scan type profile'}
            />

            <Box>
              <TextField
                label="Cron Expression"
                value={form.cron_expression}
                onChange={(event) => update('cron_expression', event.target.value)}
                required
                fullWidth
                error={Boolean(errors.cron)}
                helperText={errors.cron ?? 'Five fields: minute hour day month weekday'}
              />
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                {CRON_PRESETS.map((preset) => (
                  <Chip
                    key={preset.value}
                    label={preset.label}
                    size="small"
                    variant={form.cron_expression === preset.value ? 'filled' : 'outlined'}
                    onClick={() => update('cron_expression', preset.value)}
                  />
                ))}
              </Box>
            </Box>

            <Box
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                p: 1.5,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Typography variant="caption" color="primary.main" sx={{ mb: 0.5 }}>
                // OPTIONS
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.service_detection}
                    onChange={(event) =>
                      update('service_detection', event.target.checked)
                    }
                  />
                }
                label="Service Detection"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.os_detection}
                    onChange={(event) => update('os_detection', event.target.checked)}
                  />
                }
                label="OS Detection"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={form.aggressive}
                    onChange={(event) => update('aggressive', event.target.checked)}
                  />
                }
                label="Aggressive Mode"
              />
            </Box>

            <FormControlLabel
              control={
                <Checkbox
                  checked={form.enabled}
                  onChange={(event) => update('enabled', event.target.checked)}
                />
              }
              label="Enabled"
            />
          </Box>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={handleClose}
            disabled={loading}
            startIcon={<CloseIcon />}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            startIcon={<SaveIcon />}
          >
            {loading ? 'Saving...' : schedule ? 'Save Changes' : 'Create Schedule'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
