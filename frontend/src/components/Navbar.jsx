import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Tabs,
  Tab,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import TableChartIcon from '@mui/icons-material/TableChart';
import ChatIcon from '@mui/icons-material/Chat';
import HistoryIcon from '@mui/icons-material/History';

export default function Navbar({
  currentTab,
  onTabChange,
  user,
  onOpenAuth,
  onLogout,
  onOpenUpload,
}) {
  return (
    <AppBar position="sticky" elevation={1} sx={{ backgroundColor: '#ffffff', color: '#1e293b' }}>
      <Toolbar sx={{ justifyContent: 'space-between', px: { xs: 2, md: 4 } }}>
        {/* Brand & Logo */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <SmartToyIcon sx={{ color: '#1976d2', fontSize: 32 }} />
          <Box>
            <Typography variant="h6" fontWeight={700} sx={{ lineHeight: 1.2, letterSpacing: -0.5 }}>
              DocRAG <span style={{ color: '#1976d2', fontSize: '0.85em' }}>AI</span>
            </Typography>
            {/* <Typography variant="caption" color="text.secondary">
              Spring Boot + Ollama + MySQL
            </Typography> */}
          </Box>
        </Box>

        {/* Navigation Tabs */}
        <Tabs
          value={currentTab}
          onChange={(e, val) => onTabChange(val)}
          textColor="primary"
          indicatorColor="primary"
          sx={{ minHeight: 48 }}
        >
          <Tab icon={<ChatIcon fontSize="small" />} iconPosition="start" label="Chat Q&A" value="chat" />
          <Tab icon={<TableChartIcon fontSize="small" />} iconPosition="start" label="Chunks Explorer" value="chunks" />
          <Tab icon={<HistoryIcon fontSize="small" />} iconPosition="start" label="Query History" value="history" />
        </Tabs>

        {/* User & Upload Actions */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<CloudUploadIcon />}
            onClick={onOpenUpload}
            size="medium"
            sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 600 }}
          >
            Upload Doc
          </Button>

          {user ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                icon={<AccountCircleIcon />}
                label={user.username}
                color="primary"
                variant="outlined"
                sx={{ fontWeight: 600 }}
              />
              <Tooltip title="Log out">
                <IconButton onClick={onLogout} size="small" color="error">
                  <LogoutIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          ) : (
            <Button
              variant="outlined"
              color="primary"
              onClick={onOpenAuth}
              sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 600 }}
            >
              Sign In
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}

