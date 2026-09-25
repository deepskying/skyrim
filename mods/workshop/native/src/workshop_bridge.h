#pragma once
#include <SKSE/SKSE.h>
namespace unified_workshop {
bool InstallArrows();
void ArrowMessage(SKSE::MessagingInterface::Message*);
void AttachArrows(std::uint64_t view);
void SetArrowsVisible(bool visible);
void ArrowAction(const char* json);
void OpenArrowSection();
void CloseEquipment();
// Lives around the native transaction so rejected crafting never sounds successful.
struct ArrowCraftFeedback {
    bool success = false;
    ArrowCraftFeedback();
    ~ArrowCraftFeedback();
    ArrowCraftFeedback(const ArrowCraftFeedback&) = delete;
    ArrowCraftFeedback& operator=(const ArrowCraftFeedback&) = delete;
};
void SaveArrows(SKSE::SerializationInterface*);
void BeginLoadArrows(SKSE::SerializationInterface*);
bool LoadArrowRecord(SKSE::SerializationInterface*, std::uint32_t, std::uint32_t, std::uint32_t);
void RevertArrows(SKSE::SerializationInterface*);
// Queued crafting progress for the equipment HUD, already serialized as JSON.
std::string CraftOrderJson();
}
