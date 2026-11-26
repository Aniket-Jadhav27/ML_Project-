import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Alert,
  LinearProgress,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { documentAPI } from '../services/api';

export default function UploadModal({ open, onClose, onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF, TXT, or MD file first.');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const res = await documentAPI.upload(file);
      setResult(res);
      if (onUploadComplete) {
        onUploadComplete(res);
      }
      setTimeout(() => {
        setFile(null);
        setResult(null);
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: 3 } }}>
      <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
        Upload Document for Vector Indexing
      </DialogTitle>

      <DialogContent sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {error && <Alert severity="error">{error}</Alert>}
        {result && (
          <Alert severity="success">
            Indexed successfully! Created {result.chunkCount || 'new'} chunks in ChromaDB.
          </Alert>
        )}

        <Box
          sx={{
            border: '2px dashed #90caf9',
            borderRadius: 3,
            p: 4,
            textAlign: 'center',
            backgroundColor: '#f8fafc',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            '&:hover': {
              backgroundColor: '#eff6ff',
            },
          }}
          component="label"
        >
          <input
            type="file"
            accept=".pdf,.txt,.md"
            hidden
            onChange={handleFileChange}
            disabled={uploading}
          />
          <CloudUploadIcon sx={{ fontSize: 48, color: '#1976d2', mb: 1 }} />
          <Typography variant="body1" fontWeight={600}>
            {file ? file.name : 'Click or Drag & Drop PDF / TXT / MD to Upload'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Supported formats: .pdf, .txt, .md (Max 50MB)
          </Typography>

          {file && (
            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
              <InsertDriveFileIcon color="primary" fontSize="small" />
              <Typography variant="caption" fontWeight={500}>
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </Typography>
            </Box>
          )}
        </Box>

        {uploading && (
          <Box sx={{ width: '100%', mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Extracting pages, generating nomic-embed-text embeddings, and saving to ChromaDB...
            </Typography>
            <LinearProgress />
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} disabled={uploading} color="inherit">
          Close
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          color="primary"
          disabled={!file || uploading}
          sx={{ px: 3, fontWeight: 600 }}
        >
          {uploading ? 'Indexing...' : 'Upload & Index'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

