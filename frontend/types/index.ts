/**
 * Type definitions for PricePoint Intel frontend components.
 */

// ============================================
// SKU Types
// ============================================

export interface SKU {
  sku_id: string;
  product_name: string;
  description?: string;
  category: ProductCategory;
  subcategory?: string;
  dimensions?: SKUDimensions;
  unit_of_measure: string;
  units_per_case?: number;
  supplier_info?: SupplierInfo;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  attributes?: Record<string, unknown>;
}

export interface SKUDimensions {
  weight_lbs?: number;
  length_inches?: number;
  width_inches?: number;
  height_inches?: number;
}

export interface SupplierInfo {
  primary_supplier_id?: string;
  manufacturer?: string;
  manufacturer_part_number?: string;
  upc_code?: string;
}

export type ProductCategory =
  | 'flooring'
  | 'building_materials'
  | 'electrical'
  | 'plumbing'
  | 'hvac'
  | 'hardware'
  | 'lumber'
  | 'paint'
  | 'tools'
  | 'other';

// ============================================
// Vendor Types
// ============================================

export interface Vendor {
  vendor_id: string;
  vendor_name: string;
  vendor_type?: VendorType;
  contact?: VendorContact;
  headquarters?: VendorLocation;
  metrics?: VendorMetrics;
  api_enabled: boolean;
  is_active: boolean;
}

export type VendorType = 'distributor' | 'manufacturer' | 'retailer' | 'wholesaler' | 'other';

export interface VendorContact {
  email?: string;
  phone?: string;
  website?: string;
}

export interface VendorLocation {
  address?: string;
  city?: string;
  state?: string;
  country: string;
  zip?: string;
  latitude?: number;
  longitude?: number;
}

export interface VendorMetrics {
  reliability_score?: number;
  avg_lead_time_days?: number;
  min_order_value?: number;
}

// ============================================
// Pricing Types
// ============================================

export interface VendorPricing {
  sku_id: string;
  vendor_id: string;
  market_id?: string;
  price: number;
  currency: Currency;
  price_per_unit?: number;
  unit_of_measure: string;
  volume_pricing?: Record<string, number>;
  geographic_region?: string;
  effective_date?: string;
  expiration_date?: string;
  confidence_score?: number;
  data_source?: string;
  is_verified: boolean;
  last_updated?: string;
}

export type Currency = 'USD' | 'EUR' | 'GBP' | 'CAD' | 'MXN';

// ============================================
// Geographic Types
// ============================================

export interface GeographicMarket {
  market_id: string;
  region_name: string;
  region_code?: string;
  country_code: string;
  coordinates: Coordinates;
  bounding_box?: BoundingBox;
  market_size_tier: MarketSizeTier;
  population?: number;
  gdp_per_capita?: number;
  cost_indices: CostIndices;
  is_active: boolean;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface BoundingBox {
  north?: number;
  south?: number;
  east?: number;
  west?: number;
}

export type MarketSizeTier = 'tier_1' | 'tier_2' | 'tier_3' | 'tier_4';

export interface CostIndices {
  cost_of_living_index: number;
  regional_price_multiplier: number;
}

// ============================================
// Search & Filter Types
// ============================================

export interface SKUSearchFilters {
  query?: string;
  category?: ProductCategory;
  supplier_id?: string;
  region?: string;
  min_price?: number;
  max_price?: number;
  is_active?: boolean;
}

export interface SKUSearchResult {
  skus: SKUWithPricing[];
  total_count: number;
  page: number;
  page_size: number;
  filters_applied: SKUSearchFilters;
}

export interface SKUWithPricing extends SKU {
  prices?: VendorPricing[];
  avg_price?: number;
  price_range?: [number, number];
  vendor_count?: number;
}

// ============================================
// Heatmap Types
// ============================================

export interface RegionPricingData {
  region: string;
  region_code: string;
  coordinates: Coordinates;
  avg_price: number;
  min_price: number;
  max_price: number;
  vendor_count: number;
  sku_count: number;
  price_index: number; // Normalized 0-1 for color scale
}

export interface HeatmapConfig {
  colorScale: string[];
  minValue?: number;
  maxValue?: number;
  showLabels: boolean;
  metric: 'avg_price' | 'vendor_count' | 'price_index';
}

// ============================================
// Vendor Matrix Types
// ============================================

export interface VendorSKURelationship {
  vendor_id: string;
  vendor_name: string;
  sku_ids: string[];
  sku_count: number;
  categories: ProductCategory[];
  total_price_volume: number;
  avg_price_deviation: number;
}

export interface VendorMatrixCell {
  vendor_id: string;
  sku_id: string;
  has_pricing: boolean;
  price?: number;
  price_rank?: number; // 1 = lowest price for this SKU
  is_primary_supplier: boolean;
}

export interface VendorMatrixData {
  vendors: Vendor[];
  skus: SKU[];
  matrix: VendorMatrixCell[][];
  summary: VendorMatrixSummary;
}

export interface VendorMatrixSummary {
  total_vendors: number;
  total_skus: number;
  coverage_pct: number; // % of vendor-SKU pairs with pricing
  multi_source_skus: number; // SKUs with 2+ vendors
  single_source_skus: number; // SKUs with only 1 vendor
}

// ============================================
// API Response Types
// ============================================

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================
// Component Props Types
// ============================================

export interface SKUSearchProps {
  onSearch: (filters: SKUSearchFilters) => void;
  onSKUSelect?: (sku: SKUWithPricing) => void;
  initialFilters?: SKUSearchFilters;
  categories?: ProductCategory[];
  regions?: string[];
  suppliers?: { id: string; name: string }[];
  isLoading?: boolean;
}

export interface PricingHeatmapProps {
  data: RegionPricingData[];
  config?: Partial<HeatmapConfig>;
  onRegionClick?: (region: RegionPricingData) => void;
  onRegionHover?: (region: RegionPricingData | null) => void;
  width?: number;
  height?: number;
  title?: string;
}

export interface VendorMatrixProps {
  data: VendorMatrixData;
  onCellClick?: (cell: VendorMatrixCell) => void;
  onVendorClick?: (vendor: Vendor) => void;
  onSKUClick?: (sku: SKU) => void;
  showPriceRanking?: boolean;
  highlightSingleSource?: boolean;
}
