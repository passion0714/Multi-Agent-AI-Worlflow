import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
  Link,
} from '@mui/material';
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarExport,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
} from '@mui/x-data-grid';
import {
  PlayArrow as PlayIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { format } from 'date-fns';
import api from '../services/api';

const callStatusColors = {
  initiated: 'info',
  ringing: 'warning',
  answered: 'success',
  completed: 'success',
  failed: 'error',
  'no-answer': 'warning',
  busy: 'warning',
};

function CustomToolbar() {
  return (
    <GridToolbarContainer>
      <GridToolbarFilterButton />
      <GridToolbarDensitySelector />
      <GridToolbarExport />
    </GridToolbarContainer>
  );
}

function CallLogs() {
  const { data: callLogs, isLoading } = useQuery(
    'callLogs',
    () => api.get('/call-logs/').then(res => res.data),
    { refetchInterval: 10000 }
  );

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'lead_id', headerName: 'Lead ID', width: 100 },
    { field: 'phone_number', headerName: 'Phone', width: 130 },
    {
      field: 'call_status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value?.toUpperCase() || 'UNKNOWN'}
          color={callStatusColors[params.value] || 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'call_duration',
      headerName: 'Duration',
      width: 100,
      renderCell: (params) => formatDuration(params.value),
    },
    {
      field: 'recording_url',
      headerName: 'Recording',
      width: 120,
      renderCell: (params) => (
        params.value ? (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton
              size="small"
              onClick={() => window.open(params.value, '_blank')}
              title="Play Recording"
            >
              <PlayIcon />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => {
                const link = document.createElement('a');
                link.href = params.value;
                link.download = `recording_${params.row.id}.mp3`;
                link.click();
              }}
              title="Download Recording"
            >
              <DownloadIcon />
            </IconButton>
          </Box>
        ) : null
      ),
    },
    {
      field: 'recording_s3_key',
      headerName: 'S3 Key',
      width: 200,
      renderCell: (params) => (
        params.value ? (
          <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
            {params.value}
          </Typography>
        ) : null
      ),
    },
    {
      field: 'started_at',
      headerName: 'Started',
      width: 150,
      renderCell: (params) => (
        params.value ? format(new Date(params.value), 'MMM dd, yyyy HH:mm') : 'N/A'
      ),
    },
    {
      field: 'ended_at',
      headerName: 'Ended',
      width: 150,
      renderCell: (params) => (
        params.value ? format(new Date(params.value), 'MMM dd, yyyy HH:mm') : 'N/A'
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 150,
      renderCell: (params) => (
        format(new Date(params.value), 'MMM dd, yyyy HH:mm')
      ),
    },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Call Logs
      </Typography>
      
      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={callLogs || []}
          columns={columns}
          pageSize={25}
          rowsPerPageOptions={[25, 50, 100]}
          checkboxSelection
          disableSelectionOnClick
          components={{
            Toolbar: CustomToolbar,
          }}
          loading={isLoading}
        />
      </Paper>
    </Box>
  );
}

export default CallLogs; 