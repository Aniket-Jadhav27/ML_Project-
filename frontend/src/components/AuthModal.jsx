import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Tabs,
  Tab,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined';
import { authAPI } from '../services/api';

export default function AuthModal({ open, onClose, onAuthSuccess }) {
  const [tab, setTab] = useState(0); // 0: Login, 1: Register
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTabChange = (event, newValue) => {
    setTab(newValue);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let data;
      if (tab === 0) {
        data = await authAPI.login(username, password);
      } else {
        data = await authAPI.register(username, email, password);
      }

      if (data && data.token) {
        localStorage.setItem('rag_token', data.token);
        localStorage.setItem('rag_user', JSON.stringify(data.user));
        onAuthSuccess(data.user);
        onClose();
        // Reset form
        setUsername('');
        setEmail('');
        setPassword('');
      }
    } catch (err) {
      let msg = 'Authentication failed';
      if (err.response?.data) {
        if (err.response.data.message) {
          msg = err.response.data.message;
        } else if (err.response.data.errors && Array.isArray(err.response.data.errors) && err.response.data.errors.length > 0) {
          msg = err.response.data.errors.map((e) => e.defaultMessage || e.message).join(', ');
        } else if (err.response.data.error) {
          msg = err.response.data.error;
        }
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: 3 } }}>
      <DialogTitle sx={{ pb: 1, textAlign: 'center' }}>
        <Tabs value={tab} onChange={handleTabChange} centered>
          <Tab icon={<LockOutlinedIcon fontSize="small" />} iconPosition="start" label="Login" />
          <Tab icon={<PersonAddOutlinedIcon fontSize="small" />} iconPosition="start" label="Register" />
        </Tabs>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            label="Username"
            variant="outlined"
            fullWidth
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            helperText={tab === 1 ? "At least 3 characters" : undefined}
            inputProps={{ minLength: tab === 1 ? 3 : 1 }}
          />

          {tab === 1 && (
            <TextField
              label="Email"
              type="email"
              variant="outlined"
              fullWidth
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              helperText="Valid email format (e.g. name@example.com)"
            />
          )}

          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            helperText={tab === 1 ? "At least 4 characters" : undefined}
            inputProps={{ minLength: tab === 1 ? 4 : 1 }}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={loading} color="inherit">
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={loading}
            sx={{ px: 3, fontWeight: 600 }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : tab === 0 ? 'Sign In' : 'Create Account'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

