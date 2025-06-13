import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Input,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarExport,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
} from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Upload as UploadIcon,
  MoreVert as MoreVertIcon,
  Phone as PhoneIcon,
  Assignment as AssignmentIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import api from '../services/api';

const statusColors = {
  pending: 'default',
  calling: 'info',
  confirmed: 'success',
  call_failed: 'error',
  not_interested: 'warning',
  entry_in_progress: 'info',
  entered: 'success',
  entry_failed: 'error',
  no_answer: 'warning',
  callback_requested: 'info',
};

const statusLabels = {
  pending: 'Pending',
  calling: 'Calling',
  confirmed: 'Confirmed',
  call_failed: 'Call Failed',
  not_interested: 'Not Interested',
  entry_in_progress: 'Entry in Progress',
  entered: 'Entered',
  entry_failed: 'Entry Failed',
  no_answer: 'No Answer',
  callback_requested: 'Callback Requested',
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

function Leads() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [statusUpdateDialogOpen, setStatusUpdateDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [newLead, setNewLead] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
  });
  const [actionMenuAnchor, setActionMenuAnchor] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);

  const queryClient = useQueryClient();

  // Fetch leads with real-time updates
  const { data: leads, isLoading } = useQuery(
    'leads',
    () => api.get('/leads/').then(res => res.data),
    { 
      refetchInterval: 3000, // Reduced interval for more frequent updates
      refetchIntervalInBackground: true,
    }
  );

  // Auto-update status based on call completion
  useEffect(() => {
    if (leads) {
      // Check for leads that have completed calls and need status update
      const leadsNeedingUpdate = leads.filter(lead => 
        lead.status === 'calling' && 
        lead.call_completed_at && 
        !lead.status_updated_after_call
      );

      if (leadsNeedingUpdate.length > 0) {
        // Auto-confirm leads after successful calls
        leadsNeedingUpdate.forEach(lead => {
          if (lead.call_successful) {
            markConfirmedMutation.mutate(lead.id);
          }
        });
      }
    }
  }, [leads]);

  // Upload CSV mutation
  const uploadMutation = useMutation(
    (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/leads/import-csv/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    {
      onSuccess: (response) => {
        toast.success(response.data.message);
        setUploadDialogOpen(false);
        setSelectedFile(null);
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Upload failed: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Add lead mutation
  const addLeadMutation = useMutation(
    (leadData) => api.post('/leads/', leadData),
    {
      onSuccess: () => {
        toast.success('Lead added successfully');
        setAddDialogOpen(false);
        setNewLead({
          first_name: '',
          last_name: '',
          email: '',
          phone: '',
          address: '',
          city: '',
          state: '',
          zip_code: '',
        });
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Failed to add lead: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Make call mutation - with automatic status progression
  const makeCallMutation = useMutation(
    (leadId) => api.post(`/leads/${leadId}/make-call`),
    {
      onSuccess: (response, leadId) => {
        toast.success('Call initiated successfully');
        queryClient.invalidateQueries('leads');
        
        // If call was successful, automatically mark as confirmed
        if (response.data.call_successful) {
          setTimeout(() => {
            markConfirmedMutation.mutate(leadId);
          }, 2000); // Small delay to show calling status first
        }
      },
      onError: (error) => {
        toast.error(`Failed to make call: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Update status mutation
  const updateStatusMutation = useMutation(
    ({ leadId, status }) => {
      return api.post(`/leads/${leadId}/status`, { status });
    },
    {
      onSuccess: (response) => {
        toast.success('Status updated successfully');
        setStatusUpdateDialogOpen(false);
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Failed to update status: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Mark confirmed mutation
  const markConfirmedMutation = useMutation(
    (leadId) => api.post(`/leads/${leadId}/mark-confirmed`),
    {
      onSuccess: () => {
        toast.success('Lead confirmed successfully');
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Failed to mark confirmed: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Retry call mutation
  const retryCallMutation = useMutation(
    (leadId) => api.post(`/leads/${leadId}/retry-call`),
    {
      onSuccess: () => {
        toast.success('Call retry initiated');
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Failed to retry call: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Retry entry mutation
  const retryEntryMutation = useMutation(
    (leadId) => api.post(`/leads/${leadId}/retry-entry`),
    {
      onSuccess: () => {
        toast.success('Data entry retry initiated');
        queryClient.invalidateQueries('leads');
      },
      onError: (error) => {
        toast.error(`Failed to retry entry: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  const handleFileUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  const handleAddLead = () => {
    addLeadMutation.mutate(newLead);
  };

  const handleActionClick = (event, lead) => {
    setActionMenuAnchor(event.currentTarget);
    setSelectedLead(lead);
  };

  const handleActionClose = () => {
    setActionMenuAnchor(null);
    setSelectedLead(null);
  };

  const handleStatusUpdate = () => {
    console.log('Updating status...');
    console.log('Selected lead:', selectedLead);
    console.log('Selected status:', selectedStatus);
    
    if (selectedLead && selectedStatus) {
      const updateData = {
        leadId: selectedLead.id,
        status: selectedStatus
      };
      console.log('Sending update data:', updateData);
      
      updateStatusMutation.mutate(updateData);
    } else {
      console.error('Missing required data for status update');
    }
  };

  const openStatusUpdateDialog = () => {
    setSelectedStatus(selectedLead?.status || '');
    setStatusUpdateDialogOpen(true);
    setActionMenuAnchor(null);
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'first_name', headerName: 'First Name', width: 120 },
    { field: 'last_name', headerName: 'Last Name', width: 120 },
    { field: 'email', headerName: 'Email', width: 200 },
    { field: 'phone1', headerName: 'Phone', width: 130 },
    { field: 'address', headerName: 'Address', width: 200 },
    { field: 'city', headerName: 'City', width: 100 },
    { field: 'state', headerName: 'State', width: 80 },
    {
      field: 'status',
      headerName: 'Status',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={statusLabels[params.value] || params.value.replace('_', ' ').toUpperCase()}
          color={statusColors[params.value] || 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'tcpa_opt_in',
      headerName: 'TCPA',
      width: 80,
      renderCell: (params) => (
        params.value ? <CheckCircleIcon color="success" /> : null
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
    {
      field: 'last_called_at',
      headerName: 'Last Called',
      width: 150,
      renderCell: (params) => (
        params.value ? format(new Date(params.value), 'MMM dd, yyyy HH:mm') : 'Never'
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      renderCell: (params) => (
        <IconButton
          size="small"
          onClick={(event) => handleActionClick(event, params.row)}
        >
          <MoreVertIcon />
        </IconButton>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Leads Management
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Import CSV
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setAddDialogOpen(true)}
          >
            Add Lead
          </Button>
        </Box>
      </Box>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={leads || []}
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

      {/* CSV Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)}>
        <DialogTitle>Import Leads from CSV</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Upload a CSV file with lead data. Expected columns: First Name, Last Name, Email, Phone, Address, City, State, Zip
          </Typography>
          <Input
            type="file"
            accept=".csv"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleFileUpload}
            disabled={!selectedFile || uploadMutation.isLoading}
            variant="contained"
          >
            {uploadMutation.isLoading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Lead Dialog */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Lead</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="First Name"
              value={newLead.first_name}
              onChange={(e) => setNewLead({ ...newLead, first_name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Last Name"
              value={newLead.last_name}
              onChange={(e) => setNewLead({ ...newLead, last_name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Email"
              type="email"
              value={newLead.email}
              onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Phone"
              value={newLead.phone}
              onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Address"
              value={newLead.address}
              onChange={(e) => setNewLead({ ...newLead, address: e.target.value })}
              fullWidth
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="City"
                value={newLead.city}
                onChange={(e) => setNewLead({ ...newLead, city: e.target.value })}
                fullWidth
              />
              <TextField
                label="State"
                value={newLead.state}
                onChange={(e) => setNewLead({ ...newLead, state: e.target.value })}
                fullWidth
              />
              <TextField
                label="Zip Code"
                value={newLead.zip_code}
                onChange={(e) => setNewLead({ ...newLead, zip_code: e.target.value })}
                fullWidth
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddLead}
            disabled={addLeadMutation.isLoading}
            variant="contained"
          >
            {addLeadMutation.isLoading ? 'Adding...' : 'Add Lead'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Status Update Dialog */}
      <Dialog 
        open={statusUpdateDialogOpen} 
        onClose={() => {
          setStatusUpdateDialogOpen(false);
          // Don't reset selectedLead when just closing the dialog
        }}
      >
        <DialogTitle>Update Lead Status</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              label="Status"
            >
              {Object.entries(statusLabels).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStatusUpdateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleStatusUpdate}
            disabled={updateStatusMutation.isLoading || !selectedStatus}
            variant="contained"
          >
            {updateStatusMutation.isLoading ? 'Updating...' : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Action Menu */}
      <Menu
        anchorEl={actionMenuAnchor}
        open={Boolean(actionMenuAnchor)}
        onClose={handleActionClose}
      >
        <MenuItem
          onClick={() => {
            makeCallMutation.mutate(selectedLead.id);
            handleActionClose();
          }}
          disabled={makeCallMutation.isLoading || selectedLead?.status === 'calling'}
        >
          <PhoneIcon sx={{ mr: 1 }} />
          {selectedLead?.status === 'calling' ? 'Calling...' : 'Make Call'}
        </MenuItem>
        <MenuItem
          onClick={() => {
            retryCallMutation.mutate(selectedLead.id);
            handleActionClose();
          }}
          disabled={retryCallMutation.isLoading}
        >
          <ScheduleIcon sx={{ mr: 1 }} />
          Retry Call
        </MenuItem>
        <MenuItem
          onClick={() => {
            retryEntryMutation.mutate(selectedLead.id);
            handleActionClose();
          }}
          disabled={retryEntryMutation.isLoading}
        >
          <AssignmentIcon sx={{ mr: 1 }} />
          Retry Data Entry
        </MenuItem>
        <MenuItem
          onClick={() => {
            markConfirmedMutation.mutate(selectedLead.id);
            handleActionClose();
          }}
          disabled={markConfirmedMutation.isLoading}
        >
          <CheckCircleIcon sx={{ mr: 1 }} />
          Mark Confirmed
        </MenuItem>
        <MenuItem onClick={openStatusUpdateDialog}>
          <CancelIcon sx={{ mr: 1 }} />
          Update Status
        </MenuItem>
      </Menu>
    </Box>
  );
}

export default Leads;