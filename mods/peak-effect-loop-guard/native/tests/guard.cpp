#include <Windows.h>
#include "guard_code.h"
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

struct Node { std::byte padding[0x98]{}; Node* next{}; };
static_assert(offsetof(Node, next) == 0x98);
void Check(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }

int main()
{
    alignas(8) volatile LONG64 hits = 0;
    auto memory = static_cast<std::uint8_t*>(VirtualAlloc(nullptr, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
    Check(memory != nullptr, "VirtualAlloc");
    // Executable ABI harness: RAX=current, RDX=sentinel, R8=output.
    const std::uint8_t entry[]{0x48, 0x89, 0xC8}; // mov rax,rcx
    std::memcpy(memory, entry, sizeof(entry));
    const auto code = peak_guard::MakeGuard(reinterpret_cast<std::uintptr_t>(&hits), reinterpret_cast<std::uintptr_t>(memory + 128));
    std::memcpy(memory + 3, code.data(), code.size());
    // Capture preserved RDX; execute game's TEST, capture flags, return RAX.
    const std::uint8_t resume[]{0x49,0x89,0x10, 0x48,0x85,0xC0, 0x9C,0x41,0x59, 0x4D,0x89,0x48,0x08, 0xC3};
    std::memcpy(memory + 128, resume, sizeof(resume));
    // A second harness executes the original entire loop, including the original
    // backward branch. Patch exactly seven bytes, just as the plugin does.
    auto loop = memory + 512;
    std::memcpy(loop, entry, sizeof(entry));
    const std::uint8_t clearFlag[]{0x81,0x60,0x7C,0xFF,0xF7,0xFF,0xFF};
    std::memcpy(loop + 3, clearFlag, sizeof(clearFlag));
    std::memcpy(loop + 10, peak_guard::kExpected.data(), peak_guard::kExpected.size());
    loop[22] = 0xC3;
    const auto loopGuard = peak_guard::MakeGuard(reinterpret_cast<std::uintptr_t>(&hits), reinterpret_cast<std::uintptr_t>(loop + 17));
    std::memcpy(memory + 768, loopGuard.data(), loopGuard.size());
    loop[10] = 0xE9;
    const std::int32_t displacement = static_cast<std::int32_t>((memory + 768) - (loop + 15));
    std::memcpy(loop + 11, &displacement, sizeof(displacement));
    loop[15] = loop[16] = 0x90;
    DWORD old{};
    Check(VirtualProtect(memory, 4096, PAGE_EXECUTE_READ, &old) != 0, "VirtualProtect");
    FlushInstructionCache(GetCurrentProcess(), memory, 4096);
    using Step = Node* (*)(Node*, std::uint64_t, std::uint64_t*);
    const auto step = reinterpret_cast<Step>(memory);
    Node tail{}, head{}, self{}; head.next = &tail; self.next = &self;
    constexpr std::uint64_t sentinel = 0x123456789ABCDEF0;
    std::uint64_t out[2]{};
    Check(step(&head,sentinel,out) == &tail, "ordinary link changed");
    Check(out[0] == sentinel && !(out[1] & 0x40), "ordinary RDX/ZF");
    Check(step(&tail,sentinel,out) == nullptr, "null terminator changed");
    Check(out[0] == sentinel && (out[1] & 0x40), "null RDX/ZF");
    Check(hits == 0, "false positive");
    Check(step(&self,sentinel,out) == nullptr, "self-loop did not terminate");
    Check(out[0] == sentinel && (out[1] & 0x40), "self RDX/ZF");
    Check(self.next == &self && head.next == &tail, "object mutated");
    Check(hits == 1, "counter");
    const auto walk = reinterpret_cast<Node* (*)(Node*)>(loop);
    Node first{}, middle{}, last{};
    first.next=&middle; middle.next=&last;
    const std::uint32_t flags=0xFFFFFFFF;
    for (auto node : {&first,&middle,&last}) std::memcpy(node->padding+0x7C,&flags,4);
    Check(walk(&first)==nullptr && hits==1, "ordinary full traversal");
    for (auto node : {&first,&middle,&last}) {
        std::uint32_t actual{}; std::memcpy(&actual,node->padding+0x7C,4);
        Check(actual==0xFFFFF7FF, "original per-node flag update changed");
    }
    last.next=&last;
    Check(walk(&first)==nullptr && hits==2, "tail self-loop full traversal");
    Check(first.next==&middle && middle.next==&last && last.next==&last, "full traversal changed links");
    // Verify the actual generated LOCK INC under concurrent execution.
    std::vector<std::thread> threads;
    for (int i=0;i<8;++i) threads.emplace_back([&] {
        std::uint64_t local[2]{};
        for (int j=0;j<10000;++j) step(&self,sentinel,local);
    });
    for (auto& t:threads) t.join();
    Check(hits == 80002, "concurrent counter lost updates");
    Check(self.next == &self, "self link mutated");
    VirtualFree(memory, 0, MEM_RELEASE);
    std::cout << "PASS: native x64 stub, normal/null/self links, RDX, ZF, no object writes, 80000 concurrent interceptions\n";
}
