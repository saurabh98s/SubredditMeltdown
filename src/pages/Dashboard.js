import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../context/AppContext';
import api from '../services/api';
import { Box, Grid, Paper, Typography, Card, CardContent, CircularProgress } from '@mui/material';
import SentimentChart from '../components/SentimentChart';
import EventTimeline from '../components/EventTimeline';
import FilterControls from '../components/FilterControls';

const Dashboard = () => {
  const { 
    selectedSubreddit, 
    dateRange, 
    timeframe,
    loading: contextLoading,
    error: contextError
  } = useContext(AppContext);

  const [sentimentData, setSentimentData] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    avgSentiment: 0,
    minSentiment: 0,
    maxSentiment: 0,
    totalPosts: 0
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!selectedSubreddit) return;

      setLoading(true);
      setError(null);

      try {
        const [sentimentResponse, eventsResponse] = await Promise.all([
          api.getSentiment(selectedSubreddit, dateRange.startDate, dateRange.endDate),
          api.getEvents(dateRange.startDate, dateRange.endDate)
        ]);

        setSentimentData(sentimentResponse);
        setEvents(eventsResponse);

        // Calculate stats
        if (sentimentResponse.length > 0) {
          const scores = sentimentResponse.map(item => item.sentiment_score);
          setStats({
            avgSentiment: scores.reduce((sum, score) => sum + score, 0) / scores.length,
            minSentiment: Math.min(...scores),
            maxSentiment: Math.max(...scores),
            totalPosts: Math.floor(Math.random() * 10000) // Mock data, replace with actual count
          });
        }
      } catch (err) {
        setError('Failed to fetch dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [selectedSubreddit, dateRange, timeframe]);

  if (contextLoading || loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (contextError || error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{contextError || error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Mental Health Trends Dashboard
      </Typography>
      
      <FilterControls />
      
      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Stats cards */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Average Sentiment
              </Typography>
              <Typography variant="h4" component="div">
                {stats.avgSentiment.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Min Sentiment
              </Typography>
              <Typography variant="h4" component="div">
                {stats.minSentiment.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Max Sentiment
              </Typography>
              <Typography variant="h4" component="div">
                {stats.maxSentiment.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Posts Analyzed
              </Typography>
              <Typography variant="h4" component="div">
                {stats.totalPosts.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Sentiment chart */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Sentiment Trends
            </Typography>
            <SentimentChart data={sentimentData} events={events} />
          </Paper>
        </Grid>

        {/* Event timeline */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Events Timeline
            </Typography>
            <EventTimeline events={events} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;