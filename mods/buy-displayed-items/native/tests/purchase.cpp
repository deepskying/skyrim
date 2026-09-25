#include "purchase.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

void Check(bool ok, const char* message)
{
    if (!ok) throw std::runtime_error(message);
}

struct Fake
{
    int gold = 100, items = 7, merchant = 0;
    int debitLimit = 1000, deliveryLimit = 1000;
    bool playerOwned = false;
    std::vector<std::string> calls;
    int Gold() { return gold; }
    int Items() { return items; }
    void Debit(int n) { calls.emplace_back("debit"); gold -= std::min(n, debitLimit); }
    void Refund(int n) { calls.emplace_back("refund"); gold += n; }
    void TransferOwnership() { calls.emplace_back("own"); playerOwned = true; }
    void RestoreOwnership() { calls.emplace_back("restore"); playerOwned = false; }
    void PickUp(int n)
    {
        Check(playerOwned, "pickup must not be a crime");
        calls.emplace_back("pickup");
        items += std::min(n, deliveryLimit);
    }
    void PayMerchant(int n) { calls.emplace_back("merchant"); merchant += n; }
};

int main()
{
    using displayed::Price;
    using displayed::Purchase;
    using displayed::Result;
    Check(Price(11, 3, 1.5) == 51, "round each unit before multiplying count");
    Check(!Price(0, 1, 2), "zero value excluded");
    Check(!Price(-10, 1, 2), "negative value excluded");
    Check(!Price(10, 0, 2), "zero stack excluded");
    Check(!Price(10, -1, 2), "negative stack excluded");
    Check(!Price(10, 1, std::numeric_limits<double>::infinity()), "infinite price excluded");
    Check(!Price(10, 1, std::numeric_limits<double>::quiet_NaN()), "NaN excluded");
    Check(!Price(10, 1, 0.5), "below-value multiplier excluded");
    Check(!Price(10, 1, 11), "excessive multiplier excluded");
    Check(!Price(std::numeric_limits<int>::max(), 2, 1), "stack overflow excluded");
    Check(!Price(std::numeric_limits<int>::max(), 1, 10), "unit overflow excluded");
    Check(Price(std::numeric_limits<int>::max(), 1, 1) == std::numeric_limits<int>::max(), "integer boundary works");
    {
        Fake a;
        Check(Purchase(a, 20, 2) == Result::bought, "normal purchase succeeds");
        Check(a.gold == 60 && a.items == 9 && a.merchant == 40, "exact balance and delivery");
        Check(a.calls == std::vector<std::string>{"debit", "own", "pickup", "merchant"}, "safe operation order");
    }
    {
        Fake a;
        a.gold = 40;
        Check(Purchase(a, 20, 2) == Result::bought && a.gold == 0, "exact funds accepted");
    }
    {
        Fake a;
        a.gold = 39;
        Check(Purchase(a, 20, 2) == Result::insufficientGold, "insufficient funds blocked");
        Check(a.calls.empty() && a.items == 7 && !a.playerOwned, "insufficient funds never touches item or money");
    }
    for (int debit : {0, 15}) {
        Fake a;
        a.debitLimit = debit;
        Check(Purchase(a, 20, 2) == Result::paymentFailed, "failed or partial payment blocked");
        Check(a.gold == 100 && a.items == 7 && a.merchant == 0 && !a.playerOwned, "partial payment refunded, item untouched");
    }
    {
        Fake a;
        a.deliveryLimit = 0;
        Check(Purchase(a, 20, 2) == Result::pickupFailed, "blocked pickup detected");
        Check(a.gold == 100 && a.items == 7 && a.merchant == 0 && !a.playerOwned, "blocked pickup fully rolled back");
    }
    {
        Fake a;
        a.deliveryLimit = 1;
        Check(Purchase(a, 20, 3) == Result::bought, "partial delivery accounted for");
        Check(a.gold == 80 && a.items == 8 && a.merchant == 20 && !a.playerOwned, "refund undelivered units and restore remaining reference");
    }
    {
        Fake a;
        Check(Purchase(a, 1000000000, 3) == Result::invalid && a.calls.empty(), "overflow never mutates game state");
    }
    std::cout << "Purchase tests passed: prices, overflow, insufficient/exact funds, payment failure, pickup failure, partial delivery.\n";
}
