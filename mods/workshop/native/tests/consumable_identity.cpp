#include "../../../durability-manager/native/src/consumable_identity.h"
#include <cassert>
struct File {
    bool light;
    mutable int reads = 0;
    bool IsLight() const { ++reads; return light; }
};
int main() {
    using workshop_potions::SourceLocalID;
    // Exact form in the reported crash, plus another dynamically crafted potion.
    assert(SourceLocalID<File>(0xFF002C34, nullptr) == 0);
    assert(SourceLocalID<File>(0xFF000801, nullptr) == 0);
    assert(SourceLocalID<File>(0x010CCA12, nullptr) == 0);
    File regular{false}, light{true};
    assert(SourceLocalID(0xFF002C34, &regular) == 0);
    assert(regular.reads == 0);
    assert(SourceLocalID(0x01CCA123, &regular) == 0xCCA123);
    assert(SourceLocalID(0xFE123ABC, &light) == 0xABC);
    assert(SourceLocalID(0x00123456, &regular) == 0x123456);
}
