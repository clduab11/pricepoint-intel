'use client';

import React, { useMemo, useState, useCallback } from 'react';
import type { PricingHeatmapProps, RegionPricingData, HeatmapConfig } from '../types';

// Default color scale (green to yellow to red)
const DEFAULT_COLOR_SCALE = [
  '#22c55e', // green (low)
  '#84cc16', // lime
  '#eab308', // yellow
  '#f97316', // orange
  '#ef4444', // red (high)
];

// US state coordinates (approximate centroids)
const US_STATE_COORDS: Record<string, { x: number; y: number }> = {
  AL: { x: 730, y: 400 },
  AK: { x: 150, y: 500 },
  AZ: { x: 250, y: 380 },
  AR: { x: 620, y: 370 },
  CA: { x: 120, y: 300 },
  CO: { x: 350, y: 300 },
  CT: { x: 870, y: 200 },
  DE: { x: 850, y: 250 },
  FL: { x: 800, y: 480 },
  GA: { x: 770, y: 400 },
  HI: { x: 300, y: 520 },
  ID: { x: 220, y: 180 },
  IL: { x: 650, y: 280 },
  IN: { x: 700, y: 280 },
  IA: { x: 580, y: 240 },
  KS: { x: 480, y: 310 },
  KY: { x: 730, y: 320 },
  LA: { x: 620, y: 440 },
  ME: { x: 910, y: 120 },
  MD: { x: 830, y: 260 },
  MA: { x: 890, y: 180 },
  MI: { x: 700, y: 200 },
  MN: { x: 560, y: 160 },
  MS: { x: 670, y: 410 },
  MO: { x: 590, y: 320 },
  MT: { x: 280, y: 130 },
  NE: { x: 460, y: 250 },
  NV: { x: 180, y: 270 },
  NH: { x: 890, y: 150 },
  NJ: { x: 860, y: 230 },
  NM: { x: 320, y: 380 },
  NY: { x: 830, y: 180 },
  NC: { x: 800, y: 340 },
  ND: { x: 460, y: 130 },
  OH: { x: 750, y: 270 },
  OK: { x: 500, y: 370 },
  OR: { x: 140, y: 160 },
  PA: { x: 810, y: 230 },
  RI: { x: 890, y: 190 },
  SC: { x: 790, y: 370 },
  SD: { x: 460, y: 180 },
  TN: { x: 720, y: 350 },
  TX: { x: 470, y: 440 },
  UT: { x: 260, y: 280 },
  VT: { x: 875, y: 140 },
  VA: { x: 810, y: 300 },
  WA: { x: 160, y: 100 },
  WV: { x: 780, y: 290 },
  WI: { x: 620, y: 190 },
  WY: { x: 320, y: 210 },
};

// Region groupings for broader analysis
const REGION_GROUPS: Record<string, string[]> = {
  Northeast: ['CT', 'DE', 'MA', 'MD', 'ME', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT'],
  Southeast: ['AL', 'AR', 'FL', 'GA', 'KY', 'LA', 'MS', 'NC', 'SC', 'TN', 'VA', 'WV'],
  Midwest: ['IA', 'IL', 'IN', 'KS', 'MI', 'MN', 'MO', 'ND', 'NE', 'OH', 'SD', 'WI'],
  Southwest: ['AZ', 'NM', 'OK', 'TX'],
  West: ['AK', 'CA', 'CO', 'HI', 'ID', 'MT', 'NV', 'OR', 'UT', 'WA', 'WY'],
};

interface TooltipData {
  region: RegionPricingData;
  x: number;
  y: number;
}

const getColorFromScale = (
  value: number,
  min: number,
  max: number,
  colorScale: string[]
): string => {
  if (max === min) return colorScale[Math.floor(colorScale.length / 2)];
  const normalized = (value - min) / (max - min);
  const index = Math.min(
    Math.floor(normalized * colorScale.length),
    colorScale.length - 1
  );
  return colorScale[index];
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
};

export const PricingHeatmap: React.FC<PricingHeatmapProps> = ({
  data,
  config = {},
  onRegionClick,
  onRegionHover,
  width = 960,
  height = 600,
  title = 'Regional Pricing Heatmap',
}) => {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<HeatmapConfig['metric']>(
    config.metric || 'avg_price'
  );

  const mergedConfig: HeatmapConfig = {
    colorScale: config.colorScale || DEFAULT_COLOR_SCALE,
    showLabels: config.showLabels ?? true,
    metric: selectedMetric,
    ...config,
  };

  // Create a map of region code to data
  const regionDataMap = useMemo(() => {
    const map = new Map<string, RegionPricingData>();
    data.forEach((d) => {
      map.set(d.region_code, d);
    });
    return map;
  }, [data]);

  // Calculate min/max for color scale
  const { minValue, maxValue } = useMemo(() => {
    if (data.length === 0) return { minValue: 0, maxValue: 100 };

    const values = data.map((d) => {
      switch (selectedMetric) {
        case 'avg_price':
          return d.avg_price;
        case 'vendor_count':
          return d.vendor_count;
        case 'price_index':
          return d.price_index;
        default:
          return d.avg_price;
      }
    });

    return {
      minValue: config.minValue ?? Math.min(...values),
      maxValue: config.maxValue ?? Math.max(...values),
    };
  }, [data, selectedMetric, config.minValue, config.maxValue]);

  const handleRegionHover = useCallback(
    (regionCode: string, event: React.MouseEvent) => {
      const regionData = regionDataMap.get(regionCode);
      if (regionData) {
        setTooltip({
          region: regionData,
          x: event.clientX,
          y: event.clientY,
        });
        onRegionHover?.(regionData);
      }
    },
    [regionDataMap, onRegionHover]
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
    onRegionHover?.(null);
  }, [onRegionHover]);

  const handleRegionClick = useCallback(
    (regionCode: string) => {
      const regionData = regionDataMap.get(regionCode);
      if (regionData) {
        onRegionClick?.(regionData);
      }
    },
    [regionDataMap, onRegionClick]
  );

  const getRegionColor = useCallback(
    (regionCode: string): string => {
      const regionData = regionDataMap.get(regionCode);
      if (!regionData) return '#e5e7eb'; // Gray for no data

      const value =
        selectedMetric === 'avg_price'
          ? regionData.avg_price
          : selectedMetric === 'vendor_count'
          ? regionData.vendor_count
          : regionData.price_index;

      return getColorFromScale(
        value,
        minValue,
        maxValue,
        mergedConfig.colorScale
      );
    },
    [regionDataMap, selectedMetric, minValue, maxValue, mergedConfig.colorScale]
  );

  const getValue = (regionData: RegionPricingData): number | string => {
    switch (selectedMetric) {
      case 'avg_price':
        return formatCurrency(regionData.avg_price);
      case 'vendor_count':
        return regionData.vendor_count;
      case 'price_index':
        return regionData.price_index.toFixed(2);
      default:
        return regionData.avg_price;
    }
  };

  return (
    <div className="heatmap-container">
      <div className="heatmap-header">
        <h2 className="heatmap-title">{title}</h2>
        <div className="metric-selector">
          <label htmlFor="metric-select">View by:</label>
          <select
            id="metric-select"
            value={selectedMetric}
            onChange={(e) =>
              setSelectedMetric(e.target.value as HeatmapConfig['metric'])
            }
          >
            <option value="avg_price">Average Price</option>
            <option value="vendor_count">Vendor Count</option>
            <option value="price_index">Price Index</option>
          </select>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="heatmap-svg"
        aria-label="Regional pricing heatmap"
      >
        {/* Background */}
        <rect width={width} height={height} fill="#f8fafc" />

        {/* Region circles */}
        {Object.entries(US_STATE_COORDS).map(([code, coords]) => {
          const hasData = regionDataMap.has(code);
          const regionData = regionDataMap.get(code);

          return (
            <g key={code}>
              <circle
                cx={coords.x}
                cy={coords.y}
                r={hasData ? 28 : 20}
                fill={getRegionColor(code)}
                stroke={hasData ? '#374151' : '#9ca3af'}
                strokeWidth={hasData ? 2 : 1}
                opacity={hasData ? 0.9 : 0.4}
                className={hasData ? 'region-circle clickable' : 'region-circle'}
                onMouseEnter={(e) => hasData && handleRegionHover(code, e)}
                onMouseLeave={handleMouseLeave}
                onClick={() => hasData && handleRegionClick(code)}
                role={hasData ? 'button' : undefined}
                tabIndex={hasData ? 0 : undefined}
                aria-label={
                  hasData && regionData
                    ? `${regionData.region}: ${getValue(regionData)}`
                    : `${code}: No data`
                }
              />
              {mergedConfig.showLabels && (
                <text
                  x={coords.x}
                  y={coords.y + 4}
                  textAnchor="middle"
                  fontSize="12"
                  fontWeight="600"
                  fill={hasData ? '#1f2937' : '#6b7280'}
                  pointerEvents="none"
                >
                  {code}
                </text>
              )}
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(${width - 180}, ${height - 100})`}>
          <text x="0" y="0" fontSize="12" fontWeight="600" fill="#374151">
            {selectedMetric === 'avg_price'
              ? 'Price Level'
              : selectedMetric === 'vendor_count'
              ? 'Vendors'
              : 'Index'}
          </text>
          <defs>
            <linearGradient id="legendGradient">
              {mergedConfig.colorScale.map((color, i) => (
                <stop
                  key={i}
                  offset={`${(i / (mergedConfig.colorScale.length - 1)) * 100}%`}
                  stopColor={color}
                />
              ))}
            </linearGradient>
          </defs>
          <rect
            x="0"
            y="10"
            width="150"
            height="16"
            fill="url(#legendGradient)"
            rx="2"
          />
          <text x="0" y="40" fontSize="10" fill="#6b7280">
            {selectedMetric === 'avg_price'
              ? formatCurrency(minValue)
              : minValue.toFixed(0)}
          </text>
          <text x="150" y="40" fontSize="10" fill="#6b7280" textAnchor="end">
            {selectedMetric === 'avg_price'
              ? formatCurrency(maxValue)
              : maxValue.toFixed(0)}
          </text>
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="tooltip"
          style={{
            left: tooltip.x + 10,
            top: tooltip.y + 10,
          }}
        >
          <div className="tooltip-header">{tooltip.region.region}</div>
          <div className="tooltip-row">
            <span className="tooltip-label">Avg Price:</span>
            <span className="tooltip-value">
              {formatCurrency(tooltip.region.avg_price)}
            </span>
          </div>
          <div className="tooltip-row">
            <span className="tooltip-label">Price Range:</span>
            <span className="tooltip-value">
              {formatCurrency(tooltip.region.min_price)} -{' '}
              {formatCurrency(tooltip.region.max_price)}
            </span>
          </div>
          <div className="tooltip-row">
            <span className="tooltip-label">Vendors:</span>
            <span className="tooltip-value">{tooltip.region.vendor_count}</span>
          </div>
          <div className="tooltip-row">
            <span className="tooltip-label">SKUs:</span>
            <span className="tooltip-value">{tooltip.region.sku_count}</span>
          </div>
          <div className="tooltip-row">
            <span className="tooltip-label">Price Index:</span>
            <span className="tooltip-value">
              {tooltip.region.price_index.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="heatmap-summary">
        <div className="summary-stat">
          <span className="stat-value">{data.length}</span>
          <span className="stat-label">Regions</span>
        </div>
        <div className="summary-stat">
          <span className="stat-value">
            {data.reduce((sum, d) => sum + d.vendor_count, 0)}
          </span>
          <span className="stat-label">Total Vendors</span>
        </div>
        <div className="summary-stat">
          <span className="stat-value">
            {data.reduce((sum, d) => sum + d.sku_count, 0)}
          </span>
          <span className="stat-label">Total SKUs</span>
        </div>
        <div className="summary-stat">
          <span className="stat-value">
            {data.length > 0
              ? formatCurrency(
                  data.reduce((sum, d) => sum + d.avg_price, 0) / data.length
                )
              : '$0.00'}
          </span>
          <span className="stat-label">Avg Price (All Regions)</span>
        </div>
      </div>

      <style jsx>{`
        .heatmap-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        .heatmap-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .heatmap-title {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: #1f2937;
        }
        .metric-selector {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .metric-selector label {
          font-size: 14px;
          color: #6b7280;
        }
        .metric-selector select {
          padding: 6px 12px;
          font-size: 14px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: white;
          cursor: pointer;
        }
        .heatmap-svg {
          width: 100%;
          max-height: 500px;
        }
        .region-circle {
          transition: opacity 0.2s, r 0.2s;
        }
        .region-circle.clickable {
          cursor: pointer;
        }
        .region-circle.clickable:hover {
          opacity: 1 !important;
        }
        .region-circle:focus {
          outline: 2px solid #0066cc;
          outline-offset: 2px;
        }
        .tooltip {
          position: fixed;
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 12px 16px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 1000;
          pointer-events: none;
          min-width: 200px;
        }
        .tooltip-header {
          font-weight: 600;
          font-size: 14px;
          color: #1f2937;
          margin-bottom: 8px;
          padding-bottom: 8px;
          border-bottom: 1px solid #e5e7eb;
        }
        .tooltip-row {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          margin-bottom: 4px;
        }
        .tooltip-label {
          color: #6b7280;
        }
        .tooltip-value {
          font-weight: 500;
          color: #1f2937;
        }
        .heatmap-summary {
          display: flex;
          justify-content: space-around;
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #e5e7eb;
        }
        .summary-stat {
          text-align: center;
        }
        .stat-value {
          display: block;
          font-size: 24px;
          font-weight: 700;
          color: #1f2937;
        }
        .stat-label {
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
        }
      `}</style>
    </div>
  );
};

export default PricingHeatmap;
