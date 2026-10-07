#include "guard_code.h"

#include <Windows.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace
{
    struct FakeForm
    {
        std::byte      padding[condition_guard::kFormTypeOffset]{};
        std::uint8_t   formType{};
    };
    static_assert(offsetof(FakeForm, formType) == condition_guard::kFormTypeOffset);

    struct Recorder
    {
        int    calls{};
        void*  subject{};
        void*  arg1{};
        void*  arg2{};
        double value{};
    };

    Recorder g_recorder{};

    bool OriginalHandler(void* a_subject, void* a_arg1, void* a_arg2, double* a_out)
    {
        ++g_recorder.calls;
        g_recorder.subject = a_subject;
        g_recorder.arg1 = a_arg1;
        g_recorder.arg2 = a_arg2;
        if (a_out) {
            *a_out = g_recorder.value;
        }
        return true;
    }

    void Check(bool a_condition, const char* a_message)
    {
        if (!a_condition) {
            throw std::runtime_error(a_message);
        }
    }

    std::size_t IndexOf(std::uint16_t a_index)
    {
        for (std::size_t i = 0; i < condition_guard::kTargets.size(); ++i) {
            if (condition_guard::kTargets[i].index == a_index) {
                return i;
            }
        }
        throw std::runtime_error("target table is missing a condition function index");
    }
}

int main()
{
    // The table has to stay a table: unique indices, unique handlers and handlers
    // that live inside the executable's code section.
    constexpr std::uint32_t textStart = 0x1000;
    constexpr std::uint32_t textEnd = 0x15078EC;
    for (std::size_t i = 0; i < condition_guard::kTargets.size(); ++i) {
        const auto& target = condition_guard::kTargets[i];
        Check(target.handlerRva >= textStart && target.handlerRva < textEnd, "handler RVA outside .text");
        for (std::size_t j = i + 1; j < condition_guard::kTargets.size(); ++j) {
            Check(target.index != condition_guard::kTargets[j].index, "duplicate condition index");
            Check(target.handlerRva != condition_guard::kTargets[j].handlerRva, "duplicate handler RVA");
        }
    }

    Check(condition_guard::SubjectIsNotActor(nullptr), "null subject must be rejected");
    FakeForm container{};
    container.formType = 0x1C; // Container
    Check(condition_guard::SubjectIsNotActor(&container), "container must be rejected");
    FakeForm projectile{};
    projectile.formType = 0x32; // Projectile
    Check(condition_guard::SubjectIsNotActor(&projectile), "projectile must be rejected");
    FakeForm actor{};
    actor.formType = condition_guard::kActorFormType;
    Check(!condition_guard::SubjectIsNotActor(&actor), "actor must pass through");

    const auto hooks = condition_guard::MakeHooks();
    const auto blocking = IndexOf(569);
    auto& slot = condition_guard::g_slots[blocking];
    slot.original = &OriginalHandler;
    slot.interceptions.store(0);
    g_recorder = {};
    g_recorder.value = 42.0;

    int arg1 = 1;
    int arg2 = 2;
    double out = 7.0;

    // Non-actor subject: the original handler must not run, the out value is
    // cleared and the evaluator is told the condition cannot be computed.
    Check(hooks[blocking](&container, &arg1, &arg2, &out) == false, "container must not reach the original handler");
    Check(out == 0.0, "out value must be cleared for a non-actor");
    Check(g_recorder.calls == 0, "original handler ran for a container");
    Check(slot.interceptions.load() == 1, "interception counter");

    // Null subject takes the same path.
    out = 7.0;
    Check(hooks[blocking](nullptr, &arg1, &arg2, &out) == false, "null subject must not reach the original handler");
    Check(out == 0.0, "out value must be cleared for a null subject");
    Check(slot.interceptions.load() == 2, "interception counter after null subject");

    // Actor subject: unchanged behaviour, arguments and out value travel through.
    double secondOut = 9.0;
    Check(hooks[blocking](&actor, &arg1, &arg2, &secondOut) == true, "actor must keep the original result");
    Check(g_recorder.calls == 1, "original handler did not run for an actor");
    Check(g_recorder.subject == &actor && g_recorder.arg1 == &arg1 && g_recorder.arg2 == &arg2, "arguments changed");
    Check(secondOut == 42.0, "out value from the original handler was lost");
    Check(slot.interceptions.load() == 2, "actor evaluation must not count as an interception");

    // Every other guard behaves the same way on a non-actor subject.
    for (std::size_t i = 0; i < hooks.size(); ++i) {
        condition_guard::g_slots[i].original = &OriginalHandler;
        condition_guard::g_slots[i].interceptions.store(0);
        double value = 5.0;
        Check(hooks[i](&container, nullptr, nullptr, &value) == false, "guard did not short-circuit");
        Check(value == 0.0, "guard left a stale out value");
        Check(condition_guard::g_slots[i].interceptions.load() == 1, "guard did not count");
    }

    std::cout << "PASS: non-actor/null subjects are short-circuited, actors keep the original handler, out values and arguments are intact\n";
    return 0;
}
