import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ControlsBar } from './ControlsBar';
import type { FilterConfig } from '../types';

describe('ControlsBar', () => {
  const mockFilterConfig: FilterConfig = {
    searchTerm: '',
    status: 'all',
    sortOption: 'date-desc'
  };

  const mockOnUpdateFilter = vi.fn();
  const mockOnClearFilters = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps = {
    filterConfig: mockFilterConfig,
    onUpdateFilter: mockOnUpdateFilter,
    onClearFilters: mockOnClearFilters,
    hasActiveFilters: false
  };

  test('renders all controls correctly', () => {
    render(<ControlsBar {...defaultProps} />);

    // Should have sort dropdown
    expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();

    // Should have search input
    expect(screen.getByPlaceholderText(/search recordings/i)).toBeInTheDocument();

    // Should have status filter
    expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
  });

  test('sort dropdown has all expected options', () => {
    render(<ControlsBar {...defaultProps} />);

    const sortSelect = screen.getByLabelText(/sort by/i);
    const options = Array.from(sortSelect.children).map(option => (option as HTMLOptionElement).textContent);

    expect(options).toEqual([
      'Newest First',
      'Oldest First',
      'By Status',
      'Name A→Z',
      'Name Z→A',
      'Largest First',
      'Smallest First'
    ]);
  });

  test('search input calls onUpdateFilter when typing', () => {
    render(<ControlsBar {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(/search recordings/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('searchTerm', 'test');
  });

  test('sort dropdown calls onUpdateFilter when changed', () => {
    render(<ControlsBar {...defaultProps} />);

    const sortSelect = screen.getByLabelText(/sort by/i);
    fireEvent.change(sortSelect, { target: { value: 'name-asc' } });

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('sortOption', 'name-asc');
  });

  test('status filter calls onUpdateFilter when changed', () => {
    render(<ControlsBar {...defaultProps} />);

    const statusSelect = screen.getByLabelText(/status/i);
    fireEvent.change(statusSelect, { target: { value: 'Analyzed' } });

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('status', 'Analyzed');
  });

  test('clear filters button appears when hasActiveFilters is true', () => {
    render(<ControlsBar {...defaultProps} hasActiveFilters={true} />);

    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });

  test('clear filters button not visible when no active filters', () => {
    render(<ControlsBar {...defaultProps} hasActiveFilters={false} />);

    expect(screen.queryByText(/clear filters/i)).not.toBeInTheDocument();
  });

  test('clear filters button calls onClearFilters when clicked', () => {
    render(<ControlsBar {...defaultProps} hasActiveFilters={true} />);

    const clearButton = screen.getByText(/clear filters/i);
    fireEvent.click(clearButton);

    expect(mockOnClearFilters).toHaveBeenCalled();
  });

  test('status filter calls onUpdateFilter with object shape when failed is selected', () => {
    const failedFilterConfig: FilterConfig = {
      ...mockFilterConfig,
      status: { Failed: '' }
    };
    render(<ControlsBar {...defaultProps} filterConfig={failedFilterConfig} />);

    const statusSelect = screen.getByLabelText(/status/i);
    fireEvent.change(statusSelect, { target: { value: 'failed' } });

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('status', { Failed: '' });
  });
});
