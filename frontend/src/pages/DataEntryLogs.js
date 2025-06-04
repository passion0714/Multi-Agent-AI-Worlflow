import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
} from '@mui/material';
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarExport,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
} from '@mui/x-data-grid';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Image as ImageIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { format } from 'date-fns';
import api from '../services/api';

function CustomToolbar() {
  return (
    <GridToolbarContainer>
      <GridToolbarFilterButton />
      <GridToolbarDensitySelector />
      <GridToolbarExport />
    </GridToolbarContainer>
  );
}

function DataEntryLogs() {
  const { data: entryLogs, isLoading } = useQuery(
    'dataEntryLogs',
    () => api.get('/data-entry-logs/').then(res => res.data),
    { refetchInterval: 10000 }
  );

  const formatDuration = (startTime, endTime) => {
    if (!startTime || !endTime) return 'N/A';
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end - start;
    const diffSecs = Math.floor(diffMs / 1000);
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'lead_id', headerName: 'Lead ID', width: 100 },
    { field: 'attempt_number', headerName: 'Attempt', width: 100 },
    {
      field: 'success',
      headerName: 'Success',
      width: 100,
      renderCell: (params) => (
        params.value ? (
          <CheckCircleIcon color="success" />
        ) : (
          <ErrorIcon color="error" />
        )
      ),
    },
    {
      field: 'leadhoop_lead_id',
      headerName: 'LeadHoop ID',
      width: 150,
      renderCell: (params) => (
        params.value ? (
          <Chip
            label={params.value}
            color="success"
            size="small"
          />
        ) : null
      ),
    },
    {
      field: 'error_message',
      headerName: 'Error Message',
      width: 300,
      renderCell: (params) => (
        params.value ? (
          <Typography variant="body2" color="error" sx={{ fontSize: '0.75rem' }}>
            {params.value.length > 50 ? `${params.value.substring(0, 50)}...` : params.value}
          </Typography>
        ) : null
      ),
    },
    {
      field: 'screenshot_path',
      headerName: 'Screenshot',
      width: 120,
      renderCell: (params) => (
        params.value ? (
          <IconButton
            size="small"
            onClick={() => window.open(`/screenshots/${params.value}`, '_blank')}
            title="View Screenshot"
          >
            <ImageIcon />
          </IconButton>
        ) : null
      ),
    },
    {
      field: 'duration',
      headerName: 'Duration',
      width: 100,
      renderCell: (params) => formatDuration(params.row.started_at, params.row.completed_at),
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
      field: 'completed_at',
      headerName: 'Completed',
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
        Data Entry Logs
      </Typography>
      
      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={entryLogs || []}
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

export default DataEntryLogs; 