#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <utility>

// Condition functions whose handler takes the subject, casts it to Actor without
// a null test, and then dereferences it. Every entry below was read out of the
// Skyrim SE 1.5.97 condition function table and disassembled; the RVA is the
// handler the engine calls for that index. Never extrapolate these to another
// runtime version - the plugin refuses to load when the handler does not match.
namespace condition_guard
{
    struct Target
    {
        std::uint16_t    index;
        std::uint32_t    handlerRva;
        std::string_view name;
    };

    inline constexpr std::array<Target, 6> kTargets{ {
        {   0, 0x2DB780u, "GetWantBlocking" },
        { 286, 0x2DB520u, "IsSneaking" },
        { 287, 0x2DB610u, "IsRunning" },
        { 568, 0x2DB6C0u, "IsSprinting" },
        { 569, 0x2DB880u, "IsBlocking" },
        { 676, 0x2DEF90u, "GetCurrentShoutVariation" },
    } };

    // The engine resolves a condition function through this table on every
    // evaluation, so replacing the handler pointer is enough - no code bytes move.
    inline constexpr std::uintptr_t kTableRva = 0x1DB8930;
    inline constexpr std::size_t    kTableStride = 0x50;
    inline constexpr std::size_t    kHandlerOffset = 0x20;

    inline constexpr std::size_t  kFormTypeOffset = 0x1A;
    inline constexpr std::uint8_t kActorFormType = 0x3E;

    // A condition function handler receives (rcx, rdx, r8, r9) and reports its
    // numeric result through the double pointer in r9. Returning false tells the
    // evaluator that the function could not be evaluated for this subject.
    using Handler = bool (*)(void*, void*, void*, double*);

    struct Slot
    {
        Handler     original{};
        std::atomic<std::int64_t> interceptions{ 0 };
    };

    // One slot per target. Hook<I> resolves its own slot because the engine calls
    // the replacement with exactly the four handler registers.
    inline std::array<Slot, kTargets.size()> g_slots{};

    // The handlers all start with `cmp byte ptr [rcx + 0x1A], 0x3E` (TESForm::formType
    // against ActorCharacter) and then keep the cast result without testing it.
    [[nodiscard]] inline bool SubjectIsNotActor(const void* a_subject)
    {
        if (!a_subject) {
            return true;
        }
        const auto* bytes = static_cast<const std::uint8_t*>(a_subject);
        return bytes[kFormTypeOffset] != kActorFormType;
    }

    // Guarding rule: an actor-only condition function is simply not satisfiable on
    // a non-actor subject. Report "cannot evaluate" instead of letting the engine
    // dereference the null actor. The out value is cleared first so a caller that
    // reads it anyway never sees stale data.
    template <std::size_t I>
    bool Hook(void* a_subject, void* a_arg1, void* a_arg2, double* a_out)
    {
        static_assert(I < kTargets.size(), "hook index out of range");
        if (SubjectIsNotActor(a_subject)) {
            if (a_out) {
                *a_out = 0.0;
            }
            g_slots[I].interceptions.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        return g_slots[I].original(a_subject, a_arg1, a_arg2, a_out);
    }

    template <std::size_t... Is>
    constexpr std::array<Handler, sizeof...(Is)> MakeHooks(std::index_sequence<Is...>)
    {
        return { &Hook<Is>... };
    }

    [[nodiscard]] inline std::array<Handler, kTargets.size()> MakeHooks()
    {
        return MakeHooks(std::make_index_sequence<kTargets.size()>{});
    }
}
