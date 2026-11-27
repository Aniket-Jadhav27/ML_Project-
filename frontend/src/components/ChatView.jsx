import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  CircularProgress,
  Avatar,
  Chip,
  Tooltip,
  Button,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import DescriptionIcon from '@mui/icons-material/Description';
import TableChartIcon from '@mui/icons-material/TableChart';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import DeleteIcon from '@mui/icons-material/Delete';
import { chatAPI } from '../services/api';

const DEFAULT_WELCOME_MESSAGE = {
  id: 1,
  sender: 'assistant',
  text: 'Hello! How can i help you. Ask me any question about your uploaded document, and I will cite the specific page numbers and chunk segments!',
  chunks: [],
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
};

export default function ChatView({ user, onRequireAuth }) {
  const [messages, setMessages] = useState([DEFAULT_WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    setMessages([DEFAULT_WELCOME_MESSAGE]);
  }, [user?.username]);

  const handleClearChat = () => {
    setMessages([DEFAULT_WELCOME_MESSAGE]);
  };

  const handleDeleteMessage = (id) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  const handleSend = async (e) => {
    e?.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    if (!user) {
      onRequireAuth();
      return;
    }

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatAPI.ask(query);
      const assistantMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: res.answer || 'No response returned from the model.',
        chunks: res.chunks || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errMsg = err.response?.data?.message || err.message || 'Error communicating with server';
      const errorMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: `⚠️ Error: ${errMsg}`,
        chunks: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="chat-wrapper">
      {/* Chat Header Toolbar */}
      <Box
        sx={{
          px: 3,
          py: 1.5,
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#ffffff',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
          <SmartToyIcon color="primary" fontSize="small" />
          <Typography variant="subtitle2" fontWeight={700}>
            Live Document Q&A
          </Typography>
          <Chip
            label="Auto-saved to MySQL"
            size="small"
            color="success"
            variant="outlined"
            sx={{ height: 22, fontSize: '0.72rem', fontWeight: 600 }}
          />
        </Box>

        {messages.length > 1 && (
          <Button
            size="small"
            startIcon={<DeleteSweepIcon fontSize="small" />}
            onClick={handleClearChat}
            color="inherit"
            sx={{
              textTransform: 'none',
              fontSize: '0.8rem',
              color: '#64748b',
              '&:hover': { color: '#ef4444' },
            }}
          >
            Clear Screen
          </Button>
        )}
      </Box>

      {/* Messages Scroll Area */}
      <Box className="chat-messages">
        {messages.map((msg) => (
          <Box
            key={msg.id}
            className={`message-row ${msg.sender === 'user' ? 'user-row' : 'assistant-row'}`}
            sx={{ position: 'relative', '&:hover .delete-btn': { opacity: 1 } }}
          >
            <Avatar
              sx={{
                bgcolor: msg.sender === 'user' ? '#1976d2' : '#0284c7',
                width: 36,
                height: 36,
              }}
            >
              {msg.sender === 'user' ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
            </Avatar>

            <Box className={`message-bubble ${msg.sender === 'user' ? 'user-bubble' : 'assistant-bubble'}`}>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {msg.text}
              </Typography>

              {/* Citations / Supporting Chunks */}
              {msg.chunks && msg.chunks.length > 0 && (
                <Box className="chunks-citation-container">
                  <Typography variant="caption" sx={{ width: '100%', fontWeight: 700, color: '#475569', mb: 0.5 }}>
                    Sources & Document Evidence:
                  </Typography>
                  {msg.chunks.map((chunk, idx) => (
                    <Tooltip
                      key={idx}
                      title={
                        <Box sx={{ p: 0.5, maxWidth: 300 }}>
                          <Typography variant="caption" fontWeight={700}>
                            Chunk #{chunk.chunkId} (Page {chunk.page}):
                          </Typography>
                          <Typography variant="caption" display="block" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                            "{chunk.text?.slice(0, 180)}..."
                          </Typography>
                        </Box>
                      }
                      arrow
                    >
                      <Box
                        className="chunk-pill"
                        sx={{
                          backgroundColor: chunk.chunkType === 'table' ? '#ecfdf5' : undefined,
                          borderColor: chunk.chunkType === 'table' ? '#10b981' : undefined,
                        }}
                      >
                        {chunk.chunkType === 'table' ? (
                          <TableChartIcon sx={{ fontSize: 13, color: '#059669' }} />
                        ) : (
                          <DescriptionIcon sx={{ fontSize: 13 }} />
                        )}
                        <span>{chunk.chunkType === 'table' ? `Table #${chunk.tableId || 1}` : `Chunk ${chunk.chunkId}`}</span>
                        <span>• Page {chunk.page}</span>
                        {chunk.distance !== undefined && (
                          <span style={{ opacity: 0.75 }}>({chunk.distance.toFixed(3)})</span>
                        )}
                      </Box>
                    </Tooltip>
                  ))}
                </Box>
              )}

              <Box sx={{ display: 'flex', justifyContent: msg.sender === 'user' ? 'flex-end' : 'space-between', alignItems: 'center', mt: 0.8 }}>
                <Typography
                  variant="caption"
                  sx={{
                    opacity: 0.7,
                    fontSize: '0.72rem',
                  }}
                >
                  {msg.timestamp}
                </Typography>

                {msg.id !== 1 && (
                  <Tooltip title="Delete message">
                    <IconButton
                      size="small"
                      className="delete-btn"
                      onClick={() => handleDeleteMessage(msg.id)}
                      sx={{
                        opacity: 0.3,
                        transition: 'opacity 0.2s',
                        p: 0.2,
                        ml: 1,
                        color: msg.sender === 'user' ? '#ffffff' : '#64748b',
                        '&:hover': { opacity: 1, color: '#ef4444' },
                      }}
                    >
                      <DeleteIcon sx={{ fontSize: 15 }} />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </Box>
          </Box>
        ))}

        {loading && (
          <Box className="message-row assistant-row">
            <Avatar sx={{ bgcolor: '#0284c7', width: 36, height: 36 }}>
              <SmartToyIcon fontSize="small" />
            </Avatar>
            <Box className="message-bubble assistant-bubble" sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">
                Ollama is synthesizing an answer from retrieved document chunks...
              </Typography>
            </Box>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Form Bar */}
      <Box component="form" onSubmit={handleSend} className="chat-input-bar">
        <TextField
          placeholder={user ? "Ask a question about the document... (Press Enter)" : "Please sign in to ask questions"}
          variant="outlined"
          size="small"
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || !user}
          sx={{
            backgroundColor: '#f8fafc',
            borderRadius: 2,
            '& fieldset': { borderColor: '#e2e8f0' },
          }}
        />
        <IconButton
          type="submit"
          color="primary"
          disabled={!input.trim() || loading || !user}
          sx={{
            bgcolor: '#1976d2',
            color: '#ffffff',
            '&:hover': { bgcolor: '#1565c0' },
            '&.Mui-disabled': { bgcolor: '#e2e8f0', color: '#94a3b8' },
            p: 1.2,
          }}
        >
          <SendIcon fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
}
