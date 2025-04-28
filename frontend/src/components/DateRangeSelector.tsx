import React, { useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { format, parseISO } from 'date-fns';

interface DateRangeSelectorProps {
  startDate: string; // ISO format
  endDate: string; // ISO format
  onDateChange: (startDate: string, endDate: string) => void;
}

const DateRangeSelector: React.FC<DateRangeSelectorProps> = ({
  startDate,
  endDate,
  onDateChange,
}) => {
  const [startDateObj, setStartDateObj] = useState<Date>(() => {
    try {
      return parseISO(startDate);
    } catch (e) {
      return new Date('2020-01-01');
    }
  });
  
  const [endDateObj, setEndDateObj] = useState<Date>(() => {
    try {
      return parseISO(endDate);
    } catch (e) {
      return new Date('2022-12-31');
    }
  });

  const handleStartDateChange = (date: Date | null) => {
    if (date) {
      setStartDateObj(date);
      onDateChange(format(date, 'yyyy-MM-dd'), format(endDateObj, 'yyyy-MM-dd'));
    }
  };

  const handleEndDateChange = (date: Date | null) => {
    if (date) {
      setEndDateObj(date);
      onDateChange(format(startDateObj, 'yyyy-MM-dd'), format(date, 'yyyy-MM-dd'));
    }
  };

  return (
    <div className="bg-white p-4 shadow rounded-lg">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 mb-2">
            Start Date
          </label>
          <DatePicker
            id="start-date"
            selected={startDateObj}
            onChange={handleStartDateChange}
            selectsStart
            startDate={startDateObj}
            endDate={endDateObj}
            maxDate={endDateObj}
            className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          />
        </div>
        <div>
          <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 mb-2">
            End Date
          </label>
          <DatePicker
            id="end-date"
            selected={endDateObj}
            onChange={handleEndDateChange}
            selectsEnd
            startDate={startDateObj}
            endDate={endDateObj}
            minDate={startDateObj}
            className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          />
        </div>
      </div>
    </div>
  );
};

export default DateRangeSelector; 