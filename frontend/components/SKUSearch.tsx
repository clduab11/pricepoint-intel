'use client';

import React, { useState, useCallback, useMemo } from 'react';
import debounce from 'lodash.debounce';
import type {
  SKUSearchProps,
  SKUSearchFilters,
  SKUWithPricing,
  ProductCategory,
} from '../types';

const CATEGORY_LABELS: Record<ProductCategory, string> = {
  flooring: 'Flooring',
  building_materials: 'Building Materials',
  electrical: 'Electrical',
  plumbing: 'Plumbing',
  hvac: 'HVAC',
  hardware: 'Hardware',
  lumber: 'Lumber',
  paint: 'Paint',
  tools: 'Tools',
  other: 'Other',
};

const ALL_CATEGORIES: ProductCategory[] = [
  'flooring',
  'building_materials',
  'electrical',
  'plumbing',
  'hvac',
  'hardware',
  'lumber',
  'paint',
  'tools',
  'other',
];

interface SKUCardProps {
  sku: SKUWithPricing;
  onSelect?: (sku: SKUWithPricing) => void;
}

const SKUCard: React.FC<SKUCardProps> = ({ sku, onSelect }) => {
  return (
    <div
      className="sku-card"
      onClick={() => onSelect?.(sku)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(sku)}
    >
      <div className="sku-card-header">
        <span className="sku-id">{sku.sku_id}</span>
        <span className={`category-badge ${sku.category}`}>
          {CATEGORY_LABELS[sku.category]}
        </span>
      </div>
      <h3 className="sku-name">{sku.product_name}</h3>
      {sku.description && (
        <p className="sku-description">{sku.description}</p>
      )}
      <div className="sku-pricing">
        {sku.price_range ? (
          <span className="price-range">
            ${sku.price_range[0].toFixed(2)} - ${sku.price_range[1].toFixed(2)}
          </span>
        ) : sku.avg_price ? (
          <span className="avg-price">${sku.avg_price.toFixed(2)}</span>
        ) : (
          <span className="no-price">No pricing data</span>
        )}
        {sku.vendor_count !== undefined && (
          <span className="vendor-count">
            {sku.vendor_count} vendor{sku.vendor_count !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      {sku.supplier_info?.manufacturer && (
        <div className="sku-manufacturer">
          <span className="label">Manufacturer:</span>
          <span className="value">{sku.supplier_info.manufacturer}</span>
        </div>
      )}

      <style jsx>{`
        .sku-card {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 16px;
          cursor: pointer;
          transition: box-shadow 0.2s, transform 0.2s;
        }
        .sku-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
        }
        .sku-card:focus {
          outline: 2px solid #0066cc;
          outline-offset: 2px;
        }
        .sku-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .sku-id {
          font-family: monospace;
          font-size: 12px;
          color: #666;
        }
        .category-badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }
        .category-badge.flooring { background: #e3f2fd; color: #1565c0; }
        .category-badge.building_materials { background: #fff3e0; color: #e65100; }
        .category-badge.electrical { background: #fff8e1; color: #f57f17; }
        .category-badge.plumbing { background: #e8f5e9; color: #2e7d32; }
        .category-badge.hvac { background: #f3e5f5; color: #7b1fa2; }
        .category-badge.hardware { background: #eceff1; color: #455a64; }
        .category-badge.lumber { background: #efebe9; color: #5d4037; }
        .category-badge.paint { background: #fce4ec; color: #c2185b; }
        .category-badge.tools { background: #e0f2f1; color: #00695c; }
        .category-badge.other { background: #f5f5f5; color: #616161; }
        .sku-name {
          margin: 0 0 8px;
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        .sku-description {
          margin: 0 0 12px;
          font-size: 14px;
          color: #666;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .sku-pricing {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
        }
        .price-range, .avg-price {
          font-size: 18px;
          font-weight: 700;
          color: #0066cc;
        }
        .no-price {
          font-size: 14px;
          color: #999;
          font-style: italic;
        }
        .vendor-count {
          font-size: 12px;
          color: #666;
          background: #f5f5f5;
          padding: 4px 8px;
          border-radius: 4px;
        }
        .sku-manufacturer {
          margin-top: 12px;
          font-size: 13px;
        }
        .sku-manufacturer .label {
          color: #999;
        }
        .sku-manufacturer .value {
          color: #333;
          margin-left: 4px;
        }
      `}</style>
    </div>
  );
};

export const SKUSearch: React.FC<SKUSearchProps> = ({
  onSearch,
  onSKUSelect,
  initialFilters = {},
  categories = ALL_CATEGORIES,
  regions = [],
  suppliers = [],
  isLoading = false,
}) => {
  const [filters, setFilters] = useState<SKUSearchFilters>(initialFilters);
  const [searchResults, setSearchResults] = useState<SKUWithPricing[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Debounced search for text input
  const debouncedSearch = useMemo(
    () =>
      debounce((newFilters: SKUSearchFilters) => {
        onSearch(newFilters);
      }, 300),
    [onSearch]
  );

  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newFilters = { ...filters, query: e.target.value };
      setFilters(newFilters);
      debouncedSearch(newFilters);
    },
    [filters, debouncedSearch]
  );

  const handleFilterChange = useCallback(
    (key: keyof SKUSearchFilters, value: unknown) => {
      const newFilters = { ...filters, [key]: value || undefined };
      setFilters(newFilters);
      onSearch(newFilters);
    },
    [filters, onSearch]
  );

  const handleClearFilters = useCallback(() => {
    setFilters({});
    onSearch({});
  }, [onSearch]);

  const activeFilterCount = useMemo(() => {
    return Object.values(filters).filter(
      (v) => v !== undefined && v !== ''
    ).length;
  }, [filters]);

  return (
    <div className="sku-search">
      {/* Search Header */}
      <div className="search-header">
        <div className="search-input-wrapper">
          <svg
            className="search-icon"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Search SKUs by name, ID, or description..."
            value={filters.query || ''}
            onChange={handleQueryChange}
            aria-label="Search SKUs"
          />
          {filters.query && (
            <button
              className="clear-input"
              onClick={() => handleFilterChange('query', '')}
              aria-label="Clear search"
            >
              &times;
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="filter-group">
          <label htmlFor="category-filter">Category</label>
          <select
            id="category-filter"
            value={filters.category || ''}
            onChange={(e) =>
              handleFilterChange('category', e.target.value as ProductCategory)
            }
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {CATEGORY_LABELS[cat]}
              </option>
            ))}
          </select>
        </div>

        {regions.length > 0 && (
          <div className="filter-group">
            <label htmlFor="region-filter">Region</label>
            <select
              id="region-filter"
              value={filters.region || ''}
              onChange={(e) => handleFilterChange('region', e.target.value)}
            >
              <option value="">All Regions</option>
              {regions.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </div>
        )}

        {suppliers.length > 0 && (
          <div className="filter-group">
            <label htmlFor="supplier-filter">Supplier</label>
            <select
              id="supplier-filter"
              value={filters.supplier_id || ''}
              onChange={(e) => handleFilterChange('supplier_id', e.target.value)}
            >
              <option value="">All Suppliers</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          className="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
          aria-expanded={showAdvanced}
        >
          Advanced {showAdvanced ? '−' : '+'}
        </button>

        {activeFilterCount > 0 && (
          <button className="clear-filters" onClick={handleClearFilters}>
            Clear ({activeFilterCount})
          </button>
        )}
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="advanced-filters">
          <div className="filter-row">
            <div className="filter-group">
              <label htmlFor="min-price">Min Price</label>
              <input
                id="min-price"
                type="number"
                min="0"
                step="0.01"
                placeholder="$0.00"
                value={filters.min_price || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'min_price',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>
            <div className="filter-group">
              <label htmlFor="max-price">Max Price</label>
              <input
                id="max-price"
                type="number"
                min="0"
                step="0.01"
                placeholder="$999.99"
                value={filters.max_price || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'max_price',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>
            <div className="filter-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={filters.is_active !== false}
                  onChange={(e) =>
                    handleFilterChange(
                      'is_active',
                      e.target.checked ? undefined : false
                    )
                  }
                />
                Active SKUs only
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <div className="loading-indicator">
          <div className="spinner" />
          <span>Searching...</span>
        </div>
      )}

      <style jsx>{`
        .sku-search {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .search-header {
          margin-bottom: 16px;
        }
        .search-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }
        .search-icon {
          position: absolute;
          left: 12px;
          color: #999;
          pointer-events: none;
        }
        .search-input {
          width: 100%;
          padding: 12px 40px;
          font-size: 16px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          outline: none;
          transition: border-color 0.2s;
        }
        .search-input:focus {
          border-color: #0066cc;
        }
        .clear-input {
          position: absolute;
          right: 12px;
          background: none;
          border: none;
          font-size: 20px;
          color: #999;
          cursor: pointer;
          padding: 4px 8px;
        }
        .clear-input:hover {
          color: #333;
        }
        .filter-bar {
          display: flex;
          gap: 16px;
          align-items: flex-end;
          flex-wrap: wrap;
          margin-bottom: 16px;
          padding: 16px;
          background: #f8f9fa;
          border-radius: 8px;
        }
        .filter-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .filter-group label {
          font-size: 12px;
          font-weight: 600;
          color: #666;
          text-transform: uppercase;
        }
        .filter-group select,
        .filter-group input[type="number"] {
          padding: 8px 12px;
          font-size: 14px;
          border: 1px solid #ddd;
          border-radius: 6px;
          background: white;
          min-width: 150px;
        }
        .filter-group select:focus,
        .filter-group input:focus {
          outline: none;
          border-color: #0066cc;
        }
        .checkbox-group {
          flex-direction: row;
          align-items: center;
        }
        .checkbox-group label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          text-transform: none;
          font-weight: normal;
          cursor: pointer;
        }
        .advanced-toggle,
        .clear-filters {
          padding: 8px 16px;
          font-size: 14px;
          border: 1px solid #ddd;
          border-radius: 6px;
          background: white;
          cursor: pointer;
          transition: background 0.2s;
        }
        .advanced-toggle:hover {
          background: #f0f0f0;
        }
        .clear-filters {
          color: #dc3545;
          border-color: #dc3545;
        }
        .clear-filters:hover {
          background: #dc3545;
          color: white;
        }
        .advanced-filters {
          padding: 16px;
          background: #f8f9fa;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .filter-row {
          display: flex;
          gap: 16px;
          align-items: flex-end;
          flex-wrap: wrap;
        }
        .loading-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          padding: 24px;
          color: #666;
        }
        .spinner {
          width: 24px;
          height: 24px;
          border: 3px solid #f0f0f0;
          border-top-color: #0066cc;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default SKUSearch;
