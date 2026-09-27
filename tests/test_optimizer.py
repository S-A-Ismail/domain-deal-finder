import pytest

from ddf.models import Offer
from ddf.optimizer import Money, all_plans, best_plans, cheapest_tlds, stay_plan, transfer_plan

MONEY = Money(usd_pkr=280.0, card_markup=0.0)

promo = Offer("PromoReg", "store", "USD", register=2.0, renew=40.0, transfer=40.0)
cheap_renew = Offer("CheapRenew", "store", "USD", register=12.0, renew=10.0, transfer=9.0)
pknic = Offer("PKNIC", "pk", "PKR", register=2100, renew=2100, transfer=None, block_years=2)


def test_stay_plan_uses_promo_then_renewal():
    plan = stay_plan(promo, 3, MONEY)
    assert plan.total_pkr == pytest.approx((2 + 2 * 40) * 280)
    assert plan.years_covered == 3


def test_block_billing_rounds_up_years():
    one = stay_plan(pknic, 1, MONEY)
    three = stay_plan(pknic, 3, MONEY)
    assert (one.years_covered, one.total_pkr) == (2, 4200)
    assert (three.years_covered, three.total_pkr) == (4, 8400)


def test_transfer_plan_takes_promo_then_cheap_renewals():
    plan = transfer_plan(promo, cheap_renew, 5, MONEY)
    assert plan.total_pkr == pytest.approx((2 + 9 + 3 * 10) * 280)


def test_transfer_not_possible_for_one_year_same_registrar_or_blocked():
    assert transfer_plan(promo, cheap_renew, 1, MONEY) is None
    assert transfer_plan(promo, promo, 3, MONEY) is None
    assert transfer_plan(promo, pknic, 3, MONEY) is None


def test_best_plan_switches_strategy_with_horizon():
    plans = best_plans([promo, cheap_renew], MONEY)
    assert plans[1][0].summary == "PromoReg for all 1 yr"
    assert plans[5][0].strategy == "transfer"
    assert plans[5][0].total_pkr < stay_plan(cheap_renew, 5, MONEY).total_pkr


def test_card_markup_applies_to_usd_only():
    money = Money(usd_pkr=280.0, card_markup=0.1)
    assert money.pkr(10, "USD") == pytest.approx(3080)
    assert money.pkr(2100, "PKR") == 2100


def test_tie_prefers_stay():
    twin = Offer("Twin", "store", "USD", register=10.0, renew=10.0, transfer=10.0)
    base = Offer("Base", "store", "USD", register=10.0, renew=10.0, transfer=10.0)
    assert all_plans([twin, base], 3, MONEY)[0].strategy == "stay"


def test_cheapest_tlds_sorted_by_total():
    # .store via promo + transfer = (2 + 9) * 280 = 3080, beats .pk's 2-year block of 4200
    ranked = cheapest_tlds({"store": [promo, cheap_renew], "pk": [pknic]}, 2, MONEY)
    assert [(tld, round(plan.total_pkr)) for tld, plan in ranked] == [("store", 3080), ("pk", 4200)]
