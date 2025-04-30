import React from 'react';
import { Box, Typography, useTheme } from '@mui/material';

const KeywordCloud = ({ keywords = [] }) => {
  const theme = useTheme();
  
  if (!keywords.length) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body1">No keywords found for the selected parameters.</Typography>
      </Box>
    );
  }

  // Sort keywords by weight (descending)
  const sortedKeywords = [...keywords].sort((a, b) => b.weight - a.weight);
  
  // Calculate font sizes (min: 14px, max: 40px)
  const minWeight = Math.min(...sortedKeywords.map(k => k.weight));
  const maxWeight = Math.max(...sortedKeywords.map(k => k.weight));
  const weightRange = maxWeight - minWeight;

  const calculateFontSize = (weight) => {
    if (weightRange === 0) return 24; // If all weights are the same
    
    // Scale between 14px and 40px based on weight
    return 14 + ((weight - minWeight) / weightRange) * 26;
  };

  // Calculate color intensity (from lighter to darker primary color)
  const calculateColor = (weight) => {
    if (weightRange === 0) return theme.palette.primary.main;
    
    // Get RGB components of primary color
    const primaryColor = theme.palette.primary.main;
    const r = parseInt(primaryColor.substr(1, 2), 16);
    const g = parseInt(primaryColor.substr(3, 2), 16);
    const b = parseInt(primaryColor.substr(5, 2), 16);
    
    // Calculate lighter shade based on weight
    const intensity = 0.4 + ((weight - minWeight) / weightRange) * 0.6;
    
    const newR = Math.round(r * intensity);
    const newG = Math.round(g * intensity);
    const newB = Math.round(b * intensity);
    
    return `rgb(${newR}, ${newG}, ${newB})`;
  };

  // Generate a simple tag cloud layout
  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 2,
        height: '100%',
        p: 2
      }}
    >
      {sortedKeywords.map((keyword, index) => (
        <Typography
          key={index}
          component="span"
          sx={{
            fontSize: `${calculateFontSize(keyword.weight)}px`,
            fontWeight: keyword.weight > (minWeight + maxWeight) / 2 ? 'bold' : 'normal',
            color: calculateColor(keyword.weight),
            transition: 'all 0.2s ease',
            '&:hover': {
              transform: 'scale(1.1)',
            },
            cursor: 'default',
            lineHeight: 1.5
          }}
        >
          {keyword.keyword}
        </Typography>
      ))}
    </Box>
  );
};

export default KeywordCloud;