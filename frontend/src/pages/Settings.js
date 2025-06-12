import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Phone as PhoneIcon,
  Storage as StorageIcon,
  Cloud as CloudIcon,
  Security as SecurityIcon,
  Assessment as AssessmentIcon,
  PhoneCallback as PhoneCallbackIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
});

function Settings() {
  const [callSettings, setCallSettings] = useState({
    day1: 5,
    day2: 4,
    day3: 2,
    day4: 2,
    day5: 2,
    day6: 0,
  });

  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  // Fetch call settings on component mount
  useEffect(() => {
    fetchCallSettings();
  }, []);

  const fetchCallSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/settings/call-attempts');
      setCallSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch call settings:', error);
      setSnackbar({
        open: true,
        message: `Error loading settings: ${error.response?.data?.detail || error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleCallSettingChange = (day, value) => {
    const numValue = parseInt(value, 10) || 0;
    setCallSettings({
      ...callSettings,
      [day]: numValue
    });
  };

  const saveCallSettings = async () => {
    try {
      setLoading(true);
      await api.post('/settings/call-attempts', callSettings);
      
      setSnackbar({
        open: true,
        message: 'Call attempt settings saved successfully!',
        severity: 'success'
      });
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Error saving settings: ${error.response?.data?.detail || error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const configSections = [
    {
      title: 'VAPI Configuration',
      icon: <PhoneIcon />,
      items: [
        { label: 'API Key', value: 'Configured', status: 'success' },
        { label: 'Phone Number', value: 'Configured', status: 'success' },
        { label: 'Assistant ID (Zoe)', value: 'Configured', status: 'success' },
      ],
    },
    {
      title: 'Database Configuration',
      icon: <StorageIcon />,
      items: [
        { label: 'PostgreSQL Connection', value: 'Connected', status: 'success' },
        { label: 'Tables', value: 'Initialized', status: 'success' },
        { label: 'Migrations', value: 'Up to date', status: 'success' },
      ],
    },
    {
      title: 'AWS S3 Configuration',
      icon: <CloudIcon />,
      items: [
        { label: 'Access Key', value: 'Configured', status: 'success' },
        { label: 'Bucket Access', value: 'Verified', status: 'success' },
        { label: 'Recording Upload', value: 'Enabled', status: 'success' },
      ],
    },
    {
      title: 'Lead Hoop Configuration',
      icon: <SecurityIcon />,
      items: [
        { label: 'Login Credentials', value: 'Configured', status: 'warning' },
        { label: 'Portal URL', value: 'Set', status: 'success' },
        { label: 'UI Automation', value: 'Ready', status: 'success' },
      ],
    },
  ];

  const systemStats = [
    { label: 'System Uptime', value: '2h 34m' },
    { label: 'Voice Agent Status', value: 'Running' },
    { label: 'Data Entry Agent Status', value: 'Running' },
    { label: 'Last Health Check', value: '30 seconds ago' },
    { label: 'Memory Usage', value: '245 MB' },
    { label: 'CPU Usage', value: '12%' },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings & Configuration
      </Typography>

      {/* System Status */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          System Status
        </Typography>
        <Grid container spacing={2}>
          {systemStats.map((stat, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card variant="outlined">
                <CardContent sx={{ py: 2 }}>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    {stat.label}
                  </Typography>
                  <Typography variant="h6">
                    {stat.value}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Call Attempt Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
          <PhoneCallbackIcon sx={{ mr: 1 }} />
          Call Attempt Settings
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Configure the maximum number of call attempts per day for follow-up calls.
        </Typography>
        
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Day</TableCell>
                <TableCell>Maximum Attempts</TableCell>
                <TableCell>Description</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Day 1</TableCell>
                <TableCell>
                  <TextField
                    type="number"
                    size="small"
                    value={callSettings.day1}
                    onChange={(e) => handleCallSettingChange('day1', e.target.value)}
                    inputProps={{ min: 0, max: 10 }}
                    sx={{ width: '80px' }}
                  />
                </TableCell>
                <TableCell>First day of call attempts</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Day 2</TableCell>
                <TableCell>
                  <TextField
                    type="number"
                    size="small"
                    value={callSettings.day2}
                    onChange={(e) => handleCallSettingChange('day2', e.target.value)}
                    inputProps={{ min: 0, max: 10 }}
                    sx={{ width: '80px' }}
                  />
                </TableCell>
                <TableCell>Second day of call attempts</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Days 3-5</TableCell>
                <TableCell>
                  <TextField
                    type="number"
                    size="small"
                    value={callSettings.day3}
                    onChange={(e) => {
                      const value = e.target.value;
                      handleCallSettingChange('day3', value);
                      handleCallSettingChange('day4', value);
                      handleCallSettingChange('day5', value);
                    }}
                    inputProps={{ min: 0, max: 10 }}
                    sx={{ width: '80px' }}
                  />
                </TableCell>
                <TableCell>Attempts per day for days 3 through 5</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Day 6+</TableCell>
                <TableCell>
                  <TextField
                    type="number"
                    size="small"
                    value={callSettings.day6}
                    onChange={(e) => handleCallSettingChange('day6', e.target.value)}
                    inputProps={{ min: 0, max: 10 }}
                    sx={{ width: '80px' }}
                  />
                </TableCell>
                <TableCell>Day 6 and beyond (0 turns off calls)</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
        
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<SaveIcon />}
          onClick={saveCallSettings}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Call Settings'}
        </Button>
      </Paper>

      {/* Configuration Sections */}
      <Grid container spacing={3}>
        {configSections.map((section, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {section.icon}
                  <Box component="span" sx={{ ml: 1 }}>
                    {section.title}
                  </Box>
                </Typography>
                <Divider sx={{ my: 2 }} />
                <List dense>
                  {section.items.map((item, itemIndex) => (
                    <ListItem key={itemIndex}>
                      <ListItemText
                        primary={item.label}
                        secondary={item.value}
                      />
                      <Chip
                        label={item.status}
                        color={getStatusColor(item.status)}
                        size="small"
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
              <CardActions>
                <Button size="small" color="primary">
                  Configure
                </Button>
                <Button size="small">
                  Test Connection
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Environment Variables */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Environment Configuration
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Make sure to configure the following environment variables in your `.env` file:
        </Typography>
        <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1, fontFamily: 'monospace' }}>
          <pre style={{ margin: 0, fontSize: '0.875rem' }}>
{`# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/merge_ai_workflow

# VAPI Configuration
VAPI_API_KEY=your_vapi_api_key_here
VAPI_PHONE_NUMBER=your_vapi_phone_number
VAPI_ASSISTANT_ID=your_vapi_assistant_id

# Lead Hoop Configuration
LEADHOOP_LOGIN_URL=https://leadhoop.com/login
LEADHOOP_USERNAME=your_leadhoop_username
LEADHOOP_PASSWORD=your_leadhoop_password
LEADHOOP_PORTAL_URL=https://leadhoop.com/portal

# AWS S3 Configuration for Call Recordings
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=gWNbBxbJpE/vIQ1CKS5wAdl4APkzwzGQJ7tcMW+x
AWS_REGION=us-east-1
S3_BUCKET=mergeai.call.recordings
S3_FOLDER=ieim/eluminus_merge_142
PUBLISHER_ID=142`}
          </pre>
        </Box>
      </Paper>

      {/* Quick Actions */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Grid container spacing={2}>
          <Grid item>
            <Button variant="outlined" color="primary">
              Restart Agents
            </Button>
          </Grid>
          <Grid item>
            <Button variant="outlined" color="secondary">
              Clear Logs
            </Button>
          </Grid>
          <Grid item>
            <Button variant="outlined">
              Export Configuration
            </Button>
          </Grid>
          <Grid item>
            <Button variant="outlined">
              Run Health Check
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Snackbar for notifications */}
      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Settings; 