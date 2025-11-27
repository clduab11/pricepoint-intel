# PRICEPOINT INTEL

> **SKU-Level Competitive Intelligence Platform for Real-Time Cost Analysis & Vendor Discovery**

A research-driven competitive intelligence system that transforms geopolitical risk analysis frameworks into procurement intelligence. Built for executives who need instant access to pricing data, vendor relationships, and cost benchmarking across geographic markets.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status: Research Phase](https://img.shields.io/badge/status-research-orange.svg)](https://github.com/clduab11/pricepoint-intel)

---

## 🎯 Project Vision

**The Problem:**
An EVP in flooring types "laminate flooring" + zip code and spends hours manually searching for:
- Current vendor pricing across distributors
- Public procurement records showing competitor costs
- Vendor relationship networks and supply chains  
- Financial filings revealing cost structures
- Geographic price variations and market intelligence

**The Solution:**
One search query returns comprehensive SKU-level intelligence:
```
Query: "laminate flooring, 35242"

Results:
├─ Real-time pricing: 47 vendors, $1.89-$4.23/sqft
├─ Public records: 23 procurement contracts (city, county, state)
├─ Vendor network: 12 primary suppliers, 8 distribution relationships
├─ Cost benchmarks: Industry avg $2.67/sqft, 15% geographic premium
├─ Financial intel: 5 recent filings, margin analysis, cost trends
└─ Risk scores: Supply chain stability, price volatility, availability
```

---

## 🏗️ Architecture Foundation

### Adapted from GEOPOLITIX Framework

This project inherits architectural patterns from [geopolitix](https://github.com/clduab11/geopolitix):

| Geopolitix Component | PricePoint Intel Adaptation |
|---------------------|-----------------------------|
| **Risk scoring engine** | → **Price volatility & availability scoring** |
| **Multi-source data aggregation** | → **SKU pricing from vendors, public records, filings** |
| **Geographic visualization** | → **Cost heatmaps by zip/region** |
| **Real-time alerting** | → **Price change notifications & opportunity alerts** |
| **API integration layer** | → **Vendor APIs, public data, financial sources** |
| **Interactive dashboard** | → **Executive pricing intelligence interface** |

### Core Intelligence Modules

```
pricepoint_intel/
├── data_sources/           # Multi-channel data acquisition
│   ├── vendor_apis/        # Direct vendor pricing APIs
│   ├── public_records/     # FOIA, procurement databases
│   ├── financial_scraping/ # SEC filings, annual reports
│   ├── market_data/        # Industry benchmarks, indices
│   └── relationship_mapping/ # Supply chain network analysis
│
├── intelligence_engine/    # Core analysis algorithms
│   ├── sku_matcher/        # Product matching across sources
│   ├── price_normalization/ # Geographic & volume adjustments
│   ├── cost_benchmarking/  # Competitive position analysis
│   ├── vendor_discovery/   # Relationship network extraction
│   └── predictive_models/  # Price forecasting & trends
│
├── visualization/          # Executive dashboards
│   ├── geographic_pricing/ # Interactive cost maps
│   ├── vendor_networks/    # Relationship visualizations
│   ├── trend_analysis/     # Historical & predictive charts
│   └── comparative_tools/  # Multi-vendor benchmarking
│
└── api_layer/             # Integration & automation
    ├── query_interface/    # Natural language search
    ├── webhook_alerts/     # Real-time price notifications
    └── export_engine/      # Reports & data feeds
```

---

## 📊 Data Source Strategy

### Primary Intelligence Streams

#### 1. **Vendor Pricing Data**
- **B2B marketplaces**: BuildDirect, FloorAndDecor.com, Ferguson
- **Distributor APIs**: HD Supply, Lowe's Pro, ABC Supply
- **Regional suppliers**: Local distributor websites (web scraping)
- **Volume pricing**: Contract pricing tiers from catalogs

#### 2. **Public Procurement Records**
- **Federal**: SAM.gov, USASpending.gov
- **State**: State purchasing portals (all 50 states)
- **Municipal**: City/county procurement databases
- **Education**: University purchasing records (often public)
- **Utilities**: Public utility procurement filings

#### 3. **Financial Intelligence**
- **SEC filings**: 10-K/10-Q for material costs, supplier relationships
- **Annual reports**: Cost structure analysis, margin data
- **Investor presentations**: Market positioning, pricing strategy
- **Credit reports**: D&B, Experian for vendor financial health

#### 4. **Industry Benchmarks**
- **Trade associations**: NWFA, NOFMA pricing surveys
- **Market research**: IBISWorld, Statista industry reports
- **Academic studies**: University procurement research
- **Government statistics**: BLS Producer Price Index data

#### 5. **Relationship Discovery**
- **Supply chain databases**: Panjiva, ImportGenius for imports
- **Corporate filings**: Supplier lists in annual reports
- **Trade show data**: Exhibitor-buyer connections
- **News & press releases**: Partnership announcements

### API Integration Requirements

**Phase 1 - Free/Public Sources:**
- SAM.gov API (federal procurement)
- State purchasing portal scrapers
- Public financial filing parsers (SEC EDGAR)
- OpenStreetMap for geographic data

**Phase 2 - Paid Intelligence APIs:**
- **Pricing data**: Competera, Intelligence Node
- **Financial data**: Bloomberg API, FactSet
- **Supply chain**: Panjiva, ImportGenius
- **Web scraping**: Bright Data, Oxylabs

**Phase 3 - Advanced AI:**
- **LLM integration**: Claude/GPT for document analysis
- **Computer vision**: Product image matching across vendors
- **NLP**: Contract & filing analysis for cost intelligence

---

## 🔬 Research Milestones

### Phase 1: Foundation (Weeks 1-4)
- [ ] Data source inventory & API documentation
- [ ] Public procurement database mapping (federal, state, local)
- [ ] SKU matching algorithm research & prototyping
- [ ] Price normalization methodology (geography, volume, time)
- [ ] Basic vendor relationship graph model

### Phase 2: Core Engine (Weeks 5-10)
- [ ] Multi-source data ingestion pipeline
- [ ] SKU standardization & matching system
- [ ] Price benchmarking algorithms
- [ ] Vendor network extraction from public records
- [ ] Geographic cost modeling

### Phase 3: Intelligence Layer (Weeks 11-16)
- [ ] Predictive pricing models
- [ ] Competitive position scoring
- [ ] Vendor risk assessment (supply chain, financial)
- [ ] Opportunity detection algorithms
- [ ] Alert & notification system

### Phase 4: Interface (Weeks 17-20)
- [ ] Executive dashboard (Dash/Streamlit)
- [ ] Natural language query interface
- [ ] Interactive pricing maps
- [ ] Vendor relationship visualizations
- [ ] Export & reporting tools

### Phase 5: Market Validation (Weeks 21-26)
- [ ] Beta testing with flooring industry executives
- [ ] Pricing accuracy validation against known contracts
- [ ] User experience refinement
- [ ] Vertical expansion strategy (beyond flooring)
- [ ] Business model & monetization research

---

## 🎓 Academic & Financial Metrics

### Research Validation Framework

#### Cost Accuracy Metrics
1. **Price Prediction Error**: Mean Absolute Percentage Error (MAPE) vs actual procurement costs
   - Target: <5% MAPE for 80% of SKUs
   - Benchmark: Industry standard ±8-12%

2. **Source Coverage Score**: % of market captured by data sources
   - Formula: `(Tracked Vendors × Market Share) / Total Market`
   - Target: >70% of regional market coverage

3. **Data Freshness Index**: Time decay of pricing information
   - Real-time APIs: 0-24 hours = 1.0
   - Quarterly reports: 30-90 days = 0.5
   - Annual filings: >90 days = 0.2

#### Intelligence Quality Metrics

1. **Vendor Relationship Precision**: Accuracy of discovered supplier networks
   ```
   Precision = True Positive Relationships / (True Positive + False Positive)
   Recall = True Positive Relationships / (True Positive + False Negative)
   F1 Score = 2 × (Precision × Recall) / (Precision + Recall)
   ```
   - Target F1: >0.85

2. **Cost Benchmark Reliability**: Variance from validated procurement outcomes
   - Standard deviation from actual costs in blind validation set
   - Target: σ < $0.15/sqft for flooring (example)

3. **Geographic Adjustment Accuracy**: Price normalization performance
   - Compare predicted regional prices vs actual local procurement
   - Measure R² of geographic cost model

### Financial Performance Indicators

#### User Value Metrics
1. **Time Savings**: Manual research time vs platform query time
   - Baseline: 4-6 hours manual research per procurement decision
   - Target: <5 minutes for comprehensive intelligence
   - **Value**: 48-72x time efficiency

2. **Cost Savings**: Procurement cost reduction from better intelligence
   - Industry benchmark: 8-12% savings from data-driven procurement
   - Target: Enable 10%+ cost reduction
   - **ROI**: $100K project saves $200K+ annually on $2M procurement

3. **Decision Confidence**: % of recommendations accepted
   - Track adoption rate of platform pricing recommendations
   - Target: >75% of recommendations implemented

#### Platform Economics
1. **Data Acquisition Cost**: Cost per SKU per month
   ```
   CAC = (API Costs + Scraping Infrastructure + Data Cleaning) / SKUs Tracked
   ```
   - Target: <$0.50 per SKU per month

2. **Query Cost**: Compute & data costs per intelligence query
   - Target: <$0.25 per comprehensive search

3. **Customer Acquisition Cost**: Sales & marketing per customer
   - B2B SaaS benchmark: CAC should be recovered in <12 months
   - LTV:CAC ratio target: >3:1

### Academic Research Applications

**Potential Research Papers:**
1. "Multi-Source Price Intelligence: A Graph-Based Approach to Procurement Cost Discovery"
2. "Vendor Network Extraction from Heterogeneous Public Records Using NLP"
3. "Geographic Cost Modeling: Machine Learning for Regional Price Prediction"
4. "Financial Filing Analysis for Supply Chain Relationship Discovery"
5. "Real-Time Competitive Intelligence: Architecture for Sub-Second SKU Pricing Analysis"

**Citation Framework:**
- Methodology papers: 15-20 academic citations
- Industry validation: 3-5 case studies with real procurement data
- Benchmark comparisons: Manual research, existing platforms (GrowByData, Intelligence Node)

---

## 🚀 Quick Start (Research Mode)

### Prerequisites
```bash
# Python 3.9+
python --version

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Installation
```bash
# Clone repository
git clone https://github.com/clduab11/pricepoint-intel.git
cd pricepoint-intel

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add API keys for data sources
```

### Run Prototype
```bash
# Start research dashboard
python app.py

# Open browser
http://localhost:8050
```

### Example Query (CLI)
```python
from pricepoint_intel import IntelligenceEngine

# Initialize
engine = IntelligenceEngine()

# Query: Laminate flooring in Birmingham, AL area
results = engine.query(
    product="laminate flooring",
    location="35242",  # Vestavia Hills, AL
    radius_miles=50
)

# Results
print(results.summary())
# → 47 vendors found
# → Price range: $1.89-$4.23/sqft
# → Market average: $2.67/sqft
# → 23 public procurement records
# → 12 supplier relationships discovered
```

---

## 🔐 Data Privacy & Ethics

### Data Handling Principles
1. **Public data only**: No scraping of password-protected systems
2. **Respect robots.txt**: Comply with website crawling policies
3. **Rate limiting**: Respectful API usage, no server overload
4. **Attribution**: Credit data sources appropriately
5. **Anonymization**: Aggregate pricing data, protect individual contracts when required

### Compliance Considerations
- **FOIA regulations**: Proper handling of government data
- **Terms of Service**: Compliance with vendor website ToS
- **Competition law**: Avoid facilitating price-fixing
- **Data licensing**: Respect commercial data provider agreements

---

## 📚 Research Resources

### Industry Context
- [Competitive Price Intelligence - GrowByData](https://growbydata.com/price-intelligence/)
- [SKU-Level Analytics - OpenBrand](https://openbrand.com/competitive-intelligence)
- [Procurement Benchmarking - World Bank](https://thedocs.worldbank.org/en/doc/price-benchmarking)
- [Academic Procurement Research](https://academic.oup.com/procurement-cost-effectiveness)

### Technical References
- [Geospatial Risk Analysis](https://github.com/clduab11/geopolitix) - Parent framework
- [Price Scraping Legal Framework](https://www.eff.org/issues/coders/reverse-engineering-faq)
- [Public Procurement Data Standards](https://standard.open-contracting.org/)
- [SKU Matching Algorithms](https://arxiv.org/search/?query=product+matching)

### Competitive Analysis
- **Enterprise platforms**: Competera, Intelligence Node, Profitero
- **Procurement tools**: Coupa, Jaggaer, GEP SMART
- **Price monitoring**: Prisync, Wiser, Omnia Retail
- **Our differentiator**: SKU-level + vendor relationships + public records integration

---

## 🤝 Contributing

### Research Contributors Wanted
- **Data scientists**: Price prediction modeling, geographic cost analysis
- **Web scraping experts**: Ethical data acquisition from public sources
- **Procurement professionals**: Domain expertise, validation datasets
- **Full-stack developers**: Dashboard & API development
- **Academic researchers**: Co-authorship on methodology papers

### How to Contribute
1. Fork the repository
2. Create feature branch (`git checkout -b feature/vendor-api-integration`)
3. Commit changes with clear documentation
4. Write tests for new functionality
5. Submit pull request with research notes

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

This is a research project. Use of data sources must comply with their respective terms of service and applicable laws.

---

## 🌟 Project Status

**Current Phase**: Research & Architecture (Week 1)

**Next Milestones**:
1. ✅ Repository initialization & documentation
2. ⏳ Data source API mapping (federal/state procurement)
3. ⏳ SKU matching algorithm literature review
4. ⏳ Price normalization methodology research
5. ⏳ Vendor relationship graph schema design

**Looking for**: Research partners, domain experts, beta testers from flooring/construction industries.

---

## 📧 Contact

**Project Lead**: clduab11  
**Organization**: Parallax Analytics, LLC  
**GitHub**: [@clduab11](https://github.com/clduab11)  
**Project Discussion**: [GitHub Issues](https://github.com/clduab11/pricepoint-intel/issues)

---

**Note**: This is an active research project. Code, documentation, and methodologies will evolve significantly. Star & watch the repository for updates!