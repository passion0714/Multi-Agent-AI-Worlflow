import React, { useState } from 'react';
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Badge,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Phone as PhoneIcon,
  Assignment as AssignmentIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';
import api from '../services/api';

const drawerWidth = 240;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { text: 'Leads', icon: <PeopleIcon />, path: '/leads' },
  { text: 'Call Logs', icon: <PhoneIcon />, path: '/call-logs' },
  { text: 'Data Entry Logs', icon: <AssignmentIcon />, path: '/data-entry-logs' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
];

function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  // Get agent status
  const { data: agentStatus } = useQuery(
    'agentStatus',
    () => api.get('/agents/status').then(res => res.data),
    { refetchInterval: 5000 }
  );

  // Start agents mutation
  const startAgentsMutation = useMutation(
    () => api.post('/agents/start'),
    {
      onSuccess: () => {
        toast.success('Agents started successfully');
        queryClient.invalidateQueries('agentStatus');
      },
      onError: (error) => {
        toast.error(`Failed to start agents: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  // Stop agents mutation
  const stopAgentsMutation = useMutation(
    () => api.post('/agents/stop'),
    {
      onSuccess: () => {
        toast.success('Agents stopped successfully');
        queryClient.invalidateQueries('agentStatus');
      },
      onError: (error) => {
        toast.error(`Failed to stop agents: ${error.response?.data?.detail || error.message}`);
      },
    }
  );

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleAgentToggle = () => {
    if (agentStatus?.agents_running) {
      stopAgentsMutation.mutate();
    } else {
      startAgentsMutation.mutate();
    }
  };

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          MERGE AI
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Multi-Agent AI Workflow
          </Typography>
          
          {/* Agent Status */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip
              label={`Voice Agent: ${agentStatus?.voice_agent_running ? 'Running' : 'Stopped'}`}
              color={agentStatus?.voice_agent_running ? 'success' : 'default'}
              size="small"
            />
            <Chip
              label={`Data Entry: ${agentStatus?.data_entry_agent_running ? 'Running' : 'Stopped'}`}
              color={agentStatus?.data_entry_agent_running ? 'success' : 'default'}
              size="small"
            />
            <IconButton
              color="inherit"
              onClick={handleAgentToggle}
              disabled={startAgentsMutation.isLoading || stopAgentsMutation.isLoading}
            >
              {agentStatus?.agents_running ? <StopIcon /> : <PlayIcon />}
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>
      
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="mailbox folders"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}

export default Layout; 