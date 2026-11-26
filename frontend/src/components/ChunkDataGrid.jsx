import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, TextField, InputAdornment, Chip, Tooltip, Alert } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import LayersIcon from '@mui/icons-material/Layers';
import TableChartIcon from '@mui/icons-material/TableChart';
import DescriptionIcon from '@mui/icons-material/Description';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { documentAPI } from '../services/api';

export default function ChunkDataGrid({ user, onRequireAuth }) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const fetchChunks = async () => {
    if (!user) {
      setChunks([]);
      return;
    }
    setLoading(true);
    try {
      const data = await documentAPI.getChunks();
      setChunks(data || []);
    } catch (err) {
      console.error('Failed to load chunks', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchChunks();
    } else {
      setChunks([]);
    }
  }, [user]);

  const filteredChunks = chunks.filter((c) => {
    const s = search.toLowerCase();
    return (
      c.text?.toLowerCase().includes(s) ||
      c.source?.toLowerCase().includes(s) ||
      c.chunkType?.toLowerCase().includes(s) ||
      String(c.chunkId).includes(s) ||
      String(c.page).includes(s)
    );
  });

  const columns = [
    {
      field: 'chunkId',
      headerName: 'Chunk ID',
      width: 110,
      renderCell: (params) => (
        <Chip
          label={`#${params.value}`}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ fontWeight: 600 }}
        />
      ),
    },
    {
      field: 'chunkType',
      headerName: 'Content Type',
      width: 140,
      renderCell: (params) => {
        const isTable = params.value === 'table';
        return (
          <Chip
            icon={isTable ? <TableChartIcon fontSize="small" /> : <DescriptionIcon fontSize="small" />}
            label={isTable ? `Table #${params.row.tableId || 1}` : 'Body Text'}
            size="small"
            color={isTable ? 'success' : 'default'}
            variant={isTable ? 'filled' : 'outlined'}
            sx={{ fontWeight: 600 }}
          />
        );
      },
    },
    {
      field: 'page',
      headerName: 'Page',
      width: 90,
      renderCell: (params) => (
        <Typography variant="body2" fontWeight={600} color="text.secondary">
          p. {params.value || 1}
        </Typography>
      ),
    },
    {
      field: 'source',
      headerName: 'Source Document',
      width: 180,
      renderCell: (params) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
          {params.value || 'document.pdf'}
        </Typography>
      ),
    },
    {
      field: 'charRange',
      headerName: 'Char Span',
      width: 130,
      valueGetter: (value, row) => `${row.startChar || 0} - ${row.endChar || 0}`,
    },
    {
      field: 'text',
      headerName: 'Chunk Content Preview',
      flex: 1,
      minWidth: 350,
      renderCell: (params) => (
        <Tooltip title={params.value || ''} arrow placement="bottom-start">
          <Typography
            variant="body2"
            sx={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: '#334155',
            }}
          >
            {params.value}
          </Typography>
        </Tooltip>
      ),
    },
  ];

  return (
    <Box className="datagrid-card">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <LayersIcon color="primary" sx={{ fontSize: 28 }} />
          <Box>
            <Typography variant="h6" fontWeight={700}>
              ChromaDB Document Chunks Explorer
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {user
                ? `Account: ${user.username} • Total Chunks Indexed: ${chunks.length} segments with nomic-embed-text vectors`
                : 'Sign in to view your account\'s isolated document chunks'}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <TextField
            size="small"
            placeholder="Search text, page, or chunk..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            disabled={!user}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
            sx={{ width: 280 }}
          />

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchChunks}
            disabled={loading || !user}
            size="small"
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {!user ? (
        <Box
          sx={{
            py: 8,
            px: 3,
            textAlign: 'center',
            backgroundColor: '#f8fafc',
            borderRadius: 3,
            border: '1px dashed #cbd5e1',
          }}
        >
          <LockOutlinedIcon sx={{ fontSize: 48, color: '#94a3b8', mb: 1.5 }} />
          <Typography variant="h6" fontWeight={600} color="#334155" gutterBottom>
            Sign in to Explore Document Chunks
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 460, mx: 'auto', mb: 2.5 }}>
            Each user account has an isolated vector space in ChromaDB. Please sign in or register to inspect your uploaded document chunks, tokens, and bounding spans.
          </Typography>
          {onRequireAuth && (
            <Button variant="contained" onClick={onRequireAuth} sx={{ textTransform: 'none', px: 3 }}>
              Sign In / Register
            </Button>
          )}
        </Box>
      ) : (
        <Box sx={{ height: 560, width: '100%' }}>
          <DataGrid
            rows={filteredChunks}
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
      )}
    </Box>
  );
}

