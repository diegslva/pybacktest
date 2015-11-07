import numpy
import pandas

from pybacktest.blocks import Entry


class Blotter(object):
    """
    Blotter resolves positions and calculates trade and continuous returns for a spec
    (single Entry and its attached Exits).

    Attributes:
        entry: Entry with its attached Exits.
        positions: Positions that Entry + Exits resolves to.
        trade_price: Price series, specifying price for all of the trades.
        mark_price: Reference price series of underlying asset (if not specified, taken from Entry).
        continuous_price: Spliced mark_price and trade_price. It equals mark_price at timepoints where there
            is no position changes and trade_price when there is.
        trade_returns: Returns of each trade, recorded at times where position changes from zero or to zero.
        continuous_returns: Returns of strategy, recorded at each time step.
    """

    def __init__(self, entry, mark_price=None):
        assert isinstance(entry, Entry)
        assert entry.condition.dtype == bool

        self.mark_price = mark_price
        if self.mark_price is None:
            self.mark_price = entry.price

        self.entry = entry

        positions = pandas.Series(index=entry.condition.index, dtype='float')
        trade_price = pandas.Series(index=entry.condition.index, dtype='float')

        positions.ix[entry.condition] = entry.volume
        trade_price[entry.condition] = entry.transaction_price[entry.condition]

        for ex in entry.exits:
            positions.ix[ex.condition] = 0.0
            trade_price.ix[ex.condition] = ex.transaction_price[ex.condition]

        positions.iloc[-1] = 0.0
        positions = positions.dropna()
        positions = positions.ix[positions != positions.shift()]

        if numpy.isnan(trade_price.iloc[-1]):
            trade_price.iloc[-1] = entry.transaction_price.ix[trade_price.index[-1]]

        self.positions = positions
        self.trade_price = trade_price.ix[positions.index]

        self.trade_returns = (
            self.positions.shift() * self.trade_price.pct_change()
        ).fillna(value=0)

        self.continuous_price = self.mark_price.copy()
        self.continuous_price[self.trade_price.index] = self.trade_price
        self.continuous_returns = (self.positions.reindex(self.continuous_price.index).ffill().fillna(
            value=0).shift() * self.continuous_price.pct_change()).fillna(value=0)