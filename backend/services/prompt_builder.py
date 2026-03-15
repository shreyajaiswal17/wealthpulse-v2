def build_dost_prompt(portfolio_summary: dict) -> tuple[str, str]:
    system = """You are AI Dost, a friendly Indian personal finance assistant.
You speak in a warm, clear tone — like a knowledgeable friend, not a banker.
Give practical, actionable advice. Use INR where relevant. Be concise (max 200 words)."""

    user = f"""Here is the user's portfolio summary:
- Total Invested: ₹{portfolio_summary.get('total_invested', 0):,.0f}
- Current Value: ₹{portfolio_summary.get('current_value', 0):,.0f}
- Total P&L: ₹{portfolio_summary.get('total_pnl', 0):,.0f} ({portfolio_summary.get('total_return_pct', 0):.1f}%)
- XIRR: {portfolio_summary.get('xirr', 0):.1f}%
- Sharpe Ratio: {portfolio_summary.get('sharpe_ratio', 0):.2f}
- Max Drawdown: {portfolio_summary.get('max_drawdown', 0):.1f}%
- Holdings: {portfolio_summary.get('holdings_count', 0)} assets across {portfolio_summary.get('asset_types', [])}

Give a brief, friendly analysis and 2-3 actionable suggestions."""

    return system, user


def build_report_prompt(portfolio_summary: dict) -> tuple[str, str]:
    system = """You are a professional financial analyst. Generate a structured portfolio report.
Use markdown formatting with headers. Be data-driven and objective. Max 400 words."""

    user = f"""Generate a portfolio health report for:
- Total Invested: ₹{portfolio_summary.get('total_invested', 0):,.0f}
- Current Value: ₹{portfolio_summary.get('current_value', 0):,.0f}
- Total P&L: ₹{portfolio_summary.get('total_pnl', 0):,.0f} ({portfolio_summary.get('total_return_pct', 0):.1f}%)
- XIRR: {portfolio_summary.get('xirr', 0):.1f}%
- Sharpe Ratio: {portfolio_summary.get('sharpe_ratio', 0):.2f}
- Volatility: {portfolio_summary.get('volatility', 0):.1f}%
- Max Drawdown: {portfolio_summary.get('max_drawdown', 0):.1f}%
- Monte Carlo (median 1yr): ₹{portfolio_summary.get('monte_carlo_median', 0):,.0f}
- Holdings breakdown: {portfolio_summary.get('holdings', [])}

Include: Executive Summary, Risk Assessment, Growth Outlook, Recommendations."""

    return system, user
