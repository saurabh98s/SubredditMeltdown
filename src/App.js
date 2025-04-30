import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AppContextProvider } from './context/AppContext';

// Import pages
import Dashboard from './pages/Dashboard';
import SubredditAnalysis from './pages/SubredditAnalysis';
import EventsCorrelation from './pages/EventsCorrelation';
import Layout from './components/Layout';

// Create a theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3F51B5',
    },
    secondary: {
      main: '#F50057',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppContextProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/subreddit-analysis" element={<SubredditAnalysis />} />
              <Route path="/events-correlation" element={<EventsCorrelation />} />
            </Routes>
          </Layout>
        </Router>
      </AppContextProvider>
    </ThemeProvider>
  );
}

export default App;