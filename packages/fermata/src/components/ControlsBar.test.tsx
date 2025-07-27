import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ControlsBar } from './ControlsBar';
import type { FilterConfig } from '../types';

describe('ControlsBar', () => {
  const mockFilterConfig: FilterConfig = {
    searchTerm: '',
    status: 'all',
    sortOption: 'date-desc'
  };

  const mockOnUpdateFilter = jest.fn();
  const mockOnClearFilters = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
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

  test('search input calls onUpdateFilter when typing', async () => {
    const user = userEvent.setup();
    render(<ControlsBar {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(/search recordings/i);
    await user.type(searchInput, 'test');

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('searchTerm', 'test');
  });

  test('sort dropdown calls onUpdateFilter when changed', async () => {
    const user = userEvent.setup();
    render(<ControlsBar {...defaultProps} />);

    const sortSelect = screen.getByLabelText(/sort by/i);
    await user.selectOptions(sortSelect, 'name-asc');

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('sortOption', 'name-asc');
  });

  test('status filter calls onUpdateFilter when changed', async () => {
    const user = userEvent.setup();
    render(<ControlsBar {...defaultProps} />);

    const statusSelect = screen.getByLabelText(/status/i);
    await user.selectOptions(statusSelect, 'analyzed');

    expect(mockOnUpdateFilter).toHaveBeenCalledWith('status', 'analyzed');
  });

  test('clear filters button appears when hasActiveFilters is true', () => {
    render(<ControlsBar {...defaultProps} hasActiveFilters={true} />);

    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });

  test('clear filters button not visible when no active filters', () => {
    render(<ControlsBar {...defaultProps} hasActiveFilters={false} />);

    expect(screen.queryByText(/clear filters/i)).not.toBeInTheDocument();
  });

  test('clear filters button calls onClearFilters when clicked', async () => {
    const user = userEvent.setup();
    render(<ControlsBar {...defaultProps} hasActiveFilters={true} />);

    const clearButton = screen.getByText(/clear filters/i);
    await user.click(clearButton);

    expect(mockOnClearFilters).toHaveBeenCalled();
  });
});
