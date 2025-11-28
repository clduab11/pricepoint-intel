'use client';

import React, { useMemo, useState, useCallback } from 'react';
import type {
  VendorMatrixProps,
  VendorMatrixCell,
  Vendor,
  SKU,
} from '../types';

interface CellTooltip {
  cell: VendorMatrixCell;
  vendor: Vendor;
  sku: SKU;
  x: number;
  y: number;
}

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
};

const CATEGORY_COLORS: Record<string, string> = {
  flooring: '#3b82f6',
  building_materials: '#f97316',
  electrical: '#eab308',
  plumbing: '#22c55e',
  hvac: '#a855f7',
  hardware: '#64748b',
  lumber: '#92400e',
  paint: '#ec4899',
  tools: '#14b8a6',
  other: '#6b7280',
};

export const VendorMatrix: React.FC<VendorMatrixProps> = ({
  data,
  onCellClick,
  onVendorClick,
  onSKUClick,
  showPriceRanking = true,
  highlightSingleSource = true,
}) => {
  const [tooltip, setTooltip] = useState<CellTooltip | null>(null);
  const [sortBy, setSortBy] = useState<'name' | 'coverage' | 'price'>('coverage');
  const [filterCategory, setFilterCategory] = useState<string>('');

  // Sort vendors by selected criteria
  const sortedVendors = useMemo(() => {
    const vendors = [...data.vendors];
    switch (sortBy) {
      case 'name':
        return vendors.sort((a, b) => a.vendor_name.localeCompare(b.vendor_name));
      case 'coverage':
        return vendors.sort((a, b) => {
          const aCount = data.matrix
            .flat()
            .filter((c) => c.vendor_id === a.vendor_id && c.has_pricing).length;
          const bCount = data.matrix
            .flat()
            .filter((c) => c.vendor_id === b.vendor_id && c.has_pricing).length;
          return bCount - aCount;
        });
      case 'price':
        return vendors.sort((a, b) => {
          const aRank = data.matrix
            .flat()
            .filter((c) => c.vendor_id === a.vendor_id && c.price_rank === 1).length;
          const bRank = data.matrix
            .flat()
            .filter((c) => c.vendor_id === b.vendor_id && c.price_rank === 1).length;
          return bRank - aRank;
        });
      default:
        return vendors;
    }
  }, [data.vendors, data.matrix, sortBy]);

  // Filter SKUs by category
  const filteredSKUs = useMemo(() => {
    if (!filterCategory) return data.skus;
    return data.skus.filter((sku) => sku.category === filterCategory);
  }, [data.skus, filterCategory]);

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(data.skus.map((sku) => sku.category));
    return Array.from(cats).sort();
  }, [data.skus]);

  // Calculate vendor coverage stats
  const vendorStats = useMemo(() => {
    const stats = new Map<string, { coverage: number; bestPrice: number }>();
    sortedVendors.forEach((vendor) => {
      const vendorCells = data.matrix
        .flat()
        .filter((c) => c.vendor_id === vendor.vendor_id);
      const withPricing = vendorCells.filter((c) => c.has_pricing);
      const bestPriceCount = vendorCells.filter((c) => c.price_rank === 1).length;
      stats.set(vendor.vendor_id, {
        coverage: (withPricing.length / data.skus.length) * 100,
        bestPrice: bestPriceCount,
      });
    });
    return stats;
  }, [sortedVendors, data.matrix, data.skus]);

  // Check if SKU has single source
  const isSingleSource = useCallback(
    (skuId: string): boolean => {
      const skuCells = data.matrix
        .flat()
        .filter((c) => c.sku_id === skuId && c.has_pricing);
      return skuCells.length === 1;
    },
    [data.matrix]
  );

  // Get cell for vendor/SKU combination
  const getCell = useCallback(
    (vendorId: string, skuId: string): VendorMatrixCell | undefined => {
      return data.matrix
        .flat()
        .find((c) => c.vendor_id === vendorId && c.sku_id === skuId);
    },
    [data.matrix]
  );

  const handleCellHover = useCallback(
    (
      cell: VendorMatrixCell,
      vendor: Vendor,
      sku: SKU,
      event: React.MouseEvent
    ) => {
      if (cell.has_pricing) {
        setTooltip({
          cell,
          vendor,
          sku,
          x: event.clientX,
          y: event.clientY,
        });
      }
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const getCellColor = (cell: VendorMatrixCell | undefined, skuId: string): string => {
    if (!cell || !cell.has_pricing) return 'transparent';

    const singleSource = highlightSingleSource && isSingleSource(skuId);

    if (showPriceRanking && cell.price_rank) {
      if (cell.price_rank === 1) return singleSource ? '#fde68a' : '#bbf7d0'; // Gold for single-source best, Green for best
      if (cell.price_rank === 2) return '#bfdbfe'; // Blue for second
      if (cell.price_rank === 3) return '#e5e7eb'; // Gray for third
      return '#f3f4f6'; // Light gray for rest
    }

    return singleSource ? '#fde68a' : '#dbeafe';
  };

  return (
    <div className="vendor-matrix">
      {/* Header */}
      <div className="matrix-header">
        <h2 className="matrix-title">Vendor-SKU Relationship Matrix</h2>
        <div className="matrix-controls">
          <div className="control-group">
            <label htmlFor="sort-select">Sort vendors:</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            >
              <option value="coverage">By Coverage</option>
              <option value="name">By Name</option>
              <option value="price">By Best Price Count</option>
            </select>
          </div>
          <div className="control-group">
            <label htmlFor="category-filter">Filter category:</label>
            <select
              id="category-filter"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="matrix-summary">
        <div className="summary-item">
          <span className="summary-value">{data.summary.total_vendors}</span>
          <span className="summary-label">Vendors</span>
        </div>
        <div className="summary-item">
          <span className="summary-value">{data.summary.total_skus}</span>
          <span className="summary-label">SKUs</span>
        </div>
        <div className="summary-item">
          <span className="summary-value">
            {data.summary.coverage_pct.toFixed(1)}%
          </span>
          <span className="summary-label">Coverage</span>
        </div>
        <div className="summary-item">
          <span className="summary-value">{data.summary.multi_source_skus}</span>
          <span className="summary-label">Multi-Source</span>
        </div>
        <div className="summary-item warning">
          <span className="summary-value">{data.summary.single_source_skus}</span>
          <span className="summary-label">Single-Source Risk</span>
        </div>
      </div>

      {/* Legend */}
      <div className="matrix-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#bbf7d0' }} />
          <span>Best Price</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#bfdbfe' }} />
          <span>2nd Best</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#e5e7eb' }} />
          <span>3rd Best</span>
        </div>
        {highlightSingleSource && (
          <div className="legend-item">
            <span className="legend-color" style={{ background: '#fde68a' }} />
            <span>Single Source</span>
          </div>
        )}
        <div className="legend-item">
          <span className="legend-color empty" />
          <span>No Pricing</span>
        </div>
      </div>

      {/* Matrix Grid */}
      <div className="matrix-container">
        <table className="matrix-table">
          <thead>
            <tr>
              <th className="vendor-header">Vendor</th>
              <th className="vendor-stats">Coverage</th>
              <th className="vendor-stats">Best Price</th>
              {filteredSKUs.map((sku) => (
                <th
                  key={sku.sku_id}
                  className="sku-header"
                  onClick={() => onSKUClick?.(sku)}
                  title={sku.product_name}
                >
                  <div className="sku-header-content">
                    <span
                      className="category-dot"
                      style={{ background: CATEGORY_COLORS[sku.category] }}
                    />
                    <span className="sku-id">{sku.sku_id}</span>
                    {highlightSingleSource && isSingleSource(sku.sku_id) && (
                      <span className="single-source-badge" title="Single source">
                        !
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedVendors.map((vendor) => {
              const stats = vendorStats.get(vendor.vendor_id);
              return (
                <tr key={vendor.vendor_id}>
                  <td
                    className="vendor-name"
                    onClick={() => onVendorClick?.(vendor)}
                  >
                    {vendor.vendor_name}
                    {vendor.metrics?.reliability_score && (
                      <span className="reliability-score">
                        {(vendor.metrics.reliability_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </td>
                  <td className="vendor-stats-cell">
                    <div className="coverage-bar">
                      <div
                        className="coverage-fill"
                        style={{ width: `${stats?.coverage || 0}%` }}
                      />
                    </div>
                    <span>{stats?.coverage.toFixed(0)}%</span>
                  </td>
                  <td className="vendor-stats-cell best-price-count">
                    {stats?.bestPrice || 0}
                  </td>
                  {filteredSKUs.map((sku) => {
                    const cell = getCell(vendor.vendor_id, sku.sku_id);
                    return (
                      <td
                        key={`${vendor.vendor_id}-${sku.sku_id}`}
                        className={`matrix-cell ${
                          cell?.has_pricing ? 'has-pricing' : 'no-pricing'
                        }`}
                        style={{ background: getCellColor(cell, sku.sku_id) }}
                        onClick={() => cell && onCellClick?.(cell)}
                        onMouseEnter={(e) =>
                          cell && handleCellHover(cell, vendor, sku, e)
                        }
                        onMouseLeave={handleMouseLeave}
                      >
                        {cell?.has_pricing && cell.price && (
                          <span className="cell-price">
                            {showPriceRanking && cell.price_rank
                              ? `#${cell.price_rank}`
                              : formatCurrency(cell.price)}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="cell-tooltip"
          style={{
            left: tooltip.x + 10,
            top: tooltip.y + 10,
          }}
        >
          <div className="tooltip-header">
            <strong>{tooltip.sku.product_name}</strong>
          </div>
          <div className="tooltip-subheader">{tooltip.vendor.vendor_name}</div>
          <div className="tooltip-body">
            <div className="tooltip-row">
              <span>Price:</span>
              <strong>
                {tooltip.cell.price ? formatCurrency(tooltip.cell.price) : 'N/A'}
              </strong>
            </div>
            {showPriceRanking && tooltip.cell.price_rank && (
              <div className="tooltip-row">
                <span>Rank:</span>
                <strong>#{tooltip.cell.price_rank}</strong>
              </div>
            )}
            <div className="tooltip-row">
              <span>Primary:</span>
              <strong>{tooltip.cell.is_primary_supplier ? 'Yes' : 'No'}</strong>
            </div>
            {isSingleSource(tooltip.sku.sku_id) && (
              <div className="tooltip-warning">
                Single source - supply risk
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .vendor-matrix {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        .matrix-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          flex-wrap: wrap;
          gap: 16px;
        }
        .matrix-title {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: #1f2937;
        }
        .matrix-controls {
          display: flex;
          gap: 16px;
        }
        .control-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .control-group label {
          font-size: 14px;
          color: #6b7280;
        }
        .control-group select {
          padding: 6px 12px;
          font-size: 14px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: white;
        }
        .matrix-summary {
          display: flex;
          gap: 24px;
          margin-bottom: 16px;
          padding: 16px;
          background: #f8fafc;
          border-radius: 8px;
        }
        .summary-item {
          text-align: center;
        }
        .summary-item.warning .summary-value {
          color: #dc2626;
        }
        .summary-value {
          display: block;
          font-size: 24px;
          font-weight: 700;
          color: #1f2937;
        }
        .summary-label {
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
        }
        .matrix-legend {
          display: flex;
          gap: 16px;
          margin-bottom: 16px;
          padding: 8px 16px;
          background: #f8fafc;
          border-radius: 6px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          color: #6b7280;
        }
        .legend-color {
          width: 16px;
          height: 16px;
          border-radius: 3px;
          border: 1px solid #e5e7eb;
        }
        .legend-color.empty {
          background: repeating-linear-gradient(
            45deg,
            #f3f4f6,
            #f3f4f6 2px,
            white 2px,
            white 4px
          );
        }
        .matrix-container {
          overflow-x: auto;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
        }
        .matrix-table {
          border-collapse: collapse;
          min-width: 100%;
        }
        .matrix-table th,
        .matrix-table td {
          padding: 8px;
          border: 1px solid #e5e7eb;
          text-align: center;
          font-size: 12px;
        }
        .matrix-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #374151;
          position: sticky;
          top: 0;
          z-index: 1;
        }
        .vendor-header {
          text-align: left !important;
          min-width: 150px;
        }
        .vendor-stats {
          min-width: 80px;
          font-size: 11px !important;
        }
        .sku-header {
          min-width: 60px;
          cursor: pointer;
          transition: background 0.2s;
        }
        .sku-header:hover {
          background: #e5e7eb;
        }
        .sku-header-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        .category-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .sku-id {
          font-family: monospace;
          font-size: 10px;
        }
        .single-source-badge {
          background: #fde68a;
          color: #92400e;
          font-size: 10px;
          font-weight: 700;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .vendor-name {
          text-align: left !important;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s;
        }
        .vendor-name:hover {
          background: #f3f4f6;
        }
        .reliability-score {
          font-size: 10px;
          color: #22c55e;
          margin-left: 8px;
        }
        .vendor-stats-cell {
          font-size: 11px;
          color: #6b7280;
        }
        .coverage-bar {
          width: 50px;
          height: 6px;
          background: #e5e7eb;
          border-radius: 3px;
          overflow: hidden;
          margin: 0 auto 4px;
        }
        .coverage-fill {
          height: 100%;
          background: #22c55e;
          border-radius: 3px;
        }
        .best-price-count {
          font-weight: 600;
          color: #16a34a;
        }
        .matrix-cell {
          min-width: 50px;
          height: 32px;
          cursor: pointer;
          transition: transform 0.1s, box-shadow 0.1s;
        }
        .matrix-cell.has-pricing:hover {
          transform: scale(1.1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          z-index: 1;
        }
        .matrix-cell.no-pricing {
          background: repeating-linear-gradient(
            45deg,
            #f9fafb,
            #f9fafb 2px,
            white 2px,
            white 4px
          );
        }
        .cell-price {
          font-weight: 500;
          font-size: 10px;
        }
        .cell-tooltip {
          position: fixed;
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 12px 16px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 1000;
          pointer-events: none;
          min-width: 180px;
        }
        .tooltip-header {
          font-size: 13px;
          color: #1f2937;
          margin-bottom: 4px;
        }
        .tooltip-subheader {
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 8px;
          padding-bottom: 8px;
          border-bottom: 1px solid #e5e7eb;
        }
        .tooltip-row {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          margin-bottom: 4px;
        }
        .tooltip-row span {
          color: #6b7280;
        }
        .tooltip-warning {
          margin-top: 8px;
          padding: 6px 8px;
          background: #fef2f2;
          color: #dc2626;
          font-size: 11px;
          border-radius: 4px;
          text-align: center;
        }
      `}</style>
    </div>
  );
};

export default VendorMatrix;
