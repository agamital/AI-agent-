"""
Chart builders — turn raw analysis data into Plotly figures.
No LLM calls: these are pure data → visual functions.
"""

import plotly.graph_objects as go


# Claude Design palette
_ACC = "#5849f0"
_POS = "#0e9f6e"
_NEG = "#e0342a"
_MUT = "#6c6c76"
_BD  = "#e9e9ee"
_GRID = "#f1f1f4"


def _base_layout(fig, height=280, title=None):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 14, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#17171c"),
        title=dict(text=title, font=dict(size=14, color="#17171c")) if title else None,
        showlegend=False,
        xaxis=dict(gridcolor=_GRID, zeroline=False),
        yaxis=dict(gridcolor=_GRID, zeroline=False),
    )
    return fig


def price_chart(dates, prices, sma_20=None, sma_50=None):
    """6-month price line with optional moving averages."""
    fig = go.Figure()
    # Determine trend colour
    line_color = _POS if (prices and prices[-1] >= prices[0]) else _NEG
    fig.add_trace(go.Scatter(
        x=dates, y=prices, mode="lines", name="Price",
        line=dict(color=line_color, width=2),
        fill="tozeroy", fillcolor=f"rgba({'14,159,110' if line_color==_POS else '224,52,42'},0.06)",
    ))
    if sma_20:
        fig.add_hline(y=sma_20, line=dict(color=_ACC, width=1, dash="dot"),
                      annotation_text="SMA-20", annotation_position="right")
    if sma_50:
        fig.add_hline(y=sma_50, line=dict(color=_MUT, width=1, dash="dot"),
                      annotation_text="SMA-50", annotation_position="right")
    fig.update_yaxes(range=[min(prices) * 0.97, max(prices) * 1.02])
    return _base_layout(fig, height=300, title="Price · 6 months")


def rsi_gauge(rsi):
    """RSI as a horizontal bar with overbought/oversold zones."""
    if rsi is None:
        return None
    color = _NEG if rsi > 70 else (_POS if rsi < 30 else _MUT)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi,
        number=dict(font=dict(size=26, family="IBM Plex Mono")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1),
            bar=dict(color=color, thickness=0.7),
            steps=[
                dict(range=[0, 30], color="#e7f6ef"),
                dict(range=[30, 70], color="#f4f4f7"),
                dict(range=[70, 100], color="#fdeceb"),
            ],
        ),
    ))
    return _base_layout(fig, height=220, title="RSI-14")


def metrics_bar(ticker, peers_data, metric="pe_ratio", label="P/E Ratio"):
    """Bar chart comparing one metric across the stock and its peers."""
    if not peers_data:
        return None
    tickers = [p.ticker for p in peers_data]
    values = [getattr(p, metric, None) for p in peers_data]
    # Skip if all None
    if not any(v is not None for v in values):
        return None
    colors = [_ACC if t == ticker else "#c7c3f4" for t in tickers]
    fig = go.Figure(go.Bar(
        x=tickers, y=values, marker_color=colors,
        text=[f"{v:.2f}" if v is not None else "N/A" for v in values],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=12),
    ))
    return _base_layout(fig, height=260, title=label)


def snapshot_metrics(market):
    """Return a list of (label, value, sub) tuples for st.metric tiles."""
    tiles = []
    if market:
        if market.market_cap:
            cap = market.market_cap
            cap_str = (f"${cap/1e12:.2f}T" if cap >= 1e12
                       else f"${cap/1e9:.1f}B" if cap >= 1e9
                       else f"${cap/1e6:.0f}M")
            tiles.append(("Market Cap", cap_str, None))
        if market.current_price:
            delta = None
            if market.previous_close:
                pct = (market.current_price - market.previous_close) / market.previous_close * 100
                delta = f"{pct:+.2f}%"
            tiles.append(("Price", f"${market.current_price}", delta))
        if market.week_52_high and market.week_52_low:
            tiles.append(("52-Week Range",
                          f"${market.week_52_low} – ${market.week_52_high}", None))
        if market.beta is not None:
            tiles.append(("Beta", f"{market.beta}", None))
    return tiles


def usage_bar(remaining, limit, label="Groq tokens/min"):
    """Horizontal progress bar showing remaining quota."""
    import plotly.graph_objects as go
    if remaining is None or limit is None or limit == 0:
        return None
    used = limit - remaining
    pct_remaining = remaining / limit
    # Color: green if plenty, amber mid, red low
    if pct_remaining > 0.5:
        color = _POS
    elif pct_remaining > 0.2:
        color = "#d9a514"
    else:
        color = _NEG

    fig = go.Figure(go.Bar(
        x=[remaining], y=[label], orientation="h",
        marker=dict(color=color), width=0.5,
        text=[f"{remaining:,} / {limit:,}"], textposition="inside",
        textfont=dict(family="IBM Plex Mono", size=12, color="white"),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Bar(
        x=[used], y=[label], orientation="h",
        marker=dict(color=_GRID), width=0.5, hoverinfo="skip",
    ))
    fig.update_layout(
        barmode="stack", height=70,
        margin=dict(l=0, r=0, t=4, b=4),
        paper_bgcolor="white", plot_bgcolor="white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, limit]),
        yaxis=dict(visible=False),
        font=dict(family="IBM Plex Sans", size=11),
    )
    return fig
