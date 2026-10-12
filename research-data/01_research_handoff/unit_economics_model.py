"""
Illustrative per-account unit economics for a low-cost starter account (Section 5 of the handoff).

ONLY these inputs come from published data (Bank On National Data Hub, 2024 data, St. Louis Fed):
    average monthly balance  $1,273
    debit transactions       33 per holder per month
    average debit ticket     $13B monthly value / 341M monthly transactions = $38.12
    annual closure rate      15% overall, 31% at community institutions
Every other input is an invented placeholder to show sensitivity. Replace them with a
partner bank's own figures before using any output.

Run: python unit_economics_model.py
"""
from dataclasses import dataclass

AVG_BALANCE = 1273
TXN_PER_MONTH = 33
AVG_TICKET = 13e9 / 341e6

# Reg II cap structure for covered issuers (> $10B assets): 21c + 5 bps + 1c fraud adjustment.
# Verify the current cap before use; the Fed has proposed changing it.
COVERED_IX = 0.21 + 0.0005 * AVG_TICKET + 0.01
EXEMPT_IX = 0.009 * AVG_TICKET + 0.15  # assumption for debit-exempt community banks


@dataclass
class Scenario:
    name: str
    funding_rate: float      # value of deposit balances to the bank, per year
    interchange: float       # $ per debit transaction
    servicing_cost: float    # $ per account per year
    losses: float            # fraud + charge-offs, $ per account per year
    cross_sell: float        # margin from a second product, $ per account per year
    cac: float               # fully loaded acquisition cost, $ per account
    closure: float           # annual closure rate
    years: int = 5
    discount: float = 0.10

    def run(self) -> dict:
        revenue = AVG_BALANCE * self.funding_rate + TXN_PER_MONTH * 12 * self.interchange + self.cross_sell
        net = revenue - self.servicing_cost - self.losses
        survive = 1 - self.closure
        flows = [net * survive ** t / (1 + self.discount) ** t for t in range(1, 11)]
        npv5 = sum(flows[: self.years]) - self.cac
        cumulative, payback = -self.cac, None
        for t, f in enumerate(flows, start=1):
            cumulative += f
            if cumulative >= 0:
                payback = t
                break
        return {"scenario": self.name, "revenue": round(revenue), "net_per_year": round(net),
                "npv_5yr": round(npv5), "payback_year": payback}


SCENARIOS = [
    Scenario("A. Branch-served, bank > $10B", 0.025, COVERED_IX, 150, 10, 0, 250, 0.15),
    Scenario("B. Digital-first, bank > $10B", 0.025, COVERED_IX, 60, 10, 0, 250, 0.15),
    Scenario("C. Digital + partner channel + cross-sell", 0.025, COVERED_IX, 60, 10, 40, 120, 0.15),
    Scenario("D. Community bank, debit-exempt, digital", 0.025, EXEMPT_IX, 60, 10, 0, 250, 0.31),
]

if __name__ == "__main__":
    print(f"avg ticket ${AVG_TICKET:.2f} | covered interchange ${COVERED_IX:.3f} | exempt ${EXEMPT_IX:.3f}")
    for s in SCENARIOS:
        print(s.run())
