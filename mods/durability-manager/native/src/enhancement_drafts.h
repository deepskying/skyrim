#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <unordered_map>
#include <utility>
#include <vector>

namespace enhancement
{
    inline bool HasRoom(float current, float limit, float epsilon)
    {
        return std::isfinite(current) && std::isfinite(limit) && limit - current > epsilon;
    }

    inline std::uint32_t RefreshCost(std::uint32_t refreshes)
    {
        return 80U * ((std::min)(refreshes, 999U) + 1U);
    }

    // A round belongs to an item instance, not to the selected UI row/station.
    // The owner holds its game-thread lock while accessing this ledger.
    template <class Key, class Card, class Hash = std::hash<Key>>
    class DraftLedger
    {
    public:
        struct Draft
        {
            std::vector<Card> cards;
            std::uint32_t refreshes = 0;
        };

        const Draft* Find(const Key& key) const
        {
            const auto found = entries_.find(key);
            return found == entries_.end() ? nullptr : &found->second;
        }

        void Store(const Key& key, std::vector<Card> cards, std::uint32_t refreshes)
        {
            entries_.insert_or_assign(key, Draft{std::move(cards), refreshes});
        }

        void Erase(const Key& key) { entries_.erase(key); }
        void Clear() { entries_.clear(); }

    private:
        std::unordered_map<Key, Draft, Hash> entries_;
    };
}
