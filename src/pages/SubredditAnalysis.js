import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../context/AppContext';
import api from '../services/api';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  CircularProgress, 
  Divider 
} from '@mui/material';
import FilterControls from '../components/FilterControls';
import KeywordCloud from '../components/KeywordCloud';
import SentimentChart from '../components/SentimentChart';

const SubredditAnalysis = () => {
  const { 
    selectedSubreddit, 
    dateRange, 
    timeframe,
    loading: contextLoading,
    error: contextError
  } = useContext(AppContext);

  const [sentimentData, setSentimentData] = useState([]);
  const [keywordData, setKeywordData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalysisData = async () => {
      if (!selectedSubreddit) return;

      setLoading(true);
      setError(null);

      try {
        const [sentimentResponse, keywordResponse] = await Promise.all([
          api.getSentiment(selectedSubreddit, dateRange.startDate, dateRange.endDate),
          api.getKeywords(selectedSubreddit, timeframe)
        ]);

        setSentimentData(sentimentResponse);
        setKeywordData(keywordResponse);
      } catch (err) {
        setError('Failed to fetch subreddit analysis data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysisData();
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
        Subreddit Analysis
      </Typography>
      
      <FilterControls />
      
      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Sentiment over time */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Sentiment Trends for r/{selectedSubreddit}
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Tracking sentiment changes over time for the selected subreddit
            </Typography>
            <SentimentChart data={sentimentData} />
          </Paper>
        </Grid>
        
        {/* Keyword Analysis */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Top Keywords
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Most frequent terms used in r/{selectedSubreddit} during selected period
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ height: 300 }}>
              <KeywordCloud keywords={keywordData} />
            </Box>
          </Paper>
        </Grid>
        
        {/* Sentiment Distribution */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Sentiment Analysis
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Distribution of sentiment scores in r/{selectedSubreddit}
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ p: 2 }}>
              {sentimentData.length > 0 ? (
                <Box>
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="body1">
                      <strong>Average Sentiment Score:</strong> {
                        (sentimentData.reduce((acc, item) => acc + item.sentiment_score, 0) / sentimentData.length).toFixed(2)
                      }
                    </Typography>
                  </Box>
                  
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body1">
                      <strong>Sentiment Range:</strong> {
                        Math.min(...sentimentData.map(item => item.sentiment_score)).toFixed(2)
                      } to {
                        Math.max(...sentimentData.map(item => item.sentiment_score)).toFixed(2)
                      }
                    </Typography>
                  </Box>
                  
                  <Box>
                    <Typography variant="body1">
                      <strong>Period:</strong> {dateRange.startDate} to {dateRange.endDate}
                    </Typography>
                  </Box>
                </Box>
              ) : (
                <Typography>No sentiment data available</Typography>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SubredditAnalysis;