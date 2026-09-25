#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>

namespace displayed
{
    inline std::optional<std::int32_t> Price(std::int32_t value, std::int32_t count, double multiplier)
    {
        if (value <= 0 || count <= 0 || !std::isfinite(multiplier) || multiplier < 1.0 || multiplier > 10.0)
            return std::nullopt;
        const auto total = std::ceil(value * multiplier) * count;
        if (total > std::numeric_limits<std::int32_t>::max()) return std::nullopt;
        return static_cast<std::int32_t>(total);
    }

    enum class Result { bought, insufficientGold, paymentFailed, pickupFailed, invalid };

    // Adapter methods operate synchronously on the game thread. Reserve payment
    // before changing ownership; verify delivery and refund any undelivered units.
    // Shared with fault-injection tests so cancellation paths receive real coverage.
    template <class Adapter>
    Result Purchase(Adapter& adapter, std::int32_t unitPrice, std::int32_t count)
    {
        const auto total = Price(unitPrice, count, 1.0);
        if (!total) return Result::invalid;
        const auto goldBefore = adapter.Gold();
        if (goldBefore < *total) return Result::insufficientGold;
        adapter.Debit(*total);
        const auto paid = static_cast<std::int64_t>(goldBefore) - adapter.Gold();
        if (paid != *total) {
            if (paid > 0 && paid <= std::numeric_limits<std::int32_t>::max())
                adapter.Refund(static_cast<std::int32_t>(paid));
            return Result::paymentFailed;
        }

        const auto itemsBefore = adapter.Items();
        adapter.TransferOwnership();
        adapter.PickUp(count);
        const auto delivered = std::clamp<std::int64_t>(
            static_cast<std::int64_t>(adapter.Items()) - itemsBefore, 0, count);
        if (delivered < count) {
            adapter.RestoreOwnership();
            adapter.Refund(static_cast<std::int32_t>((count - delivered) * unitPrice));
        }
        if (delivered == 0) return Result::pickupFailed;
        adapter.PayMerchant(static_cast<std::int32_t>(delivered * unitPrice));
        return Result::bought;
    }
}
