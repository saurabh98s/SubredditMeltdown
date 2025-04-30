import React, { useContext } from 'react';
import { AppContext } from '../context/AppContext';
import { 
  Box, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  TextField,
  Button,
  Grid, 
  Paper 
} from '@mui/material';

const FilterControls = () => {
  const { 
    subreddits, 
    selectedSubreddit, 
    setSelectedSubreddit,
    dateRange,
    setDateRange,
    timeframe,
    setTimeframe
  } = useContext(AppContext);

  const handleSubredditChange = (event) => {
    setSelectedSubreddit(event.target.value);
  };

  const handleStartDateChange = (event) => {
    setDateRange({
      ...dateRange,
      startDate: event.target.value
    });
  };

  const handleEndDateChange = (event) => {
    setDateRange({
      ...dateRange,
      endDate: event.target.value
    });
  };

  const handleTimeframeChange = (event) => {
    setTimeframe(event.target.value);
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} md={3}>
          <FormControl fullWidth>
            <InputLabel id="subreddit-select-label">Subreddit</InputLabel>
            <Select
              labelId="subreddit-select-label"
              id="subreddit-select"
              value={selectedSubreddit}
              label="Subreddit"
              onChange={handleSubredditChange}
            >
              {subreddits.map((subreddit) => (
                <MenuItem key={subreddit} value={subreddit}>
                  r/{subreddit}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <TextField
            id="start-date"
            label="Start Date"
            type="date"
            value={dateRange.startDate}
            onChange={handleStartDateChange}
            InputLabelProps={{
              shrink: true,
            }}
            fullWidth
          />
        </Grid>
        
        <Grid item xs={12} md={3}>
          <TextField
            id="end-date"
            label="End Date"
            type="date"
            value={dateRange.endDate}
            onChange={handleEndDateChange}
            InputLabelProps={{
              shrink: true,
            }}
            fullWidth
          />
        </Grid>
        
        <Grid item xs={12} md={3}>
          <FormControl fullWidth>
            <InputLabel id="timeframe-select-label">Timeframe</InputLabel>
            <Select
              labelId="timeframe-select-label"
              id="timeframe-select"
              value={timeframe}
              label="Timeframe"
              onChange={handleTimeframeChange}
            >
              <MenuItem value="daily">Daily</MenuItem>
              <MenuItem value="weekly">Weekly</MenuItem>
              <MenuItem value="monthly">Monthly</MenuItem>
            </Select>
          </FormControl>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default FilterControls;