/**
 * PromoCalibrationSlider Component
 *
 * A slider component for promotional calibration with AI recommendations.
 * Features:
 * - Debounced inference call (300ms) to prevent API spam
 * - Visual "AI Anchor Point" on slider vs user's selected position
 * - Confidence bands visualization showing AI uncertainty
 * - Optimistic UI updates
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import debounce from 'lodash.debounce';

/**
 * Props interface for PromoCalibrationSlider component
 */
export interface PromoCalibrationSliderProps {
  /** SKU identifier for the product */
  skuId: string;
  /** Current price of the product */
  currentPrice: number;
  /** Confidence interval from AI (lower, upper bounds) */
  confidenceInterval: [number, number];
  /** AI recommended promotional value */
  aiRecommendedValue: number;
  /** Callback when user changes the slider value */
  onValueChange: (value: number) => void;
  /** Type of promotion: volume discount or percentage off */
  promoType: 'volume' | 'percentage';
  /** Loading state indicator */
  isLoading?: boolean;
}

/**
 * API response interface for promo simulation
 */
interface PromoSimulationResponse {
  projected_lift: number;
  confidence_interval: [number, number];
  ai_recommended_value: number;
  calibration_score: number;
  latency_ms: number;
  model_version: string;
}

/**
 * PromoCalibrationSlider - Interactive slider for promotional value calibration
 *
 * @example
 * ```tsx
 * <PromoCalibrationSlider
 *   skuId="SKU-001"
 *   currentPrice={2.99}
 *   confidenceInterval={[10, 20]}
 *   aiRecommendedValue={15}
 *   onValueChange={(value) => console.log('New value:', value)}
 *   promoType="percentage"
 * />
 * ```
 */
export const PromoCalibrationSlider: React.FC<PromoCalibrationSliderProps> = ({
  skuId,
  currentPrice,
  confidenceInterval: initialConfidenceInterval,
  aiRecommendedValue: initialAiValue,
  onValueChange,
  promoType,
  isLoading: externalLoading = false,
}) => {
  // State
  const [sliderValue, setSliderValue] = useState<number>(initialAiValue);
  const [aiRecommendedValue, setAiRecommendedValue] = useState<number>(initialAiValue);
  const [confidenceInterval, setConfidenceInterval] = useState<[number, number]>(initialConfidenceInterval);
  const [projectedLift, setProjectedLift] = useState<number>(0);
  const [calibrationScore, setCalibrationScore] = useState<number>(0.8);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [latencyMs, setLatencyMs] = useState<number>(0);

  // Refs for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  // Calculate slider range based on promo type
  const getSliderConfig = useCallback(() => {
    if (promoType === 'percentage') {
      return { min: 0, max: 50, step: 1, unit: '%' };
    } else {
      return { min: 0, max: 500, step: 10, unit: ' units' };
    }
  }, [promoType]);

  const sliderConfig = getSliderConfig();

  /**
   * Call the inference API to simulate promo lift
   */
  const callInferenceAPI = useCallback(async (value: number) => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);

    // Use environment variable or default to relative API path
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
    
    try {
      const response = await fetch(`${apiBaseUrl}/v1/inference/simulate-promo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sku_id: skuId,
          current_price: currentPrice,
          promo_type: promoType,
          promo_value: value,
          location_code: '35242', // Default location
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data: PromoSimulationResponse = await response.json();

      // Update state with API response
      setConfidenceInterval(data.confidence_interval);
      setAiRecommendedValue(data.ai_recommended_value);
      setProjectedLift(data.projected_lift);
      setCalibrationScore(data.calibration_score);
      setLatencyMs(data.latency_ms);
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Inference API error:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [skuId, currentPrice, promoType]);

  /**
   * Debounced inference call (300ms delay)
   */
  const debouncedInference = useCallback(
    debounce((value: number) => {
      callInferenceAPI(value);
    }, 300),
    [callInferenceAPI]
  );

  /**
   * Handle slider value change with optimistic UI update
   */
  const handleSliderChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = Number(event.target.value);

    // Optimistic UI update
    setSliderValue(newValue);
    onValueChange(newValue);

    // Debounced API call
    debouncedInference(newValue);
  }, [onValueChange, debouncedInference]);

  /**
   * Calculate the position percentage for visual elements
   */
  const calculatePosition = useCallback((value: number): number => {
    const range = sliderConfig.max - sliderConfig.min;
    return ((value - sliderConfig.min) / range) * 100;
  }, [sliderConfig]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      debouncedInference.cancel();
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [debouncedInference]);

  // Calculate visual positions
  const sliderPosition = calculatePosition(sliderValue);
  const aiPosition = calculatePosition(aiRecommendedValue);
  const confidenceLowerPosition = calculatePosition(confidenceInterval[0]);
  const confidenceUpperPosition = calculatePosition(confidenceInterval[1]);
  const confidenceWidth = confidenceUpperPosition - confidenceLowerPosition;

  const loading = isLoading || externalLoading;

  return (
    <div className="promo-calibration-slider" style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.title}>
          Promotional Calibration
          {loading && <span style={styles.loadingIndicator}>⏳</span>}
        </h3>
        <span style={styles.skuBadge}>SKU: {skuId}</span>
      </div>

      {/* Projected Lift Display */}
      <div style={styles.liftDisplay}>
        <span style={styles.liftLabel}>Projected Lift:</span>
        <span style={styles.liftValue}>{projectedLift.toFixed(1)}%</span>
        <span style={styles.confidenceLabel}>
          (CI: {confidenceInterval[0].toFixed(1)}% - {confidenceInterval[1].toFixed(1)}%)
        </span>
      </div>

      {/* Slider Container */}
      <div style={styles.sliderContainer}>
        {/* Confidence Band Visualization */}
        <div
          style={{
            ...styles.confidenceBand,
            left: `${confidenceLowerPosition}%`,
            width: `${confidenceWidth}%`,
          }}
          title={`Confidence Interval: ${confidenceInterval[0].toFixed(1)} - ${confidenceInterval[1].toFixed(1)}`}
        />

        {/* AI Anchor Point */}
        <div
          style={{
            ...styles.aiAnchor,
            left: `${aiPosition}%`,
          }}
          title={`AI Recommended: ${aiRecommendedValue}${sliderConfig.unit}`}
        >
          <div style={styles.aiAnchorMarker}>AI</div>
        </div>

        {/* Slider Input */}
        <input
          type="range"
          min={sliderConfig.min}
          max={sliderConfig.max}
          step={sliderConfig.step}
          value={sliderValue}
          onChange={handleSliderChange}
          style={styles.slider}
          disabled={loading}
        />

        {/* Current Value Indicator */}
        <div
          style={{
            ...styles.valueIndicator,
            left: `${sliderPosition}%`,
          }}
        >
          {sliderValue}{sliderConfig.unit}
        </div>
      </div>

      {/* Labels */}
      <div style={styles.labels}>
        <span>{sliderConfig.min}{sliderConfig.unit}</span>
        <span>{sliderConfig.max}{sliderConfig.unit}</span>
      </div>

      {/* Info Panel */}
      <div style={styles.infoPanel}>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>AI Recommended:</span>
          <span style={styles.infoValue}>{aiRecommendedValue.toFixed(1)}{sliderConfig.unit}</span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>Your Selection:</span>
          <span style={styles.infoValue}>{sliderValue}{sliderConfig.unit}</span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>Calibration Score:</span>
          <span style={styles.infoValue}>{(calibrationScore * 100).toFixed(0)}%</span>
        </div>
        {latencyMs > 0 && (
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>Latency:</span>
            <span style={styles.infoValue}>{latencyMs.toFixed(0)}ms</span>
          </div>
        )}
      </div>

      {/* Override Warning */}
      {Math.abs(sliderValue - aiRecommendedValue) > (sliderConfig.max * 0.1) && (
        <div style={styles.overrideWarning}>
          ⚠️ Your selection differs significantly from AI recommendation.
          This override will be logged for model improvement.
        </div>
      )}
    </div>
  );
};

/**
 * Component styles
 */
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '20px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    maxWidth: '600px',
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: '#333',
  },
  loadingIndicator: {
    marginLeft: '8px',
    animation: 'spin 1s linear infinite',
  },
  skuBadge: {
    backgroundColor: '#e3f2fd',
    color: '#1565c0',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: 500,
  },
  liftDisplay: {
    textAlign: 'center' as const,
    marginBottom: '24px',
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
  liftLabel: {
    fontSize: '14px',
    color: '#666',
  },
  liftValue: {
    fontSize: '32px',
    fontWeight: 700,
    color: '#2e7d32',
    margin: '0 8px',
  },
  confidenceLabel: {
    fontSize: '12px',
    color: '#999',
  },
  sliderContainer: {
    position: 'relative' as const,
    height: '60px',
    marginBottom: '10px',
  },
  confidenceBand: {
    position: 'absolute' as const,
    top: '22px',
    height: '16px',
    backgroundColor: 'rgba(76, 175, 80, 0.2)',
    borderRadius: '4px',
    border: '1px solid rgba(76, 175, 80, 0.4)',
  },
  aiAnchor: {
    position: 'absolute' as const,
    top: '0',
    transform: 'translateX(-50%)',
    zIndex: 2,
  },
  aiAnchorMarker: {
    backgroundColor: '#ff9800',
    color: 'white',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
  },
  slider: {
    position: 'absolute' as const,
    top: '20px',
    width: '100%',
    height: '20px',
    cursor: 'pointer',
    WebkitAppearance: 'none' as any,
    appearance: 'none' as any,
    background: 'transparent',
    zIndex: 3,
  },
  valueIndicator: {
    position: 'absolute' as const,
    bottom: '0',
    transform: 'translateX(-50%)',
    backgroundColor: '#1976d2',
    color: 'white',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 500,
  },
  labels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: '#999',
    marginBottom: '20px',
  },
  infoPanel: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    padding: '16px',
    backgroundColor: '#fafafa',
    borderRadius: '8px',
  },
  infoItem: {
    display: 'flex',
    flexDirection: 'column' as const,
  },
  infoLabel: {
    fontSize: '11px',
    color: '#999',
    marginBottom: '4px',
  },
  infoValue: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#333',
  },
  overrideWarning: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#fff3e0',
    border: '1px solid #ffb74d',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#e65100',
  },
};

export default PromoCalibrationSlider;
