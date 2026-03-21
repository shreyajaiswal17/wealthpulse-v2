def _aggregate_holdings_metrics(holdings: list) -> dict:
    """
    Compute aggregated metrics from holdings list.
    Returns dict with avg_xirr, avg_sharpe, avg_volatility, mc_p50_median
    """
    # Average XIRR across holdings
    xirr_values = [h.get("xirr", 0) for h in holdings if h.get("xirr")]
    avg_xirr = sum(xirr_values) / len(xirr_values) if xirr_values else 0.0

    # Average Sharpe from risk
    sharpe_values = [h.get("risk", {}).get("sharpe", 0) for h in holdings if h.get("risk")]
    avg_sharpe = sum(sharpe_values) / len(sharpe_values) if sharpe_values else 0.0

    # Average volatility from risk
    vol_values = [h.get("risk", {}).get("volatility", 0) for h in holdings if h.get("risk")]
    avg_volatility = sum(vol_values) / len(vol_values) if vol_values else 0.0

    # Median Monte Carlo p50 (expected 1yr value)
    mc_p50_values = [h.get("montecarlo", {}).get("p50", 0) for h in holdings if h.get("montecarlo")]
    mc_p50_median = sum(mc_p50_values) / len(mc_p50_values) if mc_p50_values else 0.0

    return {
        "avg_xirr": avg_xirr,
        "avg_sharpe": avg_sharpe,
        "avg_volatility": avg_volatility,
        "mc_p50_median": mc_p50_median,
    }


def build_dost_prompt(portfolio_summary: dict) -> tuple[str, str]:
    system = """You are AI Dost, a friendly Indian personal finance assistant.
You speak in a warm, clear tone — like a knowledgeable friend, not a banker.
Give practical, actionable advice. Use INR where relevant. Be concise (max 200 words)."""

    # Extract direct keys from summary
    total_invested = portfolio_summary.get("total_invested", 0)
    total_current = portfolio_summary.get("total_current_value", 0)
    total_pnl = portfolio_summary.get("total_pnl", 0)
    total_pnl_pct = portfolio_summary.get("total_pnl_pct", 0)

    # Get aggregated metrics from holdings
    holdings = portfolio_summary.get("holdings", [])
    metrics = _aggregate_holdings_metrics(holdings)

    # Determine portfolio state
    has_single_asset = len(holdings) == 1
    has_basic_metrics = total_invested > 0 and total_current > 0

    # Build metrics display section
    metrics_section = f"""- Total Invested: ₹{total_invested:,.0f}
- Current Value: ₹{total_current:,.0f}
- Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:.1f}%)
- Avg XIRR: {metrics['avg_xirr']:.1f}%
- Avg Sharpe Ratio: {metrics['avg_sharpe']:.2f}
- Avg Volatility: {metrics['avg_volatility']:.1f}%
- Monte Carlo Expected 1yr Value: ₹{metrics['mc_p50_median']:,.0f}
- Holdings: {len(holdings)} assets"""

    # Add note if risk metrics are zero but portfolio is real
    risk_note = ""
    if has_basic_metrics and (metrics['avg_xirr'] == 0 or metrics['avg_sharpe'] == 0 or metrics['avg_volatility'] == 0):
        risk_note = "\n\nNote: Some advanced metrics like XIRR and Sharpe Ratio are 0.0 right now, which usually just means there isn't enough historical data yet, not that your portfolio is empty."

    user = f"""Here is the user's portfolio summary:
{metrics_section}{risk_note}

Give a brief, friendly analysis and 2-3 actionable suggestions."""

    return system, user


def build_report_prompt(portfolio_summary: dict) -> tuple[str, str]:
    system = """You are a professional financial analyst. Generate a structured portfolio report.
Use markdown formatting with headers. Be data-driven and objective. Max 400 words."""

    # Extract direct keys from summary
    total_invested = portfolio_summary.get("total_invested", 0)
    total_current = portfolio_summary.get("total_current_value", 0)
    total_pnl = portfolio_summary.get("total_pnl", 0)
    total_pnl_pct = portfolio_summary.get("total_pnl_pct", 0)

    # Get aggregated metrics from holdings
    holdings = portfolio_summary.get("holdings", [])
    metrics = _aggregate_holdings_metrics(holdings)

    # Build holdings breakdown
    holdings_lines = []
    for h in holdings:
        pnl_pct = h.get("pnl", {}).get("pnl_pct", 0)
        invested = h.get("pnl", {}).get("invested", 0)
        current = h.get("pnl", {}).get("current_value", 0)
        symbol = h.get("name", h.get("symbol"))
        asset_type = h.get("asset_type", "")
        holdings_lines.append(
            f"- {symbol} ({asset_type}): invested ₹{invested:,.0f}, current ₹{current:,.0f}, P&L {pnl_pct:.1f}%"
        )
    holdings_text = "\n".join(holdings_lines) if holdings_lines else "(No holdings data)"

    # Determine portfolio state
    has_real_investment = total_invested > 0
    has_limited_data = (metrics['avg_xirr'] == 0 or metrics['avg_sharpe'] == 0 or
                       metrics['avg_volatility'] == 0 or metrics['mc_p50_median'] == 0)

    # Build conditional text blocks
    portfolio_status = ""
    if has_real_investment:
        portfolio_status = f"""Your portfolio shows an initial investment of ₹{total_invested:,.0f} with a current value of ₹{total_current:,.0f}, representing a total P&L of ₹{total_pnl:,.0f} ({total_pnl_pct:.1f}%)."""
    else:
        portfolio_status = "Your portfolio currently has no active investments or is entirely in cash."

    risk_note = ""
    if has_limited_data:
        risk_note = "\n\n**Data Availability Note:** Some predictive and risk metrics are 0.0, which usually means there isn't enough historical price data yet. This does not indicate a portfolio problem."

    user = f"""Generate a portfolio health report based on:
- Total Invested: ₹{total_invested:,.0f}
- Current Value: ₹{total_current:,.0f}
- Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:.1f}%)
- Avg XIRR: {metrics['avg_xirr']:.1f}%
- Avg Sharpe Ratio: {metrics['avg_sharpe']:.2f}
- Avg Volatility: {metrics['avg_volatility']:.1f}%
- Monte Carlo Expected 1yr Value: ₹{metrics['mc_p50_median']:,.0f}

**Portfolio Status:** {portfolio_status}

HOLDINGS BREAKDOWN:
{holdings_text}{risk_note}

Structure with: Executive Summary (investment status and P&L), Risk Assessment (volatility, Sharpe, diversification), Growth Outlook (XIRR trends and Monte Carlo insights), and Recommendations (actionable next steps)."""

    return system, user
