import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../context/AppContext';
import api from '../services/api';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  CircularProgress, 
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import FilterControls from '../components/FilterControls';
import SentimentEventChart from '../components/SentimentEventChart';

const categoryColors = {
  economic: '#f44336',
  weather: '#2196f3',
  health: '#4caf50',
  education: '#ff9800',
  politics: '#9c27b0'
};

const EventsCorrelation = () => {
  const { 
    selectedSubreddit, 
    dateRange, 
    loading: contextLoading,
    error: contextError
  } = useContext(AppContext);

  const [sentimentData, setSentimentData] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    const fetchCorrelationData = async () => {
      if (!selectedSubreddit) return;

      setLoading(true);
      setError(null);

      try {
        const [sentimentResponse, eventsResponse] = await Promise.all([
          api.getSentiment(selectedSubreddit, dateRange.startDate, dateRange.endDate),
          api.getEvents(dateRange.startDate, dateRange.endDate, selectedCategory || null)
        ]);

        setSentimentData(sentimentResponse);
        setEvents(eventsResponse);

        // Extract unique categories from events
        const uniqueCategories = [...new Set(eventsResponse.map(event => event.category))];
        setCategories(uniqueCategories);
      } catch (err) {
        setError('Failed to fetch correlation data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCorrelationData();
  }, [selectedSubreddit, dateRange, selectedCategory]);

  const handleCategoryChange = (event) => {
    setSelectedCategory(event.target.value);
  };

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
        Events Correlation Analysis
      </Typography>
      
      <FilterControls />
      
      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Category Filter */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ mr: 2 }}>
                Event Category:
              </Typography>
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel id="category-select-label">Category</InputLabel>
                <Select
                  labelId="category-select-label"
                  id="category-select"
                  value={selectedCategory}
                  label="Category"
                  onChange={handleCategoryChange}
                >
                  <MenuItem value="">
                    <em>All Categories</em>
                  </MenuItem>
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Paper>
        </Grid>
        
        {/* Combined Chart */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Sentiment and Events Correlation
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Visualizing how external events correlate with sentiment shifts in r/{selectedSubreddit}
            </Typography>
            <SentimentEventChart data={sentimentData} events={events} />
          </Paper>
        </Grid>
        
        {/* Events Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Events Timeline
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Event</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Sentiment Change</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {events.map((event, index) => {
                    // Calculate sentiment change (mock data for demo)
                    const sentimentChange = (Math.random() * 0.4 - 0.2).toFixed(2);
                    const isPositive = parseFloat(sentimentChange) > 0;
                    
                    return (
                      <TableRow key={index}>
                        <TableCell>{event.date}</TableCell>
                        <TableCell>{event.event}</TableCell>
                        <TableCell>
                          <Chip 
                            label={event.category} 
                            sx={{ 
                              backgroundColor: categoryColors[event.category] || '#9e9e9e',
                              color: 'white'
                            }} 
                          />
                        </TableCell>
                        <TableCell>
                          <Typography
                            sx={{ 
                              color: isPositive ? 'green' : 'red',
                              fontWeight: 'bold'
                            }}
                          >
                            {isPositive ? '+' : ''}{sentimentChange}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default EventsCorrelation;