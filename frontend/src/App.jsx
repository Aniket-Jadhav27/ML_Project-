import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, Alert, Button } from '@mui/material';
import Navbar from './components/Navbar';
import ChatView from './components/ChatView';
import ChunkDataGrid from './components/ChunkDataGrid';
import HistoryDataGrid from './components/HistoryDataGrid';
import AuthModal from './components/AuthModal';
import UploadModal from './components/UploadModal';
import { authAPI } from './services/api';
import './styles/main.scss';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      dark: '#115293',
      light: '#4791db',
    },
    secondary: {
      main: '#9c27b0',
    },
    background: {
      default: '#f8fafc',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
  },
});

export default function App() {
  const [currentTab, setCurrentTab] = useState('chat');
  const [user, setUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadCounter, setUploadCounter] = useState(0);

  useEffect(() => {
    // Check saved auth state
    const savedUser = localStorage.getItem('rag_user');
    const token = localStorage.getItem('rag_token');
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
        // Verify token with backend
        authAPI
          .getCurrentUser()
          .then((verified) => setUser(verified))
          .catch(() => {
            setUser(null);
            localStorage.removeItem('rag_token');
            localStorage.removeItem('rag_user');
          });
      } catch (e) {
        setUser(null);
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('rag_token');
    localStorage.removeItem('rag_user');
    setUser(null);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="app-container">
        <Navbar
          currentTab={currentTab}
          onTabChange={setCurrentTab}
          user={user}
          onOpenAuth={() => setAuthOpen(true)}
          onLogout={handleLogout}
          onOpenUpload={() => {
            if (!user) {
              setAuthOpen(true);
            } else {
              setUploadOpen(true);
            }
          }}
        />

        <Box className="main-content">
          {!user && (
            <Alert
              severity="info"
              sx={{ mb: 3, borderRadius: 2 }}
              action={
                <Button color="inherit" size="small" onClick={() => setAuthOpen(true)}>
                  Sign In / Register
                </Button>
              }
            >
              Sign in to manage and query your own isolated documents and vector indexes!
            </Alert>
          )}

          <Box sx={{ display: currentTab === 'chat' ? 'contents' : 'none' }}>
            <ChatView user={user} onRequireAuth={() => setAuthOpen(true)} />
          </Box>
          {currentTab === 'chunks' && (
            <ChunkDataGrid
              key={`${user?.username || 'guest'}-${uploadCounter}`}
              user={user}
              onRequireAuth={() => setAuthOpen(true)}
            />
          )}
          {currentTab === 'history' && <HistoryDataGrid user={user} />}
        </Box>

        <AuthModal
          open={authOpen}
          onClose={() => setAuthOpen(false)}
          onAuthSuccess={(loggedInUser) => setUser(loggedInUser)}
        />

        <UploadModal
          open={uploadOpen}
          onClose={() => setUploadOpen(false)}
          onUploadComplete={() => {
            setUploadCounter((c) => c + 1);
          }}
        />
      </Box>
    </ThemeProvider>
  );
}
