#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <list>
#include <memory>
#include <unordered_map>
#include <utility>
#include <vector>

namespace enhancement
{
    // Session-only IDs, never engine pointers. The owner serializes all access.
    // Signatures compare exactly (no hash-only correctness assumptions).
    class EnchantmentCache
    {
    public:
        using IDs = std::vector<std::uint32_t>;
        using Snapshot = std::shared_ptr<const IDs>;
        using Clock = std::chrono::steady_clock;
        struct Statistics { std::uint64_t hits = 0, misses = 0, evictions = 0; };

        explicit EnchantmentCache(std::size_t maxEntries = 512, std::size_t maxIDs = 262144,
            Clock::duration lifetime = std::chrono::seconds(5)) :
            maxEntries_(maxEntries), maxIDs_(maxIDs), lifetime_(lifetime) {}
        EnchantmentCache(const EnchantmentCache&) = delete;
        EnchantmentCache& operator=(const EnchantmentCache&) = delete;

        template <class Loader>
        Snapshot Get(std::uint32_t baseID, const IDs& signature, Clock::time_point now, Loader&& loader)
        {
            if (const auto found = entries_.find(baseID); found != entries_.end()) {
                const auto& entry = found->second;
                if (entry.signature == signature && now >= entry.created && now - entry.created < lifetime_) {
                    ++statistics_.hits;
                    recent_.splice(recent_.begin(), recent_, entry.position);
                    return entry.ids;
                }
                Erase(found);
            }
            ++statistics_.misses;
            Snapshot ids = std::make_shared<const IDs>(std::forward<Loader>(loader)());
            // An oversized result is still usable by this caller, but cannot evict
            // the entire working set or exceed the cache's retained memory budget.
            if (maxEntries_ == 0 || lifetime_ <= Clock::duration::zero() || signature.size() > maxIDs_ || ids->size() > maxIDs_ - signature.size()) return ids;
            const auto slots = ids->size() + signature.size();
            while (entries_.size() >= maxEntries_ || retainedIDs_ > maxIDs_ - slots) {
                Erase(entries_.find(recent_.back()));
                ++statistics_.evictions;
            }
            recent_.push_front(baseID);
            try {
                entries_.emplace(baseID, Entry{ signature, ids, now, recent_.begin() });
            } catch (...) {
                recent_.pop_front();
                throw;
            }
            retainedIDs_ += slots;
            return ids;
        }

        void Clear()
        {
            entries_.clear();
            recent_.clear();
            retainedIDs_ = 0;
            statistics_ = {};
        }
        [[nodiscard]] std::size_t Size() const { return entries_.size(); }
        [[nodiscard]] std::size_t RetainedIDs() const { return retainedIDs_; }
        [[nodiscard]] Statistics Stats() const { return statistics_; }

    private:
        struct Entry
        {
            IDs signature;
            Snapshot ids;
            Clock::time_point created;
            std::list<std::uint32_t>::iterator position;
        };
        using Entries = std::unordered_map<std::uint32_t, Entry>;
        void Erase(Entries::iterator found)
        {
            retainedIDs_ -= found->second.signature.size() + found->second.ids->size();
            recent_.erase(found->second.position);
            entries_.erase(found);
        }
        std::size_t maxEntries_, maxIDs_, retainedIDs_ = 0;
        Clock::duration lifetime_;
        Statistics statistics_;
        std::list<std::uint32_t> recent_;
        Entries entries_;
    };
}
