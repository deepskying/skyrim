// Execute the production message builder with an engine queue adapter.
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
namespace RE {
struct IMessageBoxCallback { virtual ~IMessageBoxCallback() = default; virtual void Run(int) = 0; };
template<class T> using BSTSmartPointer = std::shared_ptr<T>;
struct IUIMessageData { virtual ~IUIMessageData() = default; };
struct MessageBoxData : IUIMessageData {
    inline static int alive = 0;
    MessageBoxData() { ++alive; }
    ~MessageBoxData() { --alive; }
    std::string bodyText;
    std::vector<std::string> buttonText;
    std::uint32_t type{}, menuDepth{};
    int cancelOptionIndex{};
    BSTSmartPointer<IMessageBoxCallback> callback;
    std::uint8_t optionIndexOffset{};
    bool useHtml{}, verticalButtons{}, isCancellable{};
};
struct UIMessageQueue {
    inline static bool available = true, allocation = true;
    static UIMessageQueue* GetSingleton() { static UIMessageQueue q; return available ? &q : nullptr; }
    IUIMessageData* CreateUIMessageData(const char*) { return allocation ? new MessageBoxData : nullptr; }
};
struct InterfaceStrings {
    inline static bool available = true;
    const char* messageBoxData = "MessageBoxData";
    static InterfaceStrings* GetSingleton() { static InterfaceStrings s; return available ? &s : nullptr; }
};
}
bool accept = true;
std::unique_ptr<RE::MessageBoxData> queued;
namespace REL {
template<class Fn> struct Relocation {
    explicit Relocation(int id) { assert(id == 51422); }
    bool operator()(RE::MessageBoxData* data) { if (accept) queued.reset(data); return accept; }
};
}
#define RELOCATION_ID(se, ae) se
#include "../src/activity_prompt.h"
struct Answer : RE::IMessageBoxCallback {
    inline static int alive = 0;
    explicit Answer(int& result): result(result) { ++alive; }
    ~Answer() { --alive; }
    void Run(int choice) override { result = choice; }
    int& result;
};
int main() {
    int result = -1;
    auto callback = [&] { return RE::BSTSmartPointer<RE::IMessageBoxCallback>(new Answer(result)); };
    for (const char* line : {"爱拉：我快拿不动了", "爱拉：可以给我一些服装上的建议吗？"}) {
        std::string temporary = line;
        assert(companion::activity::QueuePrompt(temporary.c_str(), callback()));
        temporary.clear();
        assert(queued->bodyText == line); // message owns text after caller returns
        assert((queued->buttonText == std::vector<std::string>{"好的", "稍后再说"}));
        assert(queued->type == 4 && queued->menuDepth == 10);
        assert(queued->cancelOptionIndex == 1 && queued->isCancellable);
        assert(queued->optionIndexOffset == 0 && !queued->useHtml && !queued->verticalButtons);
        assert(Answer::alive == 1 && RE::MessageBoxData::alive == 1);
        queued->callback->Run(0); assert(result == 0);
        queued->callback->Run(1); assert(result == 1);
        queued.reset(); assert(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
    }
    accept = false;
    assert(!companion::activity::QueuePrompt("rejected", callback()));
    assert(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
    accept = true;
    RE::UIMessageQueue::allocation = false;
    assert(!companion::activity::QueuePrompt("no data", callback()));
    RE::UIMessageQueue::available = false;
    assert(!companion::activity::QueuePrompt("no queue", callback()));
    RE::UIMessageQueue::available = true;
    RE::InterfaceStrings::available = false;
    assert(!companion::activity::QueuePrompt("no strings", callback()));
    assert(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
}
