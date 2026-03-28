"""
Report generator for backtesting results.

Generates HTML, text, and JSON reports with charts.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from trading_system.backtesting.engine import BacktestResult, Trade
from trading_system.backtesting.metrics import AdvancedMetrics, calculate_advanced_metrics


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str = "Backtest Report"
    include_charts: bool = True
    include_trades: bool = True
    include_advanced_metrics: bool = True
    output_format: str = "html"
    theme: str = "light"


@dataclass
class ChartConfig:
    """Configuration for charts."""
    width: int = 800
    height: int = 400
    show_volume: bool = True
    show_drawdown: bool = True
    colors: dict = field(default_factory=lambda: {
        "equity": "#2ecc71",
        "drawdown": "#e74c3c",
        "benchmark": "#3498db",
        "volume": "#95a5a6"
    })


class ReportGenerator:
    """
    Generates reports from backtest results.
    
    Supports HTML, JSON, and text formats with optional charts.
    
    Example:
        >>> config = ReportConfig(title="RSI Strategy Backtest")
        >>> generator = ReportGenerator(config)
        >>> html = generator.generate_html(result)
        >>> generator.save(html, "report.html")
    """

    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()

    def generate_html(
        self,
        result: BacktestResult,
        advanced_metrics: Optional[AdvancedMetrics] = None,
        prices: Optional[pd.Series] = None,
        benchmark: Optional[pd.Series] = None,
        chart_config: ChartConfig = None
    ) -> str:
        """Generate HTML report."""
        chart_config = chart_config or ChartConfig()

        html = self._html_header()
        html += self._html_styles()
        html += self._html_summary(result)
        html += self._html_metrics_table(result)
        
        if self.config.include_advanced_metrics and advanced_metrics:
            html += self._html_advanced_metrics(advanced_metrics)
        
        if self.config.include_charts and prices is not None:
            html += self._html_charts(result, prices, chart_config)
        
        if self.config.include_trades:
            html += self._html_trades_table(result.trades)
        
        html += self._html_footer()
        
        return html

    def generate_json(
        self,
        result: BacktestResult,
        advanced_metrics: Optional[AdvancedMetrics] = None
    ) -> str:
        """Generate JSON report."""
        data = {
            "strategy": result.strategy_name,
            "symbol": result.symbol,
            "period": {
                "start": result.start_date.isoformat(),
                "end": result.end_date.isoformat()
            },
            "capital": {
                "initial": result.initial_capital,
                "final": result.final_capital
            },
            "performance": {
                "total_return": result.total_return,
                "total_return_pct": f"{result.total_return * 100:.2f}%",
                "max_drawdown": result.max_drawdown_pct
            },
            "trading": {
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor
            },
            "risk": {
                "sharpe_ratio": result.sharpe_ratio,
                "sortino_ratio": result.sortino_ratio
            }
        }
        
        if advanced_metrics:
            data["advanced_metrics"] = {
                "calmar_ratio": advanced_metrics.calmar_ratio,
                "var_95": advanced_metrics.value_at_risk,
                "cvar_95": advanced_metrics.conditional_var,
                "tail_ratio": advanced_metrics.tail_ratio,
                "skewness": advanced_metrics.skewness,
                "kurtosis": advanced_metrics.kurtosis,
                "omega_ratio": advanced_metrics.omega_ratio,
                "ulcer_index": advanced_metrics.ulcer_index,
                "max_consecutive_losses": advanced_metrics.max_consecutive_losses,
                "uptime_ratio": advanced_metrics.uptime_ratio
            }
        
        return json.dumps(data, indent=2)

    def generate_text(self, result: BacktestResult) -> str:
        """Generate text report."""
        lines = [
            "=" * 60,
            f"BACKTEST REPORT: {result.strategy_name}",
            "=" * 60,
            f"Symbol: {result.symbol}",
            f"Period: {result.start_date.date()} to {result.end_date.date()}",
            "",
            "CAPITAL",
            "-" * 40,
            f"  Initial: ${result.initial_capital:,.2f}",
            f"  Final:   ${result.final_capital:,.2f}",
            "",
            "PERFORMANCE",
            "-" * 40,
            f"  Total Return:    {result.total_return * 100:>8.2f}%",
            f"  Max Drawdown:    {result.max_drawdown_pct * 100:>8.2f}%",
            "",
            "TRADING STATISTICS",
            "-" * 40,
            f"  Total Trades:    {result.total_trades:>8}",
            f"  Winning Trades:  {result.winning_trades:>8}",
            f"  Losing Trades:  {result.losing_trades:>8}",
            f"  Win Rate:       {result.win_rate * 100:>8.2f}%",
            f"  Profit Factor:  {result.profit_factor:>8.2f}",
            "",
            "RISK METRICS",
            "-" * 40,
            f"  Sharpe Ratio:   {result.sharpe_ratio:>8.2f}",
            f"  Sortino Ratio:  {result.sortino_ratio:>8.2f}",
            "",
            "AVERAGE TRADES",
            "-" * 40,
            f"  Avg Return:     {result.avg_trade_return * 100:>8.2f}%",
            f"  Avg Win:        ${result.avg_winning_trade:>8.2f}",
            f"  Avg Loss:       ${result.avg_losing_trade:>8.2f}",
            "=" * 60,
        ]
        return "\n".join(lines)

    def save(self, content: str, filepath: str) -> None:
        """Save report to file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def _html_header(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>{self.config.title}</h1>
"""

    def _html_styles(self) -> str:
        return """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; 
                        padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #3498db; color: white; }
            tr:hover { background: #f5f5f5; }
            .metric { display: inline-block; padding: 15px 25px; margin: 10px; 
                     background: #ecf0f1; border-radius: 8px; text-align: center; }
            .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .metric-label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; }
            .positive { color: #27ae60; }
            .negative { color: #e74c3c; }
            .chart { margin: 20px 0; }
        </style>
"""

    def _html_summary(self, result: BacktestResult) -> str:
        return f"""
        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Strategy:</strong> {result.strategy_name}</p>
            <p><strong>Symbol:</strong> {result.symbol}</p>
            <p><strong>Period:</strong> {result.start_date.date()} to {result.end_date.date()}</p>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">${result.final_capital:,.0f}</div>
                    <div class="metric-label">Final Capital</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'positive' if result.total_return > 0 else 'negative'}">{result.total_return * 100:.2f}%</div>
                    <div class="metric-label">Total Return</div>
                </div>
                <div class="metric">
                    <div class="metric-value negative">{result.max_drawdown_pct * 100:.2f}%</div>
                    <div class="metric-label">Max Drawdown</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{result.sharpe_ratio:.2f}</div>
                    <div class="metric-label">Sharpe Ratio</div>
                </div>
            </div>
        </div>
"""

    def _html_metrics_table(self, result: BacktestResult) -> str:
        return f"""
        <h2>Performance Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Initial Capital</td><td>${result.initial_capital:,.2f}</td></tr>
            <tr><td>Final Capital</td><td>${result.final_capital:,.2f}</td></tr>
            <tr><td>Total Return</td><td class="{'positive' if result.total_return > 0 else 'negative'}">{result.total_return * 100:.2f}%</td></tr>
            <tr><td>Max Drawdown</td><td class="negative">{result.max_drawdown_pct * 100:.2f}%</td></tr>
            <tr><td>Total Trades</td><td>{result.total_trades}</td></tr>
            <tr><td>Winning Trades</td><td class="positive">{result.winning_trades}</td></tr>
            <tr><td>Losing Trades</td><td class="negative">{result.losing_trades}</td></tr>
            <tr><td>Win Rate</td><td>{result.win_rate * 100:.2f}%</td></tr>
            <tr><td>Profit Factor</td><td>{result.profit_factor:.2f}</td></tr>
            <tr><td>Sharpe Ratio</td><td>{result.sharpe_ratio:.2f}</td></tr>
            <tr><td>Sortino Ratio</td><td>{result.sortino_ratio:.2f}</td></tr>
            <tr><td>Avg Trade Return</td><td>{result.avg_trade_return * 100:.2f}%</td></tr>
            <tr><td>Avg Winning Trade</td><td class="positive">${result.avg_winning_trade:,.2f}</td></tr>
            <tr><td>Avg Losing Trade</td><td class="negative">${result.avg_losing_trade:,.2f}</td></tr>
        </table>
"""

    def _html_advanced_metrics(self, metrics: AdvancedMetrics) -> str:
        return f"""
        <h2>Advanced Risk Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Calmar Ratio</td><td>{metrics.calmar_ratio:.2f}</td></tr>
            <tr><td>Value at Risk (95%)</td><td>{metrics.value_at_risk * 100:.2f}%</td></tr>
            <tr><td>Conditional VaR (95%)</td><td>{metrics.conditional_var * 100:.2f}%</td></tr>
            <tr><td>Tail Ratio</td><td>{metrics.tail_ratio:.2f}</td></tr>
            <tr><td>Skewness</td><td>{metrics.skewness:.2f}</td></tr>
            <tr><td>Kurtosis</td><td>{metrics.kurtosis:.2f}</td></tr>
            <tr><td>Omega Ratio</td><td>{metrics.omega_ratio:.2f}</td></tr>
            <tr><td>Ulcer Index</td><td>{metrics.ulcer_index:.2f}</td></tr>
            <tr><td>Max Consecutive Losses</td><td>{metrics.max_consecutive_losses}</td></tr>
            <tr><td>Uptime Ratio</td><td>{metrics.uptime_ratio * 100:.2f}%</td></tr>
            <tr><td>Gain to Pain Ratio</td><td>{metrics.gain_to_pain_ratio:.2f}</td></tr>
        </table>
"""

    def _html_charts(
        self,
        result: BacktestResult,
        prices: pd.Series,
        config: ChartConfig
    ) -> str:
        equity_json = result.equity_curve.to_json(orient='split')
        dates = result.equity_curve.index.strftime('%Y-%m-%d').tolist()
        
        return f"""
        <h2>Equity Curve</h2>
        <div id="equity-chart" class="chart"></div>
        <script>
            var equityData = {equity_json};
            var dates = {json.dumps(dates)};
            
            Plotly.newPlot('equity-chart', [{{
                x: dates,
                y: equityData.data,
                type: 'scatter',
                mode: 'lines',
                line: {{color: '{config.colors["equity"]}', width: 2}},
                name: 'Equity'
            }}], {{
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Capital ($)'}},
                hovermode: 'x'
            }});
        </script>
"""

    def _html_trades_table(self, trades: List[Trade]) -> str:
        if not trades:
            return ""
        
        rows = []
        for i, trade in enumerate(trades[:50]):
            rows.append(f"""
            <tr>
                <td>{i+1}</td>
                <td>{trade.entry_date.date()}</td>
                <td>{trade.exit_date.date()}</td>
                <td>${trade.entry_price:.2f}</td>
                <td>${trade.exit_price:.2f}</td>
                <td class="{'positive' if trade.pnl > 0 else 'negative'}">${trade.pnl:,.2f}</td>
                <td class="{'positive' if trade.return_pct > 0 else 'negative'}">{trade.return_pct * 100:.2f}%</td>
            </tr>
            """)
        
        return f"""
        <h2>Trades (First 50)</h2>
        <table>
            <tr><th>#</th><th>Entry</th><th>Exit</th><th>Entry Price</th><th>Exit Price</th><th>P&L</th><th>Return</th></tr>
            {''.join(rows)}
        </table>
"""

    def _html_footer(self) -> str:
        return f"""
        <footer>
            <p style="text-align: center; color: #7f8c8d; margin-top: 40px;">
                Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </footer>
    </div>
</body>
</html>
"""
