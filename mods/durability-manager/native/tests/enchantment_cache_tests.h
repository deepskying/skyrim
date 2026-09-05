#pragma once

#include "enchantment_cache.h"
#include <algorithm>
#include <stdexcept>

inline void TestEnchantmentCache()
{
    using Cache = enhancement::EnchantmentCache;
    using namespace std::chrono_literals;
    const auto require = [](bool condition) { if (!condition) throw std::runtime_error("Enchantment cache test failed"); };
    const Cache::Clock::time_point start{};
    Cache cache(2, 20, 5s);
    int scans = 0;
    const auto load = [&] { ++scans; return Cache::IDs{10, 20}; };
    const auto original = cache.Get(1, {1, 100}, start, load);
    require(*original == Cache::IDs({10, 20}));
    require(cache.Get(1, {1, 100}, start + 1s, load) == original && scans == 1);
    // Current instance enchantments are excluded by the caller, not cached:
    // two copies can share the same snapshot without losing each other's alternative.
    require(std::find(original->begin(), original->end(), 10) != original->end());
    require(std::find(original->begin(), original->end(), 20) != original->end());
    require(cache.Get(1, {1, 101}, start + 2s, load) != original && scans == 2);  // Keyword change.
    cache.Get(1, {2, 101}, start + 2s, load);  // Weapon class change.
    require(scans == 3 && cache.Size() == 1 && cache.RetainedIDs() == 4);
    cache.Get(1, {2, 101}, start + 6s, load);
    require(scans == 3);  // A hit does NOT extend the creation deadline.
    cache.Get(1, {2, 101}, start + 7s, load);
    require(scans == 4);  // Exact TTL boundary expires.
    cache.Get(1, {2, 101}, start, load);
    require(scans == 5);  // Reversed injected time cannot preserve stale data.

    cache.Clear();
    require(cache.Size() == 0 && cache.RetainedIDs() == 0 && cache.Stats().hits == 0);
    require(*original == Cache::IDs({10, 20}));  // Snapshot remains valid after eviction/reset.
    int negatives = 0;
    const auto empty = [&] { ++negatives; return Cache::IDs{}; };
    require(cache.Get(9, {}, start, empty)->empty());
    require(cache.Get(9, {}, start + 4s, empty)->empty() && negatives == 1);
    const auto newlyAllowed = cache.Get(9, {}, start + 5s, [&] { ++negatives; return Cache::IDs{42}; });
    require(negatives == 2 && *newlyAllowed == Cache::IDs({42}));  // Empty results expire too.

    cache.Clear();
    cache.Get(1, {}, start, load);
    cache.Get(2, {}, start, load);
    cache.Get(1, {}, start, load);  // Promote 1, making 2 least recently used.
    cache.Get(3, {}, start, load);
    const auto before = scans;
    cache.Get(1, {}, start, load);
    require(scans == before && cache.Size() == 2);
    cache.Get(2, {}, start, load);
    require(scans == before + 1 && cache.Stats().evictions == 2);

    Cache limited(10, 5, 5s);
    limited.Get(1, {1}, start, load);  // 1 signature + 2 result IDs.
    limited.Get(2, {2}, start, load);
    require(limited.Size() == 1 && limited.RetainedIDs() == 3 && limited.Stats().evictions == 1);
    const auto oversized = limited.Get(3, {3}, start, [] { return Cache::IDs(6, 99); });
    require(oversized->size() == 6 && limited.Size() == 1 && limited.RetainedIDs() == 3);
    limited.Get(4, Cache::IDs(6, 1), start, empty);
    require(limited.Size() == 1);  // Signature also participates in the memory bound.
    Cache disabled(0);
    disabled.Get(1, {}, start, load);
    disabled.Get(1, {}, start, load);
    require(disabled.Size() == 0 && disabled.Stats().misses == 2);
    Cache immediate(2, 20, 0s);
    immediate.Get(1, {}, start, load);
    require(immediate.Size() == 0);

    cache.Clear();
    bool threw = false;
    try { cache.Get(1, {}, start, []() -> Cache::IDs { throw std::runtime_error("loader failed"); }); }
    catch (const std::runtime_error&) { threw = true; }
    require(threw && cache.Size() == 0 && cache.RetainedIDs() == 0);
    cache.Get(1, {}, start, load);
    cache.Clear();  // Same ID in another save or rebuilt pool MUST scan again.
    const auto changed = cache.Get(1, {}, start, [] { return Cache::IDs{30}; });
    require(*changed == Cache::IDs({30}));

    // Synthetic repeated inventory workload: 20 base items, 500 candidates each,
    // 5000 lookups in one TTL. Exactly 20 full scans, not 5000; same candidates.
    Cache workload;
    int checks = 0;
    for (std::uint32_t query = 0; query < 5000; ++query) {
        const auto id = query % 20;
        const auto result = workload.Get(id, {1, id}, start + 1s, [&] {
            Cache::IDs ids;
            for (std::uint32_t candidate = 0; candidate < 500; ++candidate) {
                ++checks;
                if (candidate % 20 == id) ids.push_back(candidate);
            }
            return ids;
        });
        require(result->size() == 25 && std::all_of(result->begin(), result->end(), [id](auto candidate) { return candidate % 20 == id; }));
    }
    require(checks == 10000 && workload.Stats().misses == 20 && workload.Stats().hits == 4980);
}
