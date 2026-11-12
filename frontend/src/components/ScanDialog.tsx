import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Box,
  Alert,
  AlertTitle,
  Typography,
} from '@mui/material';
import {
  Close as CloseIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';
import { ScanType, type ScanCreateRequest } from '@/types';
import { validateScanForm, type ScanFormErrors } from '@/utils/validation';
import { getErrorMessage } from '@/utils/errors';

interface ScanDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: ScanCreateRequest) => Promise<void>;
}

const emptyForm: ScanCreateRequest = {
  target: '',
  scan_type: ScanType.TCP_CONNECT,
  port_range: '1-1000',
  service_detection: true,
  os_detection: false,
  aggressive: false,
};

export default function ScanDialog({ open, onClose, onSubmit }: ScanDialogProps) {
  const [formData, setFormData] = useState<ScanCreateRequest>(emptyForm);
  const [errors, setErrors] = useState<ScanFormErrors>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setFormData(emptyForm);
    setErrors({});
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const nextErrors = validateScanForm(formData);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setLoading(true);
    try {
      await onSubmit(formData);
      handleClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to create scan'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      resetForm();
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle component="div">
          <Typography variant="h6" component="span" sx={{ color: 'primary.main' }}>
            &gt; NEW_SCAN
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            [CONFIGURE AUTHORIZED RECON]
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
                Only scan networks you own or have explicit permission to scan.
                Unauthorized scanning is illegal.
              </Typography>
            </Alert>

            <TextField
              label="Scan Name (Optional)"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              placeholder="My Network Scan"
              inputProps={{ maxLength: 255 }}
            />

            <TextField
              label="Target"
              value={formData.target}
              onChange={(e) => {
                setFormData({ ...formData, target: e.target.value });
                if (errors.target) setErrors({ ...errors, target: undefined });
              }}
              required
              fullWidth
              autoFocus
              error={Boolean(errors.target)}
              placeholder="192.168.1.0/24 or 192.168.1.1"
              helperText={errors.target ?? 'IP address, CIDR range, or hostname'}
            />

            <FormControl fullWidth required>
              <InputLabel>Scan Type</InputLabel>
              <Select
                value={formData.scan_type}
                label="Scan Type"
                onChange={(e) =>
                  setFormData({ ...formData, scan_type: e.target.value as ScanType })
                }
              >
                <MenuItem value={ScanType.TCP_CONNECT}>
                  TCP Connect (Recommended - No privileges required)
                </MenuItem>
                <MenuItem value={ScanType.TCP_SYN}>
                  SYN Stealth (Requires admin privileges)
                </MenuItem>
                <MenuItem value={ScanType.UDP}>
                  UDP Scan (Slower, requires admin)
                </MenuItem>
                <MenuItem value={ScanType.COMPREHENSIVE}>
                  Comprehensive (All methods, requires admin)
                </MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Port Range"
              value={formData.port_range || ''}
              onChange={(e) => {
                setFormData({ ...formData, port_range: e.target.value });
                if (errors.portRange) setErrors({ ...errors, portRange: undefined });
              }}
              fullWidth
              error={Boolean(errors.portRange)}
              placeholder="1-1000 or 22,80,443"
              helperText={
                errors.portRange ??
                'Port range (e.g., 1-1000) or specific ports (e.g., 22,80,443)'
              }
            />

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
                    checked={formData.service_detection}
                    onChange={(e) =>
                      setFormData({ ...formData, service_detection: e.target.checked })
                    }
                  />
                }
                label="Service Detection (Banner grabbing)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.os_detection}
                    onChange={(e) =>
                      setFormData({ ...formData, os_detection: e.target.checked })
                    }
                  />
                }
                label="OS Detection (May require admin privileges)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.aggressive}
                    onChange={(e) =>
                      setFormData({ ...formData, aggressive: e.target.checked })
                    }
                  />
                }
                label="Aggressive Mode (Faster but more detectable)"
              />
            </Box>
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
            startIcon={<PlayArrowIcon />}
          >
            {loading ? 'Launching...' : 'Start Scan'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
