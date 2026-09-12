#pragma once

#include <array>
#include <cstdint>
#include <cstring>

namespace peak_guard
{
    inline constexpr std::uintptr_t kPatchRva = 0x55B0B7;
    // MOV RAX,[RAX+98]; TEST RAX,RAX; JNE -19. Only the MOV is replaced.
    inline constexpr std::array<std::uint8_t, 12> kExpected{
        0x48, 0x8B, 0x80, 0x98, 0, 0, 0, 0x48, 0x85, 0xC0, 0x75, 0xED
    };

    inline std::array<std::uint8_t, 47> MakeGuard(std::uintptr_t counter, std::uintptr_t resume)
    {
        std::array<std::uint8_t, 47> code{
            0x52,                                      // push rdx
            0x48, 0x89, 0xC2,                          // mov rdx,rax (current)
            0x48, 0x8B, 0x80, 0x98, 0, 0, 0,          // original: mov rax,[rax+98]
            0x48, 0x39, 0xD0,                          // cmp rax,rdx
            0x75, 0x10,                                // jne normal (skip 16 bytes)
            0x48, 0xBA, 0, 0, 0, 0, 0, 0, 0, 0,       // mov rdx,counter
            0xF0, 0x48, 0xFF, 0x02,                    // lock inc qword ptr [rdx]
            0x31, 0xC0,                                // xor eax,eax: stop this traversal
            0x5A,                                      // normal: pop rdx
            0xFF, 0x25, 0, 0, 0, 0,                    // jmp [rip+0]
            0, 0, 0, 0, 0, 0, 0, 0                    // resume address
        };
        std::memcpy(code.data() + 18, &counter, 8);
        std::memcpy(code.data() + 39, &resume, 8);
        return code;
    }
}
