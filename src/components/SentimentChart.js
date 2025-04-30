import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine 
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { Box, useTheme } from '@mui/material';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          backgroundColor: 'white',
          border: '1px solid #ccc',
          p: 1,
          borderRadius: 1,
        }}
      >
        <p>{`Date: ${format(parseISO(label), 'MMM d, yyyy')}`}</p>
        <p style={{ color: payload[0].color }}>
          {`Sentiment: ${payload[0].value.toFixed(2)}`}
        </p>
      </Box>
    );
  }

  return null;
};

const SentimentChart = ({ data, events = [] }) => {
  const theme = useTheme();

  // Format data for chart
  const chartData = data.map(item => ({
    ...item,
    date: item.date,
    sentimentScore: item.sentiment_score
  }));

  // Find min and max sentiment values for Y axis domain
  const sentimentValues = chartData.map(item => item.sentimentScore);
  const minSentiment = Math.min(...sentimentValues);
  const maxSentiment = Math.max(...sentimentValues);
  
  // Add some padding to Y axis domain
  const yDomainMin = Math.floor(minSentiment * 10) / 10 - 0.1;
  const yDomainMax = Math.ceil(maxSentiment * 10) / 10 + 0.1;

  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <ResponsiveContainer>
        <LineChart
          data={chartData}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 50,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tickFormatter={(date) => format(parseISO(date), 'MMM d')}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis 
            domain={[yDomainMin, yDomainMax]}
            tickFormatter={(value) => value.toFixed(1)}
            label={{ value: 'Sentiment Score', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <ReferenceLine y={0} stroke="#000" strokeDasharray="3 3" />
          
          {/* Add reference lines for events if provided */}
          {events && events.map((event, index) => (
            <ReferenceLine 
              key={index}
              x={event.date}
              stroke={theme.palette.secondary.main}
              strokeDasharray="3 3"
              label={{ 
                value: event.event.substring(0, 12) + (event.event.length > 12 ? '...' : ''),
                position: 'top',
                fill: theme.palette.secondary.main,
                fontSize: 10
              }}
            />
          ))}
          
          <Line
            type="monotone"
            dataKey="sentimentScore"
            name="Sentiment"
            stroke={theme.palette.primary.main}
            activeDot={{ r: 8 }}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default SentimentChart;