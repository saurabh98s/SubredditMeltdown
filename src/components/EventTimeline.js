import React from 'react';
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  Chip, 
  Divider,
  Paper
} from '@mui/material';
import { format, parseISO } from 'date-fns';

const categoryColors = {
  economic: '#f44336',
  weather: '#2196f3',
  health: '#4caf50',
  education: '#ff9800',
  politics: '#9c27b0'
};

const EventTimeline = ({ events = [] }) => {
  if (!events.length) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body1">No events found in the selected time period.</Typography>
      </Box>
    );
  }

  // Sort events by date
  const sortedEvents = [...events].sort((a, b) => {
    return new Date(a.date) - new Date(b.date);
  });

  return (
    <Box>
      <List sx={{ width: '100%' }}>
        {sortedEvents.map((event, index) => (
          <React.Fragment key={index}>
            <ListItem 
              alignItems="flex-start"
              sx={{ 
                py: 2,
                borderLeft: `4px solid ${categoryColors[event.category] || '#9e9e9e'}`,
                pl: 2
              }}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Typography variant="h6" component="span">
                      {event.event}
                    </Typography>
                    <Chip 
                      label={event.category} 
                      size="small"
                      sx={{ 
                        ml: 2,
                        backgroundColor: categoryColors[event.category] || '#9e9e9e',
                        color: 'white'
                      }} 
                    />
                  </Box>
                }
                secondary={
                  <Typography
                    component="span"
                    variant="body2"
                    color="text.primary"
                  >
                    {format(parseISO(event.date), 'MMMM d, yyyy')}
                  </Typography>
                }
              />
            </ListItem>
            {index < sortedEvents.length - 1 && <Divider component="li" />}
          </React.Fragment>
        ))}
      </List>
    </Box>
  );
};

export default EventTimeline;