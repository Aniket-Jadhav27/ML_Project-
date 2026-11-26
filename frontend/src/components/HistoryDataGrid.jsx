import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import HistoryToggleOffIcon from '@mui/icons-material/HistoryToggleOff';
import DeleteIcon from '@mui/icons-material/Delete';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import { chatAPI } from '../services/api';

export default function HistoryDataGrid({ user }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await chatAPI.getHistory();
      const formatted = (data || []).map((row, idx) => ({
        ...row,
        id: row.id || idx + 1,
      }));
      setHistory(formatted);
    } catch (err) {
      console.error('Failed to load history', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [user]);

  const handleDelete = async (id) => {
    try {
      await chatAPI.deleteHistoryItem(id);
      setHistory((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      console.error('Failed to delete history item', err);
    }
  };

  const handleClearAll = async () => {
    try {
      await chatAPI.clearHistory();
      setHistory([]);
      setConfirmClearOpen(false);
    } catch (err) {
      console.error('Failed to clear history', err);
    }
  };

  const filteredHistory = history.filter((h) => {
    const s = search.toLowerCase();
    return (
      h.question?.toLowerCase().includes(s) ||
      h.answer?.toLowerCase().includes(s) ||
      h.username?.toLowerCase().includes(s)
    );
  });

  const columns = [
    {
      field: 'id',
      headerName: 'Log #',
      width: 70,
    },
    {
      field: 'timestamp',
      headerName: 'Timestamp',
      width: 170,
      renderCell: (params) => (
        <Typography variant="body2" color="text.secondary">
          {params.value ? new Date(params.value).toLocaleString() : '-'}
        </Typography>
      ),
    },
    {
      field: 'username',
      headerName: 'User',
      width: 110,
      renderCell: (params) => (
        <Chip label={params.value || 'guest'} size="small" variant="outlined" />
      ),
    },
    {
      field: 'question',
      headerName: 'Question',
      width: 240,
      renderCell: (params) => (
        <Tooltip title={params.value || ''} arrow>
          <Typography variant="body2" fontWeight={600} sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {params.value}
          </Typography>
        </Tooltip>
      ),
    },
    {
      field: 'answer',
      headerName: 'AI Generated Answer',
      flex: 1,
      minWidth: 300,
      renderCell: (params) => (
        <Tooltip title={params.value || ''} arrow placement="bottom-start">
          <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {params.value}
          </Typography>
        </Tooltip>
      ),
    },
    {
      field: 'chunkCount',
      headerName: 'Citations',
      width: 100,
      renderCell: (params) => (
        <Chip label={`${params.value || 0} chunks`} size="small" color="info" />
      ),
    },
    {
      field: 'actions',
      headerName: 'Delete',
      width: 80,
      sortable: false,
      renderCell: (params) => (
        <Tooltip title="Delete this entry">
          <IconButton
            size="small"
            color="error"
            onClick={() => handleDelete(params.row.id)}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ),
    },
  ];

  return (
    <Box className="datagrid-card">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <HistoryToggleOffIcon color="primary" sx={{ fontSize: 28 }} />
          <Box>
            <Typography variant="h6" fontWeight={700}>
              MySQL Q&A Query Logs
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Persisted question-answer records ({history.length} saved)
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <TextField
            size="small"
            placeholder="Search questions or answers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
            sx={{ width: 260 }}
          />

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchHistory}
            disabled={loading}
            size="small"
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Refresh
          </Button>

          {history.length > 0 && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteSweepIcon />}
              onClick={() => setConfirmClearOpen(true)}
              size="small"
              sx={{ textTransform: 'none', borderRadius: 2 }}
            >
              Clear All
            </Button>
          )}
        </Box>
      </Box>

      <Box sx={{ height: 560, width: '100%' }}>
        <DataGrid
          rows={filteredHistory}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          disableRowSelectionOnClick
          sx={{
            border: 'none',
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#f1f5f9',
              fontWeight: 700,
            },
            '& .MuiDataGrid-row:hover': {
              backgroundColor: '#f8fafc',
            },
          }}
        />
      </Box>

      {/* Confirmation Dialog for Clear All */}
      <Dialog open={confirmClearOpen} onClose={() => setConfirmClearOpen(false)}>
        <DialogTitle>Clear All Q&A History?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete all saved question and answer records from MySQL? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClearOpen(false)}>Cancel</Button>
          <Button onClick={handleClearAll} color="error" variant="contained">
            Yes, Delete All
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
