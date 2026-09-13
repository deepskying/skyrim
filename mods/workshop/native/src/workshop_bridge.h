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
void SaveArrows(SKSE::SerializationInterface*);
void BeginLoadArrows(SKSE::SerializationInterface*);
bool LoadArrowRecord(SKSE::SerializationInterface*, std::uint32_t, std::uint32_t, std::uint32_t);
void RevertArrows(SKSE::SerializationInterface*);
}
