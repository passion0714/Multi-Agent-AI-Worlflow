import React from 'react';
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
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Phone as PhoneIcon,
  Storage as StorageIcon,
  Cloud as CloudIcon,
  Security as SecurityIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';

function Settings() {
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
S3_BUCKET=leadhoop-recordings
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
    </Box>
  );
}

export default Settings; 