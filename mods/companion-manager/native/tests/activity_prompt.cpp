// Execute the production message builder with an engine queue adapter.
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"
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
    explicit Relocation(int id) { CHECK(id == 51422); }
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
        CHECK(companion::activity::QueuePrompt(temporary.c_str(), callback()));
        temporary.clear();
        CHECK(queued->bodyText == line); // message owns text after caller returns
        CHECK((queued->buttonText == std::vector<std::string>{"好的", "稍后再说"}));
        CHECK(queued->type == 4 && queued->menuDepth == 10);
        CHECK(queued->cancelOptionIndex == 1 && queued->isCancellable);
        CHECK(queued->optionIndexOffset == 0 && !queued->useHtml && !queued->verticalButtons);
        CHECK(Answer::alive == 1 && RE::MessageBoxData::alive == 1);
        queued->callback->Run(0); CHECK(result == 0);
        queued->callback->Run(1); CHECK(result == 1);
        queued.reset(); CHECK(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
    }
    accept = false;
    CHECK(!companion::activity::QueuePrompt("rejected", callback()));
    CHECK(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
    accept = true;
    RE::UIMessageQueue::allocation = false;
    CHECK(!companion::activity::QueuePrompt("no data", callback()));
    RE::UIMessageQueue::available = false;
    CHECK(!companion::activity::QueuePrompt("no queue", callback()));
    RE::UIMessageQueue::available = true;
    RE::InterfaceStrings::available = false;
    CHECK(!companion::activity::QueuePrompt("no strings", callback()));
    CHECK(Answer::alive == 0 && RE::MessageBoxData::alive == 0);
}
