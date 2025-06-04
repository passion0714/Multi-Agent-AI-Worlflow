import React from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useQuery } from 'react-query';
import api from '../services/api';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C'];

const statusLabels = {
  pending: 'Pending',
  calling: 'Calling',
  confirmed: 'Confirmed',
  call_failed: 'Call Failed',
  not_interested: 'Not Interested',
  entry_in_progress: 'Entry in Progress',
  entered: 'Entered',
  entry_failed: 'Entry Failed',
};

function Dashboard() {
  const { data: dashboardStats, isLoading: statsLoading } = useQuery(
    'dashboardStats',
    () => api.get('/stats/dashboard').then(res => res.data),
    { refetchInterval: 10000 }
  );

  const { data: statusBreakdown, isLoading: breakdownLoading } = useQuery(
    'statusBreakdown',
    () => api.get('/stats/status-breakdown').then(res => res.data),
    { refetchInterval: 10000 }
  );

  const pieData = statusBreakdown ? Object.entries(statusBreakdown).map(([key, value]) => ({
    name: statusLabels[key] || key,
    value,
    key,
  })).filter(item => item.value > 0) : [];

  const barData = statusBreakdown ? Object.entries(statusBreakdown).map(([key, value]) => ({
    status: statusLabels[key] || key,
    count: value,
  })) : [];

  if (statsLoading || breakdownLoading) {
    return (
      <Box sx={{ width: '100%' }}>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Leads
              </Typography>
              <Typography variant="h4">
                {dashboardStats?.total_leads || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Pending Calls
              </Typography>
              <Typography variant="h4" color="warning.main">
                {dashboardStats?.pending_leads || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Confirmed Leads
              </Typography>
              <Typography variant="h4" color="success.main">
                {dashboardStats?.confirmed_leads || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h4" color="primary.main">
                {dashboardStats?.success_rate?.toFixed(1) || 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Lead Status Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Lead Status Counts
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="status" 
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Workflow Progress */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Workflow Progress
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Pending → Calling
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={dashboardStats?.total_leads > 0 ? 
                      ((dashboardStats.total_leads - dashboardStats.pending_leads) / dashboardStats.total_leads) * 100 : 0
                    }
                    sx={{ mt: 1 }}
                  />
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Confirmed → Entry
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={dashboardStats?.confirmed_leads > 0 ? 
                      (dashboardStats.entered_leads / dashboardStats.confirmed_leads) * 100 : 0
                    }
                    color="success"
                    sx={{ mt: 1 }}
                  />
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Overall Success
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={dashboardStats?.success_rate || 0}
                    color="primary"
                    sx={{ mt: 1 }}
                  />
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    Active Processing
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={dashboardStats?.total_leads > 0 ? 
                      ((dashboardStats.calling_leads + dashboardStats.confirmed_leads) / dashboardStats.total_leads) * 100 : 0
                    }
                    color="warning"
                    sx={{ mt: 1 }}
                  />
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard; 